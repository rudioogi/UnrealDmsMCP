"""
Shared pytest fixtures for the Unreal DMS MCP server test suite.
"""

import json
import socket
import threading
import time
import pytest
import sys
import os

# Make the Python package importable from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Python"))


class MockUnrealPlugin:
    """
    A fake TCP server that speaks the UnrealMCP JSON command/response protocol.
    Binds to an ephemeral port; feed custom responses via `set_response()`.
    """

    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self.port: int = self._sock.getsockname()[1]
        self._responses: list[dict] = []
        self._received: list[dict] = []
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def set_response(self, response: dict):
        """Queue a response to return for the next command."""
        self._responses.append(response)

    def set_responses(self, responses: list[dict]):
        self._responses.extend(responses)

    @property
    def received(self) -> list[dict]:
        return list(self._received)

    def last_received(self) -> dict | None:
        return self._received[-1] if self._received else None

    def _serve(self):
        self._sock.settimeout(10)
        try:
            while True:
                try:
                    conn, _ = self._sock.accept()
                except socket.timeout:
                    return
                with conn:
                    conn.settimeout(5)
                    data = b""
                    while True:
                        try:
                            chunk = conn.recv(4096)
                        except socket.timeout:
                            break
                        if not chunk:
                            break
                        data += chunk
                        try:
                            parsed = json.loads(data.decode())
                            self._received.append(parsed)
                            resp = self._responses.pop(0) if self._responses else {
                                "status": "success",
                                "result": {"success": True},
                            }
                            conn.sendall(json.dumps(resp).encode())
                            data = b""
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

    def close(self):
        self._sock.close()


@pytest.fixture
def mock_plugin():
    server = MockUnrealPlugin()
    yield server
    server.close()


@pytest.fixture(autouse=True)
def reset_bridge_connection(monkeypatch):
    """Ensure bridge singleton is reset between tests."""
    import bridge
    bridge.reset_connection()
    yield
    bridge.reset_connection()


@pytest.fixture
def plugin_port(mock_plugin, monkeypatch):
    """Configure bridge to connect to the mock plugin's port."""
    import bridge
    monkeypatch.setattr(bridge, "UNREAL_PORT", mock_plugin.port)
    monkeypatch.setattr(bridge, "UNREAL_HOST", "127.0.0.1")
    return mock_plugin.port
