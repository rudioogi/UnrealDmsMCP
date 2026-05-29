"""
Animation tools: LevelSequence creation, Control Rig keyframing,
and DMS behaviour presets (drowsiness, distraction).
All via execute_python using ControlRigSequencerLibrary.
"""

from __future__ import annotations
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
import bridge

logger = logging.getLogger("unreal_dms.animation")

# DMS behaviour presets — (control_name, keyframes) where each keyframe is
# (frame, value_type, value).  value_type: 'transform'|'float'|'bool'
DMS_PRESETS: dict[str, list[tuple]] = {
    "drowsy": [
        # Gradual eye closure over 60 frames, then reopen
        ("eye_L_blink", [(0, "float", 0.0), (30, "float", 0.8), (60, "float", 1.0), (90, "float", 0.8), (120, "float", 0.0)]),
        ("eye_R_blink", [(0, "float", 0.0), (30, "float", 0.8), (60, "float", 1.0), (90, "float", 0.8), (120, "float", 0.0)]),
        # Head nod — pitch forward
        ("head",        [(0, "rotator", [0, 0, 0]), (60, "rotator", [15, 0, 0]), (120, "rotator", [0, 0, 0])]),
    ],
    "distracted_look_right": [
        # Head rotates right, gaze follows
        ("head",        [(0, "rotator", [0, 0, 0]), (20, "rotator", [0, 0, -40]), (80, "rotator", [0, 0, -40]), (100, "rotator", [0, 0, 0])]),
        ("eye_L_aim",   [(0, "rotator", [0, 0, 0]), (20, "rotator", [0, 0, -15]), (80, "rotator", [0, 0, -15]), (100, "rotator", [0, 0, 0])]),
        ("eye_R_aim",   [(0, "rotator", [0, 0, 0]), (20, "rotator", [0, 0, -15]), (80, "rotator", [0, 0, -15]), (100, "rotator", [0, 0, 0])]),
    ],
    "distracted_look_left": [
        ("head",        [(0, "rotator", [0, 0, 0]), (20, "rotator", [0, 0, 40]), (80, "rotator", [0, 0, 40]), (100, "rotator", [0, 0, 0])]),
        ("eye_L_aim",   [(0, "rotator", [0, 0, 0]), (20, "rotator", [0, 0, 15]), (80, "rotator", [0, 0, 15]), (100, "rotator", [0, 0, 0])]),
        ("eye_R_aim",   [(0, "rotator", [0, 0, 0]), (20, "rotator", [0, 0, 15]), (80, "rotator", [0, 0, 15]), (100, "rotator", [0, 0, 0])]),
    ],
    "alert": [
        # Eyes wide, head upright
        ("eye_L_blink", [(0, "float", 0.0)]),
        ("eye_R_blink", [(0, "float", 0.0)]),
        ("head",        [(0, "rotator", [0, 0, 0])]),
    ],
}


def register(mcp: FastMCP):

    @mcp.tool()
    def create_level_sequence(
        sequence_path: str,
        frame_rate: int = 30,
        duration_frames: int = 120,
    ) -> dict[str, Any]:
        """
        Create a LevelSequence asset.
        sequence_path: e.g. '/Game/Sequences/DMS_Drowsy_Seq'.
        """
        script = f"""
import unreal, json
factory = unreal.LevelSequenceFactoryNew()
tools = unreal.AssetToolsHelpers.get_asset_tools()
pkg, name = {repr(sequence_path)}.rsplit("/", 1)
seq = tools.create_asset(name, pkg, unreal.LevelSequence, factory)
if seq is None:
    print(json.dumps({{"success": False, "error": "Failed to create LevelSequence"}}))
else:
    seq.set_display_rate(unreal.FrameRate({frame_rate}, 1))
    seq.set_playback_end_seconds({duration_frames} / {frame_rate})
    unreal.EditorAssetLibrary.save_asset({repr(sequence_path)})
    print(json.dumps({{"success": True, "path": {repr(sequence_path)}}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def bind_actor_to_sequence(
        sequence_path: str, actor_name: str
    ) -> dict[str, Any]:
        """Bind an actor in the current level to a LevelSequence for animation."""
        script = f"""
import unreal, json
seq = unreal.load_asset({repr(sequence_path)})
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(actor_name)}), None)
if seq is None or actor is None:
    print(json.dumps({{"success": False, "error": "Sequence or actor not found"}}))
else:
    binding = seq.add_possessable(actor)
    unreal.EditorAssetLibrary.save_asset({repr(sequence_path)})
    print(json.dumps({{"success": True, "binding_id": str(binding.get_unique_id())}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def add_control_rig_track(
        sequence_path: str,
        actor_name: str,
    ) -> dict[str, Any]:
        """Add a Control Rig track to a LevelSequence for a MetaHuman actor."""
        script = f"""
import unreal, json
seq = unreal.load_asset({repr(sequence_path)})
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(actor_name)}), None)
if seq is None or actor is None:
    print(json.dumps({{"success": False, "error": "Sequence or actor not found"}}))
else:
    world = unreal.EditorLevelLibrary.get_editor_world()
    binding = seq.add_possessable(actor)
    # Find the skeletal mesh component to attach the CR track
    skel_comp = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    comp_binding = seq.add_possessable(skel_comp) if skel_comp else None
    # Try adding CR track via ControlRigSequencerLibrary
    try:
        track = unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(
            world, seq, unreal.ControlRig.static_class(), binding
        )
        print(json.dumps({{"success": True, "binding_id": str(binding.get_unique_id())}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def keyframe_control(
        sequence_path: str,
        actor_name: str,
        control_name: str,
        frame: int,
        value_type: str,
        value: Any,
    ) -> dict[str, Any]:
        """
        Set a keyframe on a Control Rig control for a given actor in a LevelSequence.
        value_type: 'float' | 'bool' | 'rotator' | 'transform'.
        value:
          float  -> number
          bool   -> true/false
          rotator -> [pitch, yaw, roll]
          transform -> {"location": [x,y,z], "rotation": [p,y,r], "scale": [x,y,z]}
        """
        script = f"""
import unreal, json
seq = unreal.load_asset({repr(sequence_path)})
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(actor_name)}), None)
if seq is None or actor is None:
    print(json.dumps({{"success": False, "error": "Not found"}}))
else:
    world = unreal.EditorLevelLibrary.get_editor_world()
    binding = seq.add_possessable(actor)
    rigs = unreal.ControlRigSequencerLibrary.get_control_rigs(seq)
    if not rigs:
        print(json.dumps({{"success": False, "error": "No control rigs on sequence binding"}}))
    else:
        rig = rigs[0].control_rig
        fn = unreal.FrameNumber({frame})
        vtype = {repr(value_type)}
        val = {repr(value)}
        ok = False
        if vtype == "float":
            unreal.ControlRigSequencerLibrary.set_local_control_rig_float(rig, {repr(control_name)}, fn, float(val), set_key=True)
            ok = True
        elif vtype == "bool":
            unreal.ControlRigSequencerLibrary.set_local_control_rig_bool(rig, {repr(control_name)}, fn, bool(val), set_key=True)
            ok = True
        elif vtype == "rotator":
            r = unreal.Rotator(*val)
            unreal.ControlRigSequencerLibrary.set_local_control_rig_rotator(rig, {repr(control_name)}, fn, r, set_key=True)
            ok = True
        elif vtype == "transform":
            t = unreal.Transform(
                unreal.Vector(*val.get("location", [0,0,0])),
                unreal.Rotator(*val.get("rotation", [0,0,0])),
                unreal.Vector(*val.get("scale", [1,1,1])),
            )
            unreal.ControlRigSequencerLibrary.set_local_control_rig_transform(rig, {repr(control_name)}, fn, t, set_key=True)
            ok = True
        print(json.dumps({{"success": ok}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def apply_behavior_preset(
        sequence_path: str,
        actor_name: str,
        preset: str,
        start_frame: int = 0,
    ) -> dict[str, Any]:
        """
        Apply a named DMS behaviour preset to a MetaHuman actor in a LevelSequence.
        preset: 'drowsy' | 'distracted_look_right' | 'distracted_look_left' | 'alert'.
        All keyframes are offset by start_frame.
        """
        presets = DMS_PRESETS
        if preset not in presets:
            return {"status": "error", "error": f"Unknown preset '{preset}'. Available: {list(presets.keys())}"}

        results = []
        for control_name, keyframes in presets[preset]:
            for frame_offset, value_type, value in keyframes:
                r = keyframe_control.__wrapped__(
                    sequence_path=sequence_path,
                    actor_name=actor_name,
                    control_name=control_name,
                    frame=start_frame + frame_offset,
                    value_type=value_type,
                    value=value,
                )
                results.append(r)

        errors = [r for r in results if r.get("status") == "error"]
        return {
            "status": "success" if not errors else "partial",
            "result": {
                "preset": preset,
                "keyframes_set": len(results) - len(errors),
                "errors": errors,
            },
        }

    @mcp.tool()
    def bake_to_anim_sequence(
        sequence_path: str,
        actor_name: str,
        output_anim_path: str,
        frame_rate: int = 30,
    ) -> dict[str, Any]:
        """
        Bake a LevelSequence Control Rig animation to a standalone AnimSequence asset.
        """
        script = f"""
import unreal, json
seq = unreal.load_asset({repr(sequence_path)})
actors = unreal.EditorActorSubsystem().get_all_level_actors()
actor = next((a for a in actors if a.get_name() == {repr(actor_name)}), None)
if seq is None or actor is None:
    print(json.dumps({{"success": False, "error": "Not found"}}))
else:
    skel_comp = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    if skel_comp is None:
        print(json.dumps({{"success": False, "error": "No SkeletalMeshComponent"}}))
    else:
        try:
            anim_seq = unreal.ControlRigSequencerLibrary.bake_to_control_rig(
                unreal.EditorLevelLibrary.get_editor_world(),
                seq,
                unreal.ControlRig.static_class(),
                unreal.FrameRate({frame_rate}, 1),
                seq.get_playback_start(),
                seq.get_playback_end(),
                False
            )
            print(json.dumps({{"success": True, "anim_path": str(anim_seq.get_path_name()) if anim_seq else None}}))
        except Exception as e:
            print(json.dumps({{"success": False, "error": str(e)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def list_dms_presets() -> dict[str, Any]:
        """List available DMS behaviour preset names and their control tracks."""
        return {
            "status": "success",
            "result": {
                name: [ctrl for ctrl, _ in tracks]
                for name, tracks in DMS_PRESETS.items()
            },
        }
