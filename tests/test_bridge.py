"""
Layer 2: TCP bridge tests using the MockUnrealPlugin fixture.
No Unreal Editor required — verifies command serialisation, response parsing,
error handling, timeouts, and reconnect behaviour.
"""

import json
import socket
import threading
import time
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Python"))


class TestSendCommand:
    """Bridge must serialise, send, and parse commands correctly."""

    def test_send_command_format(self, mock_plugin, plugin_port):
        """The JSON sent must have 'type' and 'params' keys."""
        import bridge
        mock_plugin.set_response({"status": "success", "result": {"actors": []}})
        bridge.send_command("get_actors_in_level", {})
        received = mock_plugin.last_received()
        assert received is not None
        assert received["type"] == "get_actors_in_level"
        assert "params" in received

    def test_send_command_with_params(self, mock_plugin, plugin_port):
        import bridge
        mock_plugin.set_response({"status": "success", "result": {"actors": []}})
        bridge.send_command("find_actors_by_name", {"pattern": "Vehicle*"})
        received = mock_plugin.last_received()
        assert received["type"] == "find_actors_by_name"
        assert received["params"]["pattern"] == "Vehicle*"

    def test_success_response_returned(self, mock_plugin, plugin_port):
        import bridge
        mock_plugin.set_response({"status": "success", "result": {"actors": ["Actor1"]}})
        resp = bridge.send_command("get_actors_in_level", {})
        assert resp.get("status") == "success"

    def test_error_response_normalised(self, mock_plugin, plugin_port):
        import bridge
        mock_plugin.set_response({
            "status": "success",
            "result": {"success": False, "error": "Actor not found"}
        })
        resp = bridge.send_command("delete_actor", {"name": "Missing"})
        assert resp.get("status") == "error"
        assert "Actor not found" in resp.get("error", "")

    def test_malformed_plugin_response_returns_error(self, mock_plugin, plugin_port):
        """If the plugin sends non-JSON, bridge returns an error dict (no crash)."""
        import bridge
        # Inject a raw non-JSON byte sequence via the mock
        import bridge as br
        # Override the mock to send garbage
        original_responses = mock_plugin._responses
        mock_plugin._responses = []
        # Patch _send_once to simulate a JSON decode failure
        orig = br.UnrealConnection._send_once
        call_count = {"n": 0}

        def broken_send(self, command, params, attempt):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                raise ValueError("Invalid JSON response: test inject")
            return orig(self, command, params, attempt)

        from unittest.mock import patch
        with patch.object(br.UnrealConnection, "_send_once", broken_send):
            resp = br.send_command("get_actors_in_level", {})
        assert "error" in resp


class TestExecutePython:
    """execute_python must parse the last JSON line as the result."""

    def test_execute_python_parses_last_json_line(self, mock_plugin, plugin_port):
        import bridge
        mock_plugin.set_response({
            "status": "success",
            "result": {
                "success": True,
                "output": 'some log\n{"success": true, "actor": "BP_Car"}',
                "result": {"success": True, "actor": "BP_Car"},
            }
        })
        resp = bridge.execute_python("import unreal; print('...')")
        assert resp.get("status") == "success"
        assert resp.get("result", {}).get("actor") == "BP_Car"

    def test_execute_python_non_json_output_ok(self, mock_plugin, plugin_port):
        """When output is not JSON the bridge returns success with result=None."""
        import bridge
        mock_plugin.set_response({
            "status": "success",
            "result": {"success": True, "output": "hello world", "result": None}
        })
        resp = bridge.execute_python("print('hello world')")
        assert resp.get("status") == "success"


class TestReconnect:
    """Bridge must auto-reconnect after a dropped connection."""

    def test_reconnects_after_disconnect(self, mock_plugin, plugin_port):
        import bridge
        # First command succeeds
        mock_plugin.set_response({"status": "success", "result": {"success": True}})
        r1 = bridge.send_command("ping", {})
        assert r1.get("status") == "success"

        # Force disconnect
        bridge.reset_connection()

        # Second command should reconnect and succeed
        mock_plugin.set_response({"status": "success", "result": {"success": True}})
        r2 = bridge.send_command("ping", {})
        assert r2.get("status") == "success"


class TestConnectionRefused:
    """When Unreal is not running, bridge returns a clean error (no exception leaks)."""

    def test_no_unreal_returns_error(self, monkeypatch):
        import bridge
        bridge.reset_connection()
        monkeypatch.setattr(bridge, "UNREAL_PORT", 19999)  # nothing listening here
        monkeypatch.setattr(bridge, "_MAX_RETRIES", 0)
        resp = bridge.send_command("get_actors_in_level", {})
        assert "error" in resp
        assert resp.get("status") == "error"


class TestGracefulDegradation:
    """Server starts and tools surface clean errors when Unreal is disconnected."""

    def test_get_actors_returns_error_not_exception(self, monkeypatch):
        """Tool functions must never raise; they return error dicts."""
        import bridge
        bridge.reset_connection()
        monkeypatch.setattr(bridge, "UNREAL_PORT", 19999)
        monkeypatch.setattr(bridge, "_MAX_RETRIES", 0)
        from tools.core_tools import register
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("test")
        register(mcp)
        # Find get_actors_in_level tool and call it
        tool = next(t for t in mcp._tool_manager.list_tools() if t.name == "get_actors_in_level")
        result = tool.fn()
        assert isinstance(result, dict)
