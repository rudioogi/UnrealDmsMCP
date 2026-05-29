# Install unreal-dms-mcp

You are guiding a developer through the full installation, build, and smoke-test of the **unreal-dms-mcp** MCP server — a bridge that lets Claude control Unreal Engine 5.7 via a TCP plugin. Work through each phase in order. Use your tools to check state, run commands, and edit files; don't just print instructions and wait. After completing each phase, confirm it succeeded before moving on.

---

## Phase 0 — Orient

1. Read `docs/setup.md` and `docs/smoke.md` from the repo root so you have the full reference.
2. Find the absolute path to this repo on the user's machine (use the current working directory).
3. Announce the plan: five phases, what each does, roughly how long it takes (≈15–20 min total).

---

## Phase 1 — Prerequisite check

Run the following checks and report pass/fail for each. If anything fails, explain exactly how to fix it before continuing.

```
# Python ≥ 3.11
python --version   (or py --version on Windows)

# uv installed
uv --version

# Visual Studio Build Tools / MSBuild accessible (Windows only)
where msbuild   (or Get-Command msbuild on PowerShell)
```

Also ask the user:
- What is the **absolute path** to the Unreal Engine project they want to use? (e.g. `C:/Dev/MyProject/MyProject.uproject`)
- What is the **absolute path** to this cloned repo? (confirm from CWD or ask to correct)

Store both paths — you will need them in later phases.

---

## Phase 2 — Unreal plugin installation

Goal: compile and load the `UnrealMCP` C++ plugin into the user's UE project.

### 2a. Edit the `.uproject` file

Read the user's `.uproject` JSON. Find the `"Plugins"` array and ensure the following two entries are present (add them if missing, do not duplicate):

```json
{ "Name": "PythonScriptPlugin",       "Enabled": true },
{ "Name": "EditorScriptingUtilities", "Enabled": true }
```

Write the file back with the changes.

### 2b. Copy the plugin

Copy (or instruct the user to copy/symlink) the `UnrealMCP/` folder from this repo into `<UserProject>/Plugins/UnrealMCP/`. If you can access the filesystem, do the copy now:

```powershell
Copy-Item -Recurse -Force "<repo>/UnrealMCP" "<uproject_dir>/Plugins/UnrealMCP"
```

### 2c. Generate project files & build

Tell the user to:
1. Right-click the `.uproject` file in Explorer → **Generate Visual Studio project files**.
2. Open the generated `.sln` in Visual Studio 2022.
3. Set configuration to **Development Editor** / **Win64** and build.

Or, if `UnrealBuildTool` is on the PATH, offer to run it:

```powershell
& "<UE_ROOT>/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" `
    <ProjectName>Editor Win64 Development `
    -Project="<uproject_path>"
```

### 2d. Verify plugin started

Ask the user to open the project in the Unreal Editor and watch the Output Log. They should see:

```
EpicUnrealMCPBridge: Server started on 127.0.0.1:55557
```

Confirm this before proceeding. If they see a connection error, refer them to the troubleshooting section in `docs/setup.md`.

---

## Phase 3 — Python MCP server setup

### 3a. Install dependencies

Run from the repo root:

```powershell
cd Python
uv sync
```

Capture and show the output. If `uv` is not found, remind the user to install it: `pip install uv` or via `winget install astral-sh.uv`.

### 3b. Run the offline test suite

```powershell
cd Python
uv run pytest ../tests -v --ignore=../tests/test_bridge.py
```

All tests should pass. The `test_server_schema.py` tests validate tool registration without needing a live editor. Fix any failures before continuing — missing dependencies are the most common cause.

If the user wants to also run integration tests against a live editor (optional at this stage), they can set `UNREAL_MCP_LIVE=1`:

```powershell
$env:UNREAL_MCP_LIVE=1; uv run pytest ../tests -v -m integration
```

---

## Phase 4 — Wire Claude Code

### 4a. Create `.mcp.json`

In the **project directory where the user runs Claude Code** (often the UE project root or a workspace root — ask if unclear), create or update `.mcp.json`:

```json
{
  "mcpServers": {
    "unreal-dms": {
      "command": "uv",
      "args": [
        "--directory",
        "<ABSOLUTE_PATH_TO_REPO>/Python",
        "run",
        "unreal_dms_mcp_server.py"
      ],
      "env": {
        "UNREAL_MCP_HOST": "127.0.0.1",
        "UNREAL_MCP_PORT": "55557"
      }
    }
  }
}
```

Substitute the real absolute path. Write the file.

### 4b. Register with Claude Code

```
claude mcp add unreal-dms
```

If Claude Code is already open in the target directory, tell the user to **restart it** or reload the MCP config so the new server is picked up.

### 4c. Confirm tools are visible

Ask the user to type `/mcp` or run:

```
claude mcp list
```

They should see `unreal-dms` listed as connected. If it shows as disconnected, check that the `.mcp.json` path is correct and that `uv` is on the PATH Claude Code uses.

---

## Phase 5 — Smoke test (live editor required)

Walk the user through the checklist from `docs/smoke.md`. For each check, give them the exact Claude Code prompt to type. Work through the phases in order:

### Foundation checks (Phase 0 of smoke.md)

Instruct the user to type these prompts to Claude Code one at a time and confirm each succeeds:

1. "List all actors in the current level" — should call `get_actors_in_level`
2. "Spawn a StaticMeshActor named TestCube" — actor should appear in the Unreal viewport
3. "Move TestCube to location 500, 0, 100" — actor should move
4. "Delete the actor named TestCube" — actor should disappear
5. "Run this Python in Unreal and return the result: `import unreal, json; print(json.dumps({'version': str(unreal.SystemLibrary.get_engine_version())}))`" — should return engine version string
6. "Create a Blueprint named TestBP with parent class Actor" — asset should appear in Content Browser
7. "Compile the Blueprint named TestBP" — no compile errors
8. "Add a Print String node to the EventGraph of /Game/TestBP" — node should appear in graph

For checks in Phases 1–5 of smoke.md, tell the user those require project-specific asset paths (vehicle BPs, MetaHuman BPs, etc.) and point them to `docs/smoke.md` for the full parameterized checklist.

---

## Completion

When all phases pass, print a summary:

```
✓ Phase 1  Prerequisites satisfied
✓ Phase 2  UnrealMCP plugin compiled and running on :55557
✓ Phase 3  Python deps installed, offline tests passing
✓ Phase 4  MCP server wired into Claude Code
✓ Phase 5  Foundation smoke checks passed

unreal-dms-mcp is ready.
Full smoke checklist: docs/smoke.md
Troubleshooting:      docs/setup.md
```

---

## Troubleshooting quick reference

| Symptom | Fix |
|---|---|
| Connection refused on 55557 | Plugin didn't compile or isn't loaded — check UE Output Log for `EpicUnrealMCPBridge` |
| `execute_python` returns "Python not available" | `PythonScriptPlugin` not in `.uproject` — re-run Phase 2a |
| `uv: command not found` | `pip install uv` or `winget install astral-sh.uv` |
| MCP server shows disconnected in Claude Code | Wrong absolute path in `.mcp.json`, or `uv` not on PATH for Claude Code's shell |
| Offline tests fail with import errors | Run `uv sync` again — lock file may be out of date |
| MCP Inspector debug | `npx @modelcontextprotocol/inspector uv --directory Python run unreal_dms_mcp_server.py` |
