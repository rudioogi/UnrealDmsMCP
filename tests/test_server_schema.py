"""
Layer 1: Server boot & protocol tests.
No Unreal Editor required — validates tool registration, schemas, and lifecycle.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Python"))


def _load_mcp_app():
    """Import the FastMCP app without starting it."""
    # Prevent actual Unreal connection during import
    from unittest.mock import patch
    with patch("bridge.get_connection"):
        from mcp.server.fastmcp import FastMCP
        import importlib
        # Re-import to ensure tools are registered
        import unreal_dms_mcp_server as srv
        return srv.mcp


class TestToolRegistration:
    """All expected tools must be registered with valid schemas."""

    # Minimum required tools per module
    REQUIRED_TOOLS = {
        # core
        "get_actors_in_level", "find_actors_by_name", "spawn_actor", "delete_actor",
        "set_actor_transform", "get_actor_property", "set_actor_property",
        "load_level", "save_current_level", "list_assets", "execute_python",
        # blueprint
        "create_blueprint", "add_component_to_blueprint", "compile_blueprint",
        "read_blueprint_content", "add_blueprint_node", "connect_blueprint_nodes",
        "create_blueprint_variable",
        # mesh_material
        "create_material_instance", "set_material_scalar_param",
        "set_material_vector_param", "set_material_texture_param",
        "apply_material_to_actor", "create_glass_material_instance",
        # spline_vehicle
        "create_spline_actor", "add_spline_points", "spawn_chaos_vehicle",
        "attach_vehicle_to_spline",
        # metahuman
        "spawn_metahuman", "attach_accessory", "seat_metahuman_in_vehicle",
        "swap_accessory_asset",
        # animation
        "create_level_sequence", "bind_actor_to_sequence", "keyframe_control",
        "apply_behavior_preset", "list_dms_presets",
        # capture
        "export_face_landmarks", "take_screenshot", "run_capture_batch",
        "export_ground_truth_labels",
    }

    def test_all_required_tools_registered(self):
        """Every tool in REQUIRED_TOOLS must appear in tools/list."""
        mcp = _load_mcp_app()
        registered = {t.name for t in mcp._tool_manager.list_tools()}
        missing = self.REQUIRED_TOOLS - registered
        assert not missing, f"Missing tools: {sorted(missing)}"

    def test_all_tools_have_descriptions(self):
        mcp = _load_mcp_app()
        no_desc = [
            t.name for t in mcp._tool_manager.list_tools()
            if not t.description or not t.description.strip()
        ]
        assert not no_desc, f"Tools without descriptions: {no_desc}"

    def test_all_tools_have_valid_input_schema(self):
        mcp = _load_mcp_app()
        for tool in mcp._tool_manager.list_tools():
            schema = tool.parameters
            assert isinstance(schema, dict), f"{tool.name}: parameters must be a dict"
            assert schema.get("type") == "object", f"{tool.name}: schema type must be 'object'"

    def test_tool_count_is_reasonable(self):
        mcp = _load_mcp_app()
        tools = mcp._tool_manager.list_tools()
        assert len(tools) >= 30, f"Expected >= 30 tools, found {len(tools)}"


class TestServerLifecycle:
    """Server must start cleanly and handle missing Unreal gracefully."""

    def test_server_import_succeeds(self):
        """Server module imports without errors even when Unreal is not running."""
        from unittest.mock import patch
        with patch("bridge.get_connection"):
            import unreal_dms_mcp_server  # noqa: F401

    def test_server_name(self):
        mcp = _load_mcp_app()
        assert mcp.name == "UnrealDMS"

    def test_execute_python_tool_exists(self):
        """The execute_python escape-hatch tool must always be registered."""
        mcp = _load_mcp_app()
        names = {t.name for t in mcp._tool_manager.list_tools()}
        assert "execute_python" in names


class TestDMSPresets:
    """DMS behaviour presets must be internally consistent."""

    def test_presets_have_required_keys(self):
        from tools.animation_tools import DMS_PRESETS
        for name, tracks in DMS_PRESETS.items():
            assert tracks, f"Preset '{name}' has no tracks"
            for control_name, keyframes in tracks:
                assert control_name, f"Preset '{name}' has empty control name"
                for frame, vtype, value in keyframes:
                    assert isinstance(frame, int), f"Frame must be int in '{name}'"
                    assert vtype in ("float", "bool", "rotator", "transform"), \
                        f"Unknown value_type '{vtype}' in preset '{name}'"

    def test_alert_preset_exists(self):
        from tools.animation_tools import DMS_PRESETS
        assert "alert" in DMS_PRESETS

    def test_drowsy_preset_exists(self):
        from tools.animation_tools import DMS_PRESETS
        assert "drowsy" in DMS_PRESETS
