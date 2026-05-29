"""
Core tools: actors, levels, assets, editor control, and the execute_python escape hatch.
Ported from flopperam/unreal-engine-mcp and extended with DMS-specific editor tools.
"""

from __future__ import annotations
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
import bridge
from helpers.actor_name_manager import safe_spawn_actor, safe_delete_actor

logger = logging.getLogger("unreal_dms.core")


def register(mcp: FastMCP):

    # ─── Actor management ─────────────────────────────────────────────────────

    @mcp.tool()
    def get_actors_in_level(random_string: str = "") -> dict[str, Any]:
        """Get a list of all actors in the current level."""
        return bridge.send_command("get_actors_in_level", {})

    @mcp.tool()
    def find_actors_by_name(pattern: str) -> dict[str, Any]:
        """Find actors whose names match a glob/substring pattern."""
        return bridge.send_command("find_actors_by_name", {"pattern": pattern})

    @mcp.tool()
    def spawn_actor(
        name: str,
        actor_type: str = "StaticMeshActor",
        location: list[float] = None,
        rotation: list[float] = None,
        scale: list[float] = None,
        static_mesh: str = "/Engine/BasicShapes/Cube.Cube",
    ) -> dict[str, Any]:
        """
        Spawn an actor in the current level.
        actor_type: UClass name (e.g. 'StaticMeshActor', 'PointLight', 'CameraActor').
        """
        params: dict[str, Any] = {
            "name": name,
            "type": actor_type,
            "location": location or [0, 0, 0],
            "rotation": rotation or [0, 0, 0],
            "scale": scale or [1, 1, 1],
            "static_mesh": static_mesh,
        }
        return safe_spawn_actor(bridge.get_connection(), params)

    @mcp.tool()
    def delete_actor(name: str) -> dict[str, Any]:
        """Delete an actor by name."""
        return safe_delete_actor(bridge.get_connection(), name)

    @mcp.tool()
    def set_actor_transform(
        name: str,
        location: list[float] = None,
        rotation: list[float] = None,
        scale: list[float] = None,
    ) -> dict[str, Any]:
        """Set the world transform of an actor (location cm, rotation degrees, scale)."""
        params: dict[str, Any] = {"name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale
        return bridge.send_command("set_actor_transform", params)

    @mcp.tool()
    def get_actor_property(actor_name: str, property_name: str) -> dict[str, Any]:
        """Read a named property from an actor using the unreal Python API."""
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
target = next((a for a in actors if a.get_name() == {repr(actor_name)}), None)
if target is None:
    print(json.dumps({{"success": False, "error": "Actor not found: {actor_name}"}}))
else:
    try:
        val = target.get_editor_property({repr(property_name)})
        print(json.dumps({{"success": True, "value": str(val)}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_actor_property(
        actor_name: str, property_name: str, property_value: Any
    ) -> dict[str, Any]:
        """
        Set a named property on an actor using the unreal Python API.
        property_value is passed as a JSON-serialisable value and coerced in-editor.
        """
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
target = next((a for a in actors if a.get_name() == {repr(actor_name)}), None)
if target is None:
    print(json.dumps({{"success": False, "error": "Actor not found: {actor_name}"}}))
else:
    try:
        target.set_editor_property({repr(property_name)}, {repr(property_value)})
        print(json.dumps({{"success": True}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def attach_actor_to_socket(
        child_actor: str, parent_actor: str, socket_name: str = "None"
    ) -> dict[str, Any]:
        """Attach child_actor to a socket on parent_actor."""
        script = f"""
import unreal, json
sub = unreal.EditorActorSubsystem()
actors = sub.get_all_level_actors()
by_name = {{a.get_name(): a for a in actors}}
child = by_name.get({repr(child_actor)})
parent = by_name.get({repr(parent_actor)})
if not child or not parent:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    child.attach_to_actor(parent, unreal.AttachmentTransformRules.KEEP_WORLD_TRANSFORM)
    if {repr(socket_name)} != "None":
        child.attach_to_component(
            parent.root_component,
            unreal.AttachmentTransformRules.KEEP_WORLD_TRANSFORM,
            {repr(socket_name)},
        )
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    # ─── Level management ─────────────────────────────────────────────────────

    @mcp.tool()
    def load_level(level_path: str) -> dict[str, Any]:
        """Load a level by asset path (e.g. '/Game/Maps/MyLevel')."""
        script = f"""
import unreal, json
sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ok = sub.load_level({repr(level_path)})
print(json.dumps({{"success": ok}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def save_current_level() -> dict[str, Any]:
        """Save the currently open level."""
        script = """
import unreal, json
sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ok = sub.save_current_level()
print(json.dumps({"success": ok}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def get_current_level_path() -> dict[str, Any]:
        """Return the asset path of the currently open level."""
        script = """
import unreal, json
world = unreal.EditorLevelLibrary.get_editor_world()
print(json.dumps({"success": True, "path": world.get_path_name() if world else None}))
"""
        return bridge.execute_python(script)

    # ─── Asset management ─────────────────────────────────────────────────────

    @mcp.tool()
    def list_assets(directory: str = "/Game/", recursive: bool = True) -> dict[str, Any]:
        """List all assets under a content directory."""
        script = f"""
import unreal, json
assets = unreal.EditorAssetLibrary.list_assets({repr(directory)}, recursive={repr(recursive)})
print(json.dumps({{"success": True, "assets": list(assets)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def duplicate_asset(source_path: str, destination_path: str) -> dict[str, Any]:
        """Duplicate an asset to a new path."""
        script = f"""
import unreal, json
ok = unreal.EditorAssetLibrary.duplicate_asset({repr(source_path)}, {repr(destination_path)})
print(json.dumps({{"success": bool(ok), "path": {repr(destination_path)} if ok else None}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def delete_asset(asset_path: str) -> dict[str, Any]:
        """Delete an asset by content path."""
        script = f"""
import unreal, json
ok = unreal.EditorAssetLibrary.delete_asset({repr(asset_path)})
print(json.dumps({{"success": bool(ok)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def get_asset_info(asset_path: str) -> dict[str, Any]:
        """Return metadata about an asset (class, path, package)."""
        script = f"""
import unreal, json
reg = unreal.AssetRegistryHelpers.get_asset_registry()
data = reg.get_asset_by_object_path({repr(asset_path)})
if data.is_valid():
    print(json.dumps({{
        "success": True,
        "asset_class": str(data.asset_class_path.asset_name),
        "package_name": str(data.package_name),
        "object_path": str(data.get_full_name()),
    }}))
else:
    print(json.dumps({{"success": False, "error": "Asset not found"}}))
"""
        return bridge.execute_python(script)

    # ─── Editor control ───────────────────────────────────────────────────────

    @mcp.tool()
    def run_console_command(command: str) -> dict[str, Any]:
        """Execute a console command in the Unreal Editor."""
        script = f"""
import unreal, json
unreal.SystemLibrary.execute_console_command(None, {repr(command)})
print(json.dumps({{"success": True, "command": {repr(command)}}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def play_in_editor(mode: str = "selected_viewport") -> dict[str, Any]:
        """Start a Play-In-Editor session. mode: 'selected_viewport' | 'new_editor_window' | 'simulate'."""
        script = f"""
import unreal, json
settings = unreal.EditorPlayInSettings()
mode_map = {{
    "selected_viewport": unreal.PlayModeType.PLAY_MODE_IN_VIEWPORT,
    "new_editor_window": unreal.PlayModeType.PLAY_MODE_IN_NEW_PROCESS,
    "simulate": unreal.PlayModeType.PLAY_MODE_SIMULATE,
}}
unreal.UnrealEditorSubsystem().play_from_here(
    unreal.Vector(0,0,0), mode_map.get({repr(mode)}, unreal.PlayModeType.PLAY_MODE_IN_VIEWPORT)
)
print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def stop_play_in_editor() -> dict[str, Any]:
        """Stop the current Play-In-Editor session."""
        script = """
import unreal, json
unreal.UnrealEditorSubsystem().request_end_play_map()
print(json.dumps({"success": True}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def take_viewport_screenshot(output_path: str) -> dict[str, Any]:
        """Capture a screenshot of the active editor viewport to disk."""
        script = f"""
import unreal, json
unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, {repr(output_path)})
print(json.dumps({{"success": True, "path": {repr(output_path)}}}))
"""
        return bridge.execute_python(script)

    # ─── Escape hatch ─────────────────────────────────────────────────────────

    @mcp.tool()
    def execute_python(script: str) -> dict[str, Any]:
        """
        Run arbitrary Python code inside the live Unreal Editor.
        The script has access to the 'unreal' module.
        End with:  import json; print(json.dumps(result))
        to get a structured return value.
        """
        return bridge.execute_python(script)
