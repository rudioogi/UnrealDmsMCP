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
        name: str = None,
        actor_type: str = "StaticMeshActor",
        location: list[float] = None,
        rotation: list[float] = None,
        scale: list[float] = None,
        static_mesh: str = "/Engine/BasicShapes/Cube.Cube",
        actor_name: str = None,
    ) -> dict[str, Any]:
        """
        Spawn an actor in the current level.
        actor_type: UClass name (e.g. 'StaticMeshActor', 'PointLight', 'CameraActor').
        Accepts 'name' or 'actor_name' interchangeably.
        """
        name = name or actor_name
        if not name:
            return {"status": "error", "error": "Missing required parameter: 'name'"}
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
    def delete_actor(name: str = None, actor_name: str = None) -> dict[str, Any]:
        """Delete an actor by name. Accepts 'name' or 'actor_name' interchangeably."""
        name = name or actor_name
        if not name:
            return {"status": "error", "error": "Missing required parameter: 'name'"}
        return safe_delete_actor(bridge.get_connection(), name)

    @mcp.tool()
    def set_actor_transform(
        name: str = None,
        location: list[float] = None,
        rotation: list[float] = None,
        scale: list[float] = None,
        actor_name: str = None,
    ) -> dict[str, Any]:
        """Set the world transform of an actor (location cm, rotation degrees, scale). Accepts 'name' or 'actor_name'."""
        name = name or actor_name
        if not name:
            return {"status": "error", "error": "Missing required parameter: 'name'"}
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
    socket = {repr(socket_name)}
    if socket and socket != "None":
        child.attach_to_component(
            parent.root_component, socket,
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            False,
        )
    else:
        child.attach_to_actor(
            parent, "",
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            False,
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
    def take_viewport_screenshot(
        output_path: str,
        width: int = 1920,
        height: int = 1080,
    ) -> dict[str, Any]:
        """
        Capture the active level editor viewport synchronously to disk.
        Always reflects the current scene state — use this for visual confirmation after
        scene changes. The image dimensions match the actual viewport size regardless of
        the width/height hints.
        output_path: absolute file path for the PNG.
        """
        return bridge.send_command(
            "take_viewport_screenshot",
            {"output_path": output_path, "width": width, "height": height},
        )

    # ─── Editor world geometry ────────────────────────────────────────────────

    @mcp.tool()
    def line_trace(
        start: list[float],
        end: list[float],
        trace_complex: bool = False,
    ) -> dict[str, Any]:
        """
        Cast a line trace in the editor world and return the first blocking hit.
        Uses the Visibility trace channel (TraceTypeQuery1 under default project config).
        start/end: [x, y, z] world coordinates in cm.
        Returns blocking_hit, location, impact_point, impact_normal, and actor name.
        """
        script = f"""
import unreal, json
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
hit = unreal.SystemLibrary.line_trace_single(
    world,
    unreal.Vector(*{repr(start)}),
    unreal.Vector(*{repr(end)}),
    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
    {repr(trace_complex)}, [],
    unreal.DrawDebugTrace.NONE, True,
)
if hit and hit.blocking_hit:
    actor = hit.hit_actor
    print(json.dumps({{
        "success": True, "blocking_hit": True,
        "location": [hit.location.x, hit.location.y, hit.location.z],
        "impact_point": [hit.impact_point.x, hit.impact_point.y, hit.impact_point.z],
        "impact_normal": [hit.impact_normal.x, hit.impact_normal.y, hit.impact_normal.z],
        "actor": actor.get_name() if actor else None,
    }}))
else:
    print(json.dumps({{"success": True, "blocking_hit": False}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def snap_actor_to_floor(
        actor_name: str,
        trace_distance: float = 10000.0,
    ) -> dict[str, Any]:
        """
        Move an actor downward until its base rests on the first collision surface below it.
        Uses a vertical line trace (Visibility channel, trace_complex=True so it hits
        per-poly collision). Returns the final snapped location or an error if no floor
        is found within trace_distance cm.
        """
        script = f"""
import unreal, json
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
by_name = {{a.get_name(): a for a in unreal.EditorActorSubsystem().get_all_level_actors()}}
actor = by_name.get({repr(actor_name)})
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    origin, extent = actor.get_actor_bounds(False)
    dist = {trace_distance}
    hit = unreal.SystemLibrary.line_trace_single(
        world,
        unreal.Vector(origin.x, origin.y, origin.z + dist),
        unreal.Vector(origin.x, origin.y, origin.z - dist),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        True, [actor],
        unreal.DrawDebugTrace.NONE, True,
    )
    if hit and hit.blocking_hit:
        loc = actor.get_actor_location()
        delta_z = hit.impact_point.z + extent.z - origin.z
        actor.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + delta_z), False, False)
        new_loc = actor.get_actor_location()
        print(json.dumps({{
            "success": True,
            "snapped_to": [new_loc.x, new_loc.y, new_loc.z],
        }}))
    else:
        print(json.dumps({{"success": False, "error": "No floor found within trace distance"}}))
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
