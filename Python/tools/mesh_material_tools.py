"""
Mesh and material tools.
Static mesh LOD/collision via the C++ bridge; material instance creation and
parameter editing via execute_python (unreal.MaterialInstanceConstant API).
"""

from __future__ import annotations
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
import bridge

logger = logging.getLogger("unreal_dms.mesh_material")


def register(mcp: FastMCP):

    # ─── Static mesh ──────────────────────────────────────────────────────────

    @mcp.tool()
    def set_static_mesh_on_actor(actor_name: str, mesh_path: str) -> dict[str, Any]:
        """Assign a static mesh asset to the first StaticMeshComponent on an actor."""
        script = f"""
import unreal, json
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(actor_name)}), None)
if actor is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    mesh_asset = unreal.load_asset({repr(mesh_path)})
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp:
        comp.set_editor_property("static_mesh", mesh_asset)
        print(json.dumps({{"success": True}}))
    else:
        print(json.dumps({{"success": False, "error": "No StaticMeshComponent found"}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def add_simple_collision(
        static_mesh_path: str,
        collision_type: str = "box",
    ) -> dict[str, Any]:
        """
        Add simple collision to a static mesh asset.
        collision_type: 'box' | 'sphere' | 'capsule' | 'convex'.
        """
        script = f"""
import unreal, json
mesh = unreal.load_asset({repr(static_mesh_path)})
if mesh is None:
    print(json.dumps({{"success": False, "error": "Mesh not found"}}))
else:
    lib = unreal.EditorStaticMeshLibrary
    ctype = {repr(collision_type)}.lower()
    if ctype == "box":
        lib.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.BOX)
    elif ctype == "sphere":
        lib.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.SPHERE)
    elif ctype == "capsule":
        lib.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.SPHYL)
    elif ctype == "convex":
        lib.add_convex_collision(mesh)
    unreal.EditorAssetLibrary.save_asset({repr(static_mesh_path)})
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def get_static_mesh_info(static_mesh_path: str) -> dict[str, Any]:
        """Return LOD count, triangle count, material slots, and collision info for a mesh."""
        script = f"""
import unreal, json
mesh = unreal.load_asset({repr(static_mesh_path)})
if mesh is None:
    print(json.dumps({{"success": False, "error": "Mesh not found"}}))
else:
    lib = unreal.EditorStaticMeshLibrary
    info = {{
        "success": True,
        "lod_count": lib.get_lod_count(mesh),
        "material_slots": [str(s.material_slot_name) for s in mesh.get_editor_property("static_materials")],
    }}
    print(__import__("json").dumps(info))
"""
        return bridge.execute_python(script)

    # ─── Material instances ───────────────────────────────────────────────────

    @mcp.tool()
    def create_material_instance(
        parent_material_path: str, instance_path: str
    ) -> dict[str, Any]:
        """
        Create a MaterialInstanceConstant from a parent material.
        instance_path: desired content path (e.g. '/Game/Materials/MI_Glass').
        """
        script = f"""
import unreal, json
parent = unreal.load_asset({repr(parent_material_path)})
if parent is None:
    print(json.dumps({{"success": False, "error": "Parent material not found"}}))
else:
    factory = unreal.MaterialInstanceConstantFactoryNew()
    factory.set_editor_property("initial_parent", parent)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    pkg, name = {repr(instance_path)}.rsplit("/", 1)
    inst = tools.create_asset(name, pkg, unreal.MaterialInstanceConstant, factory)
    if inst:
        unreal.EditorAssetLibrary.save_asset({repr(instance_path)})
        print(json.dumps({{"success": True, "path": {repr(instance_path)}}}))
    else:
        print(json.dumps({{"success": False, "error": "Failed to create material instance"}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_material_scalar_param(
        instance_path: str, param_name: str, value: float
    ) -> dict[str, Any]:
        """Set a scalar (float) parameter on a MaterialInstanceConstant."""
        script = f"""
import unreal, json
inst = unreal.load_asset({repr(instance_path)})
if inst is None:
    print(json.dumps({{"success": False, "error": "Material instance not found"}}))
else:
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(inst, {repr(param_name)}, float({value}))
    unreal.MaterialEditingLibrary.update_material_instance(inst)
    unreal.EditorAssetLibrary.save_loaded_asset(inst)
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_material_vector_param(
        instance_path: str,
        param_name: str,
        r: float,
        g: float,
        b: float,
        a: float = 1.0,
    ) -> dict[str, Any]:
        """Set a vector (colour/RGBA) parameter on a MaterialInstanceConstant."""
        script = f"""
import unreal, json
inst = unreal.load_asset({repr(instance_path)})
if inst is None:
    print(json.dumps({{"success": False, "error": "Material instance not found"}}))
else:
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(inst, {repr(param_name)}, unreal.LinearColor({r}, {g}, {b}, {a}))
    unreal.MaterialEditingLibrary.update_material_instance(inst)
    unreal.EditorAssetLibrary.save_loaded_asset(inst)
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def set_material_texture_param(
        instance_path: str, param_name: str, texture_path: str
    ) -> dict[str, Any]:
        """Set a texture parameter on a MaterialInstanceConstant."""
        script = f"""
import unreal, json
inst = unreal.load_asset({repr(instance_path)})
tex = unreal.load_asset({repr(texture_path)})
if inst is None or tex is None:
    print(json.dumps({{"success": False, "error": "Asset not found"}}))
else:
    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(inst, {repr(param_name)}, tex)
    unreal.MaterialEditingLibrary.update_material_instance(inst)
    unreal.EditorAssetLibrary.save_loaded_asset(inst)
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def get_material_parameters(instance_path: str) -> dict[str, Any]:
        """List all scalar, vector, and texture parameters on a MaterialInstanceConstant."""
        script = f"""
import unreal, json
inst = unreal.load_asset({repr(instance_path)})
if inst is None:
    print(json.dumps({{"success": False, "error": "Not found"}}))
else:
    scalars = [
        {{"name": str(p.parameter_info.name), "value": p.parameter_value}}
        for p in inst.get_editor_property("scalar_parameter_values")
    ]
    vectors = [
        {{"name": str(p.parameter_info.name), "value": [p.parameter_value.r, p.parameter_value.g, p.parameter_value.b, p.parameter_value.a]}}
        for p in inst.get_editor_property("vector_parameter_values")
    ]
    textures = [
        {{"name": str(p.parameter_info.name), "value": str(p.parameter_value.get_path_name()) if p.parameter_value else None}}
        for p in inst.get_editor_property("texture_parameter_values")
    ]
    print(__import__("json").dumps({{"success": True, "scalars": scalars, "vectors": vectors, "textures": textures}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def apply_material_to_actor(
        actor_name: str, material_path: str, material_slot: int = 0
    ) -> dict[str, Any]:
        """Apply a material (or material instance) to an actor by slot index."""
        return bridge.send_command(
            "apply_material_to_actor",
            {"actor_name": actor_name, "material_path": material_path, "material_slot": material_slot},
        )

    @mcp.tool()
    def get_available_materials(
        search_path: str = "/Game/", include_engine_materials: bool = True
    ) -> dict[str, Any]:
        """List available material assets in the project."""
        return bridge.send_command(
            "get_available_materials",
            {"search_path": search_path, "include_engine_materials": include_engine_materials},
        )

    @mcp.tool()
    def get_actor_material_info(actor_name: str) -> dict[str, Any]:
        """Get information about the materials currently applied to an actor."""
        return bridge.send_command("get_actor_material_info", {"actor_name": actor_name})

    @mcp.tool()
    def create_glass_material_instance(
        instance_path: str,
        parent_material_path: str,
        roughness: float = 0.0,
        metallic: float = 0.0,
        opacity: float = 0.15,
        ior: float = 1.5,
        tint_r: float = 0.9,
        tint_g: float = 0.95,
        tint_b: float = 1.0,
    ) -> dict[str, Any]:
        """
        Create a MaterialInstanceConstant configured for realistic glass/lens behaviour.
        Applies roughness, metallic, opacity, IOR, and tint vector params in one call.
        Suitable for spectacles, sunglasses, and vehicle windshields.
        """
        # First create the instance, then set all params
        result = create_material_instance.__wrapped__(instance_path, parent_material_path)
        if result.get("status") == "error" or not result.get("result", {}).get("success"):
            return result
        for setter, kwargs in [
            (set_material_scalar_param.__wrapped__, {"param_name": "Roughness", "value": roughness}),
            (set_material_scalar_param.__wrapped__, {"param_name": "Metallic", "value": metallic}),
            (set_material_scalar_param.__wrapped__, {"param_name": "Opacity", "value": opacity}),
            (set_material_scalar_param.__wrapped__, {"param_name": "IOR", "value": ior}),
            (set_material_vector_param.__wrapped__, {"param_name": "Tint", "r": tint_r, "g": tint_g, "b": tint_b, "a": 1.0}),
        ]:
            r = setter(instance_path=instance_path, **kwargs)
            if r.get("status") == "error":
                return r
        return {"status": "success", "result": {"success": True, "path": instance_path}}
