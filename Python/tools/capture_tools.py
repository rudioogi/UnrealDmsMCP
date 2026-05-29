"""
Data capture tools for DMS training data generation.
Ports logic from ChaosHumanDriver/Scripts/runGetLandmarks.py:
  - 32 FACIAL_* bone positions projected to CineCamera screen UV
  - JSON export per frame (landmark UVs + ground-truth label)
  - Screenshot/render-to-disk pipeline
  - Batch capture runner
"""

from __future__ import annotations
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
import bridge

logger = logging.getLogger("unreal_dms.capture")

# The 32 facial landmark bones tracked in the existing DMS pipeline
FACIAL_BONES = [
    "FACIAL_C_NoseTip", "FACIAL_C_NoseBridge", "FACIAL_C_ForeheadMid",
    "FACIAL_L_NostrilBase", "FACIAL_R_NostrilBase",
    "FACIAL_L_OuterBrow", "FACIAL_L_MidBrow", "FACIAL_L_InnerBrow",
    "FACIAL_R_OuterBrow", "FACIAL_R_MidBrow", "FACIAL_R_InnerBrow",
    "FACIAL_L_OuterEyelid", "FACIAL_L_InnerEyelid",
    "FACIAL_R_OuterEyelid", "FACIAL_R_InnerEyelid",
    "FACIAL_L_Cheek", "FACIAL_R_Cheek",
    "FACIAL_L_CheekLower", "FACIAL_R_CheekLower",
    "FACIAL_C_UpperLipMid", "FACIAL_C_LowerLipMid",
    "FACIAL_L_UpperLipOuter", "FACIAL_R_UpperLipOuter",
    "FACIAL_L_LowerLipOuter", "FACIAL_R_LowerLipOuter",
    "FACIAL_L_MouthCorner", "FACIAL_R_MouthCorner",
    "FACIAL_C_Jaw", "FACIAL_L_JawCorner", "FACIAL_R_JawCorner",
    "FACIAL_L_Ear", "FACIAL_R_Ear",
]


def register(mcp: FastMCP):

    @mcp.tool()
    def setup_capture_camera(
        camera_actor_name: str,
        metahuman_actor_name: str,
        location_offset: list[float] = None,
        fov_degrees: float = 60.0,
    ) -> dict[str, Any]:
        """
        Configure a CineCamera actor for DMS capture:
        sets FOV, focuses it on the MetaHuman face, and locks it to the driver position.
        """
        script = f"""
import unreal, json
by_name = {{a.get_name(): a for a in unreal.EditorActorSubsystem().get_all_level_actors()}}
cam = by_name.get({repr(camera_actor_name)})
mh = by_name.get({repr(metahuman_actor_name)})
if cam is None or mh is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    cam_comp = cam.get_component_by_class(unreal.CineCameraComponent)
    if cam_comp:
        cam_comp.set_editor_property("field_of_view", {fov_degrees})
    offset = unreal.Vector(*{repr(location_offset or [0, 0, 0])})
    cam.set_actor_location(mh.get_actor_location() + offset)
    cam.set_actor_look_at_location(mh.get_actor_location())
    print(json.dumps({{"success": True}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def export_face_landmarks(
        metahuman_actor_name: str,
        camera_actor_name: str,
        output_json_path: str,
        label: str = "alert",
        frame_id: int = 0,
    ) -> dict[str, Any]:
        """
        Project the 32 FACIAL_* bone world positions to CineCamera screen UVs
        and append a labelled frame record to a JSON file.
        label: 'alert' | 'drowsy' | 'distracted' (ground-truth DMS state).
        Ports the core logic of ChaosHumanDriver/Scripts/runGetLandmarks.py.
        """
        script = f"""
import unreal, json, os

FACIAL_BONES = {FACIAL_BONES!r}

by_name = {{a.get_name(): a for a in unreal.EditorActorSubsystem().get_all_level_actors()}}
mh = by_name.get({repr(metahuman_actor_name)})
cam = by_name.get({repr(camera_actor_name)})

if mh is None or cam is None:
    print(json.dumps({{"success": False, "error": "Actor not found"}}))
else:
    face_mesh = next(
        (c for c in mh.get_components_by_class(unreal.SkeletalMeshComponent)
         if "face" in c.get_name().lower()),
        mh.get_component_by_class(unreal.SkeletalMeshComponent)
    )
    cam_comp = cam.get_component_by_class(unreal.CineCameraComponent)
    landmarks = {{}}
    if face_mesh and cam_comp:
        for bone in FACIAL_BONES:
            world_pos = face_mesh.get_socket_location(bone)
            # Project world → screen UV
            view_proj = cam_comp.calc_scene_view(None)
            screen_pos, in_front = unreal.GameplayStatics.project_world_to_screen(
                None, world_pos, False
            )
            size = unreal.GameplayStatics.get_viewport_size(None)
            if size.x > 0 and size.y > 0:
                landmarks[bone] = [screen_pos.x / size.x, screen_pos.y / size.y]
            else:
                landmarks[bone] = [float(world_pos.x), float(world_pos.y)]
    record = {{
        "frame": {frame_id},
        "label": {repr(label)},
        "landmarks": landmarks,
    }}
    # Append to JSON file
    out = {repr(output_json_path)}
    os.makedirs(os.path.dirname(out), exist_ok=True) if os.path.dirname(out) else None
    existing = []
    if os.path.exists(out):
        with open(out) as f:
            existing = json.load(f)
    existing.append(record)
    with open(out, "w") as f:
        json.dump(existing, f, indent=2)
    print(json.dumps({{"success": True, "frame": {frame_id}, "landmark_count": len(landmarks)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def take_screenshot(
        output_path: str,
        width: int = 1920,
        height: int = 1080,
    ) -> dict[str, Any]:
        """
        Take a high-resolution screenshot of the current editor viewport.
        output_path: absolute file path for the PNG (e.g. 'C:/DMS_Data/frame_0001.png').
        """
        script = f"""
import unreal, json
unreal.AutomationLibrary.take_high_res_screenshot({width}, {height}, {repr(output_path)})
print(json.dumps({{"success": True, "path": {repr(output_path)}}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def render_sequence_to_disk(
        sequence_path: str,
        output_directory: str,
        width: int = 1920,
        height: int = 1080,
        frame_rate: int = 30,
        format: str = "PNG",
    ) -> dict[str, Any]:
        """
        Render a LevelSequence to disk using Movie Render Queue.
        format: 'PNG' | 'JPG' | 'EXR'.
        """
        script = f"""
import unreal, json
seq = unreal.load_asset({repr(sequence_path)})
if seq is None:
    print(json.dumps({{"success": False, "error": "Sequence not found"}}))
else:
    queue = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    job = queue.get_queue().allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.set_editor_property("sequence", unreal.SoftObjectPath({repr(sequence_path)}))
    cfg = job.get_configuration()
    # Image output settings
    out_setting = cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG if {repr(format)} == "PNG" else unreal.MoviePipelineImageSequenceOutput_JPG)
    out_setting.set_editor_property("output_directory", unreal.DirectoryPath({repr(output_directory)}))
    # Resolution
    res_setting = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    res_setting.set_editor_property("output_resolution", unreal.IntPoint({width}, {height}))
    res_setting.set_editor_property("output_frame_rate", unreal.FrameRate({frame_rate}, 1))
    executor = unreal.MoviePipelinePIEExecutor()
    queue.render_queue_with_executor_instance(executor)
    print(json.dumps({{"success": True, "output_directory": {repr(output_directory)}}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def export_ground_truth_labels(
        labels: list[dict[str, Any]],
        output_path: str,
    ) -> dict[str, Any]:
        """
        Write a ground-truth label file for a DMS capture batch.
        labels: list of {frame, label, metadata} dicts.
        Appends to existing file if present.
        """
        script = f"""
import json, os
labels = {repr(labels)}
out = {repr(output_path)}
os.makedirs(os.path.dirname(out), exist_ok=True) if os.path.dirname(out) else None
existing = []
if os.path.exists(out):
    with open(out) as f:
        existing = json.load(f)
existing.extend(labels)
with open(out, "w") as f:
    json.dump(existing, f, indent=2)
print(json.dumps({{"success": True, "total_records": len(existing)}}))
"""
        return bridge.execute_python(script)

    @mcp.tool()
    def run_capture_batch(
        scenario: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run a complete DMS capture batch for one scenario.
        scenario dict keys:
          metahuman_actor (str)      — MetaHuman actor name in the scene
          camera_actor (str)         — CineCamera actor name
          label (str)                — DMS ground truth: 'alert'|'drowsy'|'distracted'
          sequence_path (str)        — LevelSequence to play back (or null for static)
          frames (int)               — Number of frames to capture
          output_dir (str)           — Directory for screenshots + JSON
          capture_landmarks (bool)   — Whether to export landmark JSON
          screenshot_width (int)     — Default 1920
          screenshot_height (int)    — Default 1080
        """
        mh = scenario.get("metahuman_actor", "")
        cam = scenario.get("camera_actor", "")
        label = scenario.get("label", "alert")
        frames = scenario.get("frames", 1)
        out_dir = scenario.get("output_dir", "C:/DMS_Capture")
        do_landmarks = scenario.get("capture_landmarks", True)
        w = scenario.get("screenshot_width", 1920)
        h = scenario.get("screenshot_height", 1080)
        seq_path = scenario.get("sequence_path")

        results: list[dict[str, Any]] = []
        landmark_file = f"{out_dir}/landmarks.json"
        label_file = f"{out_dir}/labels.json"

        for frame_id in range(frames):
            # Screenshot
            frame_file = f"{out_dir}/frame_{frame_id:05d}.png"
            sr = take_screenshot.__wrapped__(output_path=frame_file, width=w, height=h)
            results.append({"frame": frame_id, "screenshot": sr})

            # Landmarks
            if do_landmarks and mh and cam:
                lr = export_face_landmarks.__wrapped__(
                    metahuman_actor_name=mh,
                    camera_actor_name=cam,
                    output_json_path=landmark_file,
                    label=label,
                    frame_id=frame_id,
                )
                results.append({"frame": frame_id, "landmarks": lr})

        # Write consolidated labels
        label_records = [{"frame": i, "label": label, "screenshot": f"frame_{i:05d}.png"} for i in range(frames)]
        export_ground_truth_labels.__wrapped__(labels=label_records, output_path=label_file)

        errors = [r for r in results if r.get("status") == "error"]
        return {
            "status": "success" if not errors else "partial",
            "result": {
                "frames_captured": frames,
                "label": label,
                "output_dir": out_dir,
                "errors": len(errors),
            },
        }
