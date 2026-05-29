"""
Spline and Chaos vehicle tools.
Splines are created/edited via execute_python (USplineComponent API).
Vehicle spawning uses the unreal Python API; spline-follow wiring attaches a
reusable Blueprint component (BP_SplineFollower from Content/DMS_Toolkit).
"""

from __future__ import annotations
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
import bridge

logger = logging.getLogger("unreal_dms.spline_vehicle")

# Path to the reusable spline-follower Blueprint created in Phase 2
BP_SPLINE_FOLLOWER = "/Game/DMS_Toolkit/BP_SplineFollower"


def register(mcp: FastMCP):

    # ─── Spline tools ─────────────────────────────────────────────────────────

    @mcp.tool()
    def create_spline_actor(
        name: str,
        location: list[float] = None,
        closed: bool = False,
    ) -> dict[str, Any]:
        """
        Spawn an Actor with a SplineComponent in the current level.
        Returns the actor name and the path to its SplineComponent.
        """
        script = f"""
import unreal, json
world = unreal.EditorLevelLibrary.get_editor_world()
actor = unreal.EditorActorSubsystem().spawn_actor_from_class(
    unreal.Actor.static_class(),
    unreal.Vector(*{repr(location or [0, 0, 0])}),
)
actor.set_actor_label({repr(name)})
spline = unreal.SplineComponent()
actor.add_instance_component(spline)
spline.register_component()
spline.set_editor_property("is_closed_loop", {repr(closed)})
print(json.dumps({{"success": True, "actor": actor.get_name()}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def add_spline_points(
        spline_actor_name: str,
        points: list[list[float]],
        coordinate_space: str = "world",
    ) -> dict[str, Any]:
        """
        Append a list of [x, y, z] points to a spline actor's SplineComponent.
        coordinate_space: 'world' | 'local'.
        """
        space = "unreal.SplineCoordinateSpace.WORLD" if coordinate_space == "world" else "unreal.SplineCoordinateSpace.LOCAL"
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(spline_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Spline actor not found"}}))
else:
    spline = actor.get_component_by_class(unreal.SplineComponent)
    if spline is None:
        print(json.dumps({{"success": False, "error": "No SplineComponent on actor"}}))
    else:
        pts = {repr(points)}
        for pt in pts:
            spline.add_point(unreal.SplinePoint(location=unreal.Vector(*pt)), {space})
        unreal.EditorLevelLibrary.mark_level_as_changed()
        print(json.dumps({{"success": True, "point_count": spline.get_number_of_spline_points()}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_spline_point(
        spline_actor_name: str,
        index: int,
        location: list[float],
        arrive_tangent: list[float] = None,
        leave_tangent: list[float] = None,
        coordinate_space: str = "world",
    ) -> dict[str, Any]:
        """Move a spline point at index to a new location (and optionally new tangents)."""
        space = "unreal.SplineCoordinateSpace.WORLD" if coordinate_space == "world" else "unreal.SplineCoordinateSpace.LOCAL"
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(spline_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Spline actor not found"}}))
else:
    spline = actor.get_component_by_class(unreal.SplineComponent)
    spline.set_location_at_spline_point({index}, unreal.Vector(*{repr(location)}), {space})
    if {repr(arrive_tangent)} is not None:
        spline.set_tangents_at_spline_point({index}, unreal.Vector(*{repr(arrive_tangent or location)}), unreal.Vector(*{repr(leave_tangent or location)}), {space})
    unreal.EditorLevelLibrary.mark_level_as_changed()
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def get_spline_info(spline_actor_name: str) -> dict[str, Any]:
        """Return the spline point count, total length, and all point locations."""
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(spline_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    spline = actor.get_component_by_class(unreal.SplineComponent)
    n = spline.get_number_of_spline_points()
    pts = [list(spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)) for i in range(n)]
    print(json.dumps({{
        "success": True,
        "point_count": n,
        "length_cm": spline.get_spline_length(),
        "closed": spline.get_editor_property("is_closed_loop"),
        "points": pts,
    }}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def clear_spline_points(spline_actor_name: str) -> dict[str, Any]:
        """Remove all points from a spline actor's SplineComponent."""
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(spline_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    spline = actor.get_component_by_class(unreal.SplineComponent)
    spline.clear_spline_points()
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    # ─── Chaos vehicle tools ──────────────────────────────────────────────────

    @mcp.tool()
    def spawn_chaos_vehicle(
        name: str,
        blueprint_path: str,
        location: list[float] = None,
        rotation: list[float] = None,
    ) -> dict[str, Any]:
        """
        Spawn a Chaos Wheeled Vehicle Blueprint actor.
        blueprint_path: e.g. '/Game/Vehicles/BP_SportsCar'.
        """
        script = f"""
import unreal, json
bp_class = unreal.load_asset({repr(blueprint_path)})
if bp_class is None:
    print(json.dumps({{"success": False, "error": "Blueprint not found: {blueprint_path}"}}))
else:
    loc = unreal.Vector(*{repr(location or [0, 0, 0])})
    rot = unreal.Rotator(*{repr(rotation or [0, 0, 0])})
    actor = unreal.EditorActorSubsystem().spawn_actor_from_object(bp_class.generated_class, loc, rot)
    actor.set_actor_label({repr(name)})
    print(json.dumps({{"success": True, "actor": actor.get_name()}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def configure_vehicle(
        vehicle_actor_name: str,
        max_speed_kmh: float = 120.0,
        mass_kg: float = 1500.0,
        engine_torque: float = 300.0,
    ) -> dict[str, Any]:
        """Configure basic Chaos vehicle movement properties on a spawned vehicle actor."""
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(vehicle_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    comp = actor.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
    if comp is None:
        print(json.dumps({{"success": False, "error": "No ChaosWheeledVehicleMovementComponent"}}))
    else:
        # Engine setup
        engine = comp.get_editor_property("engine_setup")
        engine.set_editor_property("max_torque", {engine_torque})
        comp.set_editor_property("engine_setup", engine)
        comp.set_editor_property("mass", {mass_kg})
        print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def attach_vehicle_to_spline(
        vehicle_actor_name: str,
        spline_actor_name: str,
        speed_kmh: float = 60.0,
    ) -> dict[str, Any]:
        """
        Wire a vehicle actor to follow a spline by attaching the BP_SplineFollower
        Blueprint component and pointing it at the given spline actor.
        Requires BP_SplineFollower to exist at Content/DMS_Toolkit/.
        """
        script = f"""
import unreal, json
actors = {{a.get_name(): a for a in unreal.EditorActorSubsystem().get_all_level_actors()}}
vehicle = actors.get({repr(vehicle_actor_name)})
spline_actor = actors.get({repr(spline_actor_name)})
if vehicle is None or spline_actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    bp = unreal.load_asset({repr(BP_SPLINE_FOLLOWER)})
    if bp is None:
        print(json.dumps({{"success": False, "error": "BP_SplineFollower not found at {BP_SPLINE_FOLLOWER}. Complete Phase 2 first."}}))
    else:
        comp_class = bp.generated_class
        comp = vehicle.add_component_by_class(comp_class, False, unreal.Transform(), False)
        comp.set_editor_property("target_spline", spline_actor)
        comp.set_editor_property("follow_speed", {speed_kmh} / 3.6)  # convert to m/s
        comp.register_component()
        print(json.dumps({{"success": True, "component": comp.get_name()}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_vehicle_follow_speed(
        vehicle_actor_name: str, speed_kmh: float
    ) -> dict[str, Any]:
        """Adjust the follow speed (km/h) of the BP_SplineFollower component on a vehicle."""
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
vehicle = next((a for a in actors if a.get_name() == {repr(vehicle_actor_name)}), None)
if vehicle is None:
    print(json.dumps({{"success": False, "error": "Vehicle not found"}}))
else:
    # Find the SplineFollower component by class name heuristic
    comp = None
    for c in vehicle.get_components_by_class(unreal.ActorComponent):
        if "SplineFollower" in c.get_class().get_name():
            comp = c
            break
    if comp is None:
        print(json.dumps({{"success": False, "error": "No SplineFollower component found"}}))
    else:
        comp.set_editor_property("follow_speed", {speed_kmh} / 3.6)
        print(json.dumps({{"success": True, "speed_kmh": {speed_kmh}}}))
"""
        return bridge.execute_python(script)
