# Smoke Checklist

Run this after every engine/plugin recompile or Python dependency update.
Open the editor with a test project, then verify each item in Claude Code.

## Foundation (Phase 0)

- [ ] `get_actors_in_level` — returns a list (may be empty)
- [ ] `spawn_actor name="TestCube" actor_type="StaticMeshActor"` — actor appears in viewport
- [ ] `set_actor_transform name="TestCube" location=[500,0,100]` — actor moves
- [ ] `delete_actor name="TestCube"` — actor disappears
- [ ] `execute_python script="import unreal, json; print(json.dumps({'version': str(unreal.SystemLibrary.get_engine_version())}))"` — returns engine version string
- [ ] `create_blueprint name="TestBP" parent_class="Actor"` — Blueprint asset created
- [ ] `compile_blueprint blueprint_name="TestBP"` — compiles with no errors
- [ ] `add_blueprint_node blueprint_path="/Game/TestBP" graph_name="EventGraph" node_type="Print"` — node appears in graph

## Phase 1 (Mesh & Material)

- [ ] `create_material_instance parent_material_path="/Engine/BasicShapes/BasicShapeMaterial" instance_path="/Game/_mcp_test/MI_Test"` — MI asset created
- [ ] `set_material_scalar_param instance_path="/Game/_mcp_test/MI_Test" param_name="Roughness" value=0.1` — param updated
- [ ] `create_glass_material_instance instance_path="/Game/_mcp_test/MI_Glass" parent_material_path="<your glass master>"` — creates MI with glass params

## Phase 2 (Spline & Vehicle)

- [ ] `create_spline_actor name="TestSpline"` — spline actor in level
- [ ] `add_spline_points spline_actor_name="TestSpline" points=[[0,0,0],[500,0,0],[1000,500,0]]` — 3 spline points
- [ ] `spawn_chaos_vehicle name="TestCar" blueprint_path="<your vehicle BP>"` — vehicle in level
- [ ] `attach_vehicle_to_spline vehicle_actor_name="TestCar" spline_actor_name="TestSpline" speed_kmh=60` — BP_SplineFollower attached

## Phase 3 (MetaHuman)

- [ ] `spawn_metahuman name="Driver" blueprint_path="<your MH BP>"` — MetaHuman in level
- [ ] `attach_accessory metahuman_actor_name="Driver" accessory_blueprint_path="<glasses BP>" accessory_name="Glasses"` — glasses attached to face
- [ ] `set_material_scalar_param instance_path="<glasses MI>" param_name="Roughness" value=0.0` — glass roughness set
- [ ] `seat_metahuman_in_vehicle metahuman_actor_name="Driver" vehicle_actor_name="TestCar"` — MetaHuman attached to vehicle

## Phase 4 (Animation)

- [ ] `create_level_sequence sequence_path="/Game/_mcp_test/Seq_Drowsy" frame_rate=30 duration_frames=120` — sequence created
- [ ] `apply_behavior_preset sequence_path="/Game/_mcp_test/Seq_Drowsy" actor_name="Driver" preset="drowsy"` — keyframes set
- [ ] `list_dms_presets` — returns all 4 presets

## Phase 5 (Capture)

- [ ] `take_screenshot output_path="C:/DMS_Capture/test.png"` — PNG file on disk
- [ ] `export_face_landmarks metahuman_actor_name="Driver" camera_actor_name="<cam>" output_json_path="C:/DMS_Capture/landmarks.json" label="alert" frame_id=0` — JSON file created with 32 bone entries
- [ ] `run_capture_batch scenario={"metahuman_actor":"Driver","camera_actor":"<cam>","label":"drowsy","frames":5,"output_dir":"C:/DMS_Capture/batch01"}` — 5 PNGs + landmarks.json + labels.json
