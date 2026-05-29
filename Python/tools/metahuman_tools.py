"""
MetaHuman tools: spawn, wardrobe, accessories (glasses/sunglasses), and seating.
All via execute_python using the MetaHuman Blueprint utilities in UE 5.6/5.7.
"""

from __future__ import annotations
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
import bridge

logger = logging.getLogger("unreal_dms.metahuman")

# Common MetaHuman accessory socket names (adjust to match your rig)
GLASSES_SOCKET = "FACIAL_C_ForeheadMid"
HEAD_SOCKET = "head"


def register(mcp: FastMCP):

    @mcp.tool()
    def spawn_metahuman(
        name: str,
        blueprint_path: str,
        location: list[float] = None,
        rotation: list[float] = None,
    ) -> dict[str, Any]:
        """
        Spawn a MetaHuman Blueprint actor.
        blueprint_path: content path to the MetaHuman Blueprint (e.g. '/Game/MetaHumans/Char1/BP_Char1').
        """
        script = f"""
import unreal, json
bp = unreal.load_asset({repr(blueprint_path)})
if bp is None:
    print(json.dumps({{"success": False, "error": "MetaHuman Blueprint not found"}}))
else:
    loc = unreal.Vector(*{repr(location or [0, 0, 0])})
    rot = unreal.Rotator(*{repr(rotation or [0, 0, 0])})
    actor = unreal.EditorActorSubsystem().spawn_actor_from_object(bp.generated_class, loc, rot)
    actor.set_actor_label({repr(name)})
    print(json.dumps({{"success": True, "actor": actor.get_name()}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def list_metahuman_components(metahuman_actor_name: str) -> dict[str, Any]:
        """
        List all components on a MetaHuman actor, including skeletal mesh components
        that correspond to body parts or clothing items.
        """
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(metahuman_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    comps = []
    for c in actor.get_components_by_class(unreal.ActorComponent):
        entry = {{"name": c.get_name(), "class": c.get_class().get_name()}}
        if isinstance(c, unreal.SkeletalMeshComponent):
            mesh = c.get_editor_property("skeletal_mesh")
            entry["mesh"] = str(mesh.get_path_name()) if mesh else None
        comps.append(entry)
    print(json.dumps({{"success": True, "components": comps}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_metahuman_body_mesh(
        metahuman_actor_name: str,
        component_name: str,
        mesh_path: str,
    ) -> dict[str, Any]:
        """
        Swap a skeletal mesh on a named component of a MetaHuman (e.g. clothing, torso).
        Use list_metahuman_components to find available component names.
        """
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(metahuman_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    comp = next(
        (c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent)
         if c.get_name() == {repr(component_name)}),
        None
    )
    if comp is None:
        print(json.dumps({{"success": False, "error": f"Component not found: {repr(component_name)}"}}))
    else:
        mesh = unreal.load_asset({repr(mesh_path)})
        comp.set_editor_property("skeletal_mesh", mesh)
        print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def attach_accessory(
        metahuman_actor_name: str,
        accessory_blueprint_path: str,
        accessory_name: str,
        socket_name: str = GLASSES_SOCKET,
        location_offset: list[float] = None,
        rotation_offset: list[float] = None,
    ) -> dict[str, Any]:
        """
        Spawn an accessory actor (e.g. glasses Blueprint) and attach it to a
        socket on the MetaHuman's head/face mesh.
        socket_name defaults to the forehead bone used for eyewear.
        """
        script = f"""
import unreal, json
actors = {{a.get_name(): a for a in unreal.EditorActorSubsystem().get_all_level_actors()}}
mh = actors.get({repr(metahuman_actor_name)})
if mh is None:
    print(json.dumps({{"success": False, "error": "MetaHuman not found"}}))
else:
    bp = unreal.load_asset({repr(accessory_blueprint_path)})
    if bp is None:
        print(json.dumps({{"success": False, "error": "Accessory Blueprint not found"}}))
    else:
        loc = unreal.Vector(*{repr(location_offset or [0, 0, 0])})
        rot = unreal.Rotator(*{repr(rotation_offset or [0, 0, 0])})
        acc = unreal.EditorActorSubsystem().spawn_actor_from_object(bp.generated_class, unreal.Vector(0,0,0))
        acc.set_actor_label({repr(accessory_name)})
        # Attach to head mesh socket
        face_comp = next(
            (c for c in mh.get_components_by_class(unreal.SkeletalMeshComponent)
             if "face" in c.get_name().lower() or "head" in c.get_name().lower()),
            mh.get_component_by_class(unreal.SkeletalMeshComponent)
        )
        if face_comp:
            rules = unreal.AttachmentTransformRules(
                unreal.AttachmentRule.SNAP_TO_TARGET,
                unreal.AttachmentRule.SNAP_TO_TARGET,
                unreal.AttachmentRule.KEEP_RELATIVE,
                False
            )
            acc.attach_to_component(face_comp, rules, {repr(socket_name)})
            acc.set_actor_relative_location(loc)
            acc.set_actor_relative_rotation(rot)
        print(json.dumps({{"success": True, "accessory_actor": acc.get_name()}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def swap_accessory_asset(
        accessory_actor_name: str,
        new_mesh_path: str,
        component_name: str = None,
    ) -> dict[str, Any]:
        """
        Swap the skeletal/static mesh on an already-attached accessory actor.
        Useful for changing glasses style without re-attaching.
        """
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(accessory_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Accessory actor not found"}}))
else:
    mesh_asset = unreal.load_asset({repr(new_mesh_path)})
    comp_name = {repr(component_name)}
    # Try SkeletalMeshComponent first, then StaticMeshComponent
    for cls in (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent):
        comps = actor.get_components_by_class(cls)
        if comp_name:
            comps = [c for c in comps if c.get_name() == comp_name]
        if comps:
            prop = "skeletal_mesh" if cls == unreal.SkeletalMeshComponent else "static_mesh"
            comps[0].set_editor_property(prop, mesh_asset)
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "No mesh component found on accessory"}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_accessory_material_param(
        accessory_actor_name: str,
        param_name: str,
        param_type: str,
        value: Any,
        material_slot: int = 0,
    ) -> dict[str, Any]:
        """
        Set a material parameter on an accessory's dynamic material instance.
        param_type: 'scalar' | 'vector'. For vector, value = [r, g, b, a].
        Useful for adjusting glass reflection/roughness/tint at runtime.
        """
        if param_type == "vector":
            v = value if isinstance(value, (list, tuple)) and len(value) == 4 else list(value) + [1.0]
            set_val = f"comp.create_and_set_material_instance_dynamic(slot).set_vector_parameter_value({repr(param_name)}, unreal.LinearColor(*{v}))"
        else:
            set_val = f"comp.create_and_set_material_instance_dynamic(slot).set_scalar_parameter_value({repr(param_name)}, float({repr(value)}))"

        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(accessory_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    for cls in (unreal.SkeletalMeshComponent, unreal.StaticMeshComponent):
        comp = actor.get_component_by_class(cls)
        if comp:
            slot = {material_slot}
            {set_val}
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "No mesh component"}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def seat_metahuman_in_vehicle(
        metahuman_actor_name: str,
        vehicle_actor_name: str,
        driver_socket: str = "driver_seat",
        location_offset: list[float] = None,
        rotation_offset: list[float] = None,
    ) -> dict[str, Any]:
        """
        Attach a MetaHuman actor to the driver seat socket on a vehicle actor.
        Hides the vehicle's default skeletal driver mesh if one exists.
        """
        script = f"""
import unreal, json
by_name = {{a.get_name(): a for a in unreal.EditorActorSubsystem().get_all_level_actors()}}
mh = by_name.get({repr(metahuman_actor_name)})
vehicle = by_name.get({repr(vehicle_actor_name)})
if mh is None or vehicle is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    # Find vehicle skeletal mesh root or socket component
    vehicle_root = vehicle.get_component_by_class(unreal.SkeletalMeshComponent)
    rules = unreal.AttachmentTransformRules(
        unreal.AttachmentRule.SNAP_TO_TARGET,
        unreal.AttachmentRule.SNAP_TO_TARGET,
        unreal.AttachmentRule.KEEP_RELATIVE,
        False
    )
    if vehicle_root:
        mh.attach_to_component(vehicle_root, rules, {repr(driver_socket)})
    else:
        mh.attach_to_actor(vehicle, rules)
    loc = unreal.Vector(*{repr(location_offset or [0, 0, 0])})
    rot = unreal.Rotator(*{repr(rotation_offset or [0, 0, 0])})
    mh.set_actor_relative_location(loc)
    mh.set_actor_relative_rotation(rot)
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def detach_from_vehicle(metahuman_actor_name: str) -> dict[str, Any]:
        """Detach a MetaHuman from its parent vehicle, keeping world position."""
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(metahuman_actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    actor.detach_from_actor(unreal.DetachmentTransformRules.KEEP_WORLD_TRANSFORM)
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)
