"""
TCP bridge to the UnrealMCP C++ editor plugin.

Provides send_command() and execute_python() to the rest of the MCP server.
All tools import from here — no tool module talks to the socket directly.
"""

import json
import logging
import os
import socket
import struct
import textwrap
import threading
import time
from typing import Any

logger = logging.getLogger("unreal_dms.bridge")

UNREAL_HOST = os.environ.get("UNREAL_MCP_HOST", "127.0.0.1")
UNREAL_PORT = int(os.environ.get("UNREAL_MCP_PORT", "55557"))

_MAX_RETRIES = 3
_BASE_RETRY_DELAY = 0.5
_MAX_RETRY_DELAY = 5.0
_CONNECT_TIMEOUT = 10
_DEFAULT_RECV_TIMEOUT = 30
_LARGE_OP_RECV_TIMEOUT = 300
_BUFFER_SIZE = 8192

_LARGE_OPERATION_COMMANDS = {
    "get_available_materials",
    "create_town",
    "create_castle_fortress",
    "construct_mansion",
    "create_suspension_bridge",
    "create_aqueduct",
    "create_maze",
    "execute_python",  # Python scripts can be long-running
    "render_sequence_to_disk",
    "run_capture_batch",
}


class UnrealConnection:
    """Thread-safe TCP connection to the UnrealMCP plugin with auto-reconnect."""

    def __init__(self):
        self.socket: socket.socket | None = None
        self.connected = False
        self._lock = threading.RLock()
        self._last_error: str | None = None

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(_CONNECT_TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("hh", 1, 0))
        except OSError:
            pass
        return sock

    def connect(self) -> bool:
        for attempt in range(_MAX_RETRIES + 1):
            with self._lock:
                self._close_socket_unsafe()
                try:
                    logger.info(
                        "Connecting to Unreal at %s:%d (attempt %d/%d)",
                        UNREAL_HOST, UNREAL_PORT, attempt + 1, _MAX_RETRIES + 1,
                    )
                    self.socket = self._create_socket()
                    self.socket.connect((UNREAL_HOST, UNREAL_PORT))
                    self.connected = True
                    self._last_error = None
                    logger.info("Connected to Unreal Engine")
                    return True
                except (socket.timeout, ConnectionRefusedError, OSError) as e:
                    self._last_error = str(e)
                    logger.warning("Connection attempt %d failed: %s", attempt + 1, e)
                except Exception as e:
                    self._last_error = str(e)
                    logger.error("Unexpected connection error (attempt %d): %s", attempt + 1, e)
                self._close_socket_unsafe()
                self.connected = False

            if attempt < _MAX_RETRIES:
                delay = min(_BASE_RETRY_DELAY * (2**attempt), _MAX_RETRY_DELAY)
                logger.info("Retrying in %.1fs…", delay)
                time.sleep(delay)

        logger.error(
            "Failed to connect after %d attempts. Last error: %s",
            _MAX_RETRIES + 1, self._last_error,
        )
        return False

    def _close_socket_unsafe(self):
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.connected = False

    def disconnect(self):
        with self._lock:
            self._close_socket_unsafe()

    def _get_timeout(self, command_type: str) -> int:
        if any(k in command_type for k in _LARGE_OPERATION_COMMANDS):
            return _LARGE_OP_RECV_TIMEOUT
        return _DEFAULT_RECV_TIMEOUT

    def _receive_response(self, command_type: str) -> bytes:
        timeout = self._get_timeout(command_type)
        self.socket.settimeout(timeout)
        chunks: list[bytes] = []
        total = 0
        start = time.time()
        try:
            while True:
                if time.time() - start > timeout:
                    raise socket.timeout(f"Overall timeout after {time.time()-start:.1f}s")
                try:
                    chunk = self.socket.recv(_BUFFER_SIZE)
                except socket.timeout:
                    if chunks:
                        data = b"".join(chunks)
                        try:
                            json.loads(data.decode("utf-8"))
                            return data
                        except json.JSONDecodeError:
                            pass
                    raise
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                data = b"".join(chunks)
                try:
                    json.loads(data.decode("utf-8"))
                    logger.debug("Received %d bytes for %s", total, command_type)
                    return data
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        except socket.timeout:
            if chunks:
                data = b"".join(chunks)
                try:
                    json.loads(data.decode("utf-8"))
                    return data
                except Exception:
                    pass
            raise TimeoutError(
                f"Timeout waiting for response to {command_type} ({total} bytes received)"
            )
        if chunks:
            data = b"".join(chunks)
            try:
                json.loads(data.decode("utf-8"))
                return data
            except Exception:
                raise ConnectionError(f"Connection closed with incomplete data ({total} bytes)")
        raise ConnectionError("Connection closed without response")

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: str | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self._send_once(command, params, attempt)
            except (ConnectionError, TimeoutError, socket.error, OSError) as e:
                last_error = str(e)
                logger.warning("Command %s failed (attempt %d): %s", command, attempt + 1, e)
                self.disconnect()
                if attempt < _MAX_RETRIES:
                    delay = min(_BASE_RETRY_DELAY * (2**attempt), _MAX_RETRY_DELAY)
                    time.sleep(delay)
            except Exception as e:
                logger.error("Unexpected error in send_command: %s", e)
                self.disconnect()
                return {"status": "error", "error": str(e)}
        return {
            "status": "error",
            "error": f"Command {command} failed after {_MAX_RETRIES + 1} attempts: {last_error}",
        }

    def _send_once(self, command: str, params: dict[str, Any] | None, attempt: int) -> dict[str, Any]:
        with self._lock:
            if not self.connect():
                raise ConnectionError(f"Failed to connect: {self._last_error}")
            try:
                payload = json.dumps({"type": command, "params": params or {}})
                logger.debug("→ %s (attempt %d)", command, attempt + 1)
                self.socket.settimeout(10)
                self.socket.sendall(payload.encode("utf-8"))
                raw = self._receive_response(command)
                response = json.loads(raw.decode("utf-8"))
                # Normalise: top-level success=false
                if response.get("success") is False:
                    err = response.get("error") or response.get("message", "Unknown error")
                    return {"status": "error", "error": err}
                # Normalise: status=success but nested result has success=false
                if response.get("status") == "success":
                    inner = response.get("result", {})
                    if isinstance(inner, dict) and inner.get("success") is False:
                        err = inner.get("error") or inner.get("message", "Unknown error")
                        return {"status": "error", "error": err}
                return response
            finally:
                self._close_socket_unsafe()


# ─── Singleton ────────────────────────────────────────────────────────────────

_connection: UnrealConnection | None = None
_connection_lock = threading.Lock()


def get_connection() -> UnrealConnection:
    global _connection
    with _connection_lock:
        if _connection is None:
            _connection = UnrealConnection()
        return _connection


def reset_connection():
    global _connection
    with _connection_lock:
        if _connection:
            _connection.disconnect()
            _connection = None


# ─── Public helpers ───────────────────────────────────────────────────────────

def send_command(command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a named command to the C++ plugin and return its response dict."""
    return get_connection().send_command(command, params)


def _wrap_script(script: str) -> str:
    """
    Wrap a user script so that any *runtime* exception is reported as structured
    JSON (with a full traceback) on stdout, instead of the script dying silently
    before it prints its result.

    The original script is exec'd from a string literal (not textually indented),
    so multi-line string literals inside it are preserved and traceback line
    numbers stay meaningful. Our error record carries an "_exception" marker so
    execute_python can promote it to a hard error rather than a normal result.
    """
    src = textwrap.dedent(script)
    return (
        "import json as __bridge_json\n"
        "import traceback as __bridge_tb\n"
        f"__bridge_src = {src!r}\n"
        "try:\n"
        "    exec(compile(__bridge_src, '<mcp-script>', 'exec'), {})\n"
        "except Exception as __bridge_e:\n"
        "    print(__bridge_json.dumps({"
        '"success": False, "_exception": True, '
        '"error": type(__bridge_e).__name__ + ": " + str(__bridge_e), '
        '"traceback": __bridge_tb.format_exc()'
        "}))\n"
    )


def execute_python(script: str, timeout_hint: str = "default") -> dict[str, Any]:
    """
    Run a Python script inside the live Unreal Editor via the execute_python
    C++ command.  The script should end with:
        import json; print(json.dumps(result))
    so the bridge can parse the structured return value.

    The script is wrapped so that an unhandled exception inside the editor is
    returned as {"status": "error", "error": "<Type>: <msg>", "traceback": ...}
    rather than a silent null result.
    """
    response = send_command("execute_python", {"script": _wrap_script(script)})
    if response.get("status") == "error":
        return response
    # The C++ handler returns {"status":"success","result":{"output":"...","result":{...}}}
    result_obj = response.get("result", {})
    parsed = result_obj.get("result")  # pre-parsed JSON if C++ did it
    if parsed is None:
        # Fall back: parse the last JSON line of output (scan from the end).
        output: str = result_obj.get("output", "")
        for line in reversed([l.strip() for l in output.splitlines() if l.strip()]):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    # A runtime exception from the wrapper → surface as a hard error with traceback.
    if isinstance(parsed, dict) and parsed.get("_exception"):
        return {
            "status": "error",
            "error": parsed.get("error", "Script raised an exception"),
            "traceback": parsed.get("traceback", ""),
        }
    if parsed is not None:
        return {"status": "success", "result": parsed}
    return {"status": "success", "result": None, "output": result_obj.get("output", "")}


def not_connected_error() -> dict[str, Any]:
    return {"success": False, "message": "Not connected to Unreal Engine"}
