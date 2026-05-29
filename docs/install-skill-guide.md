# Using the `/install-unreal-dms` Skill

The repo ships with a Claude Code skill that walks you through the full installation interactively — checking prerequisites, building the C++ plugin, wiring the Python MCP server, and running smoke tests. Claude does as much of the work as possible instead of just printing instructions.

## Prerequisites (before you start)

| Tool | Version | Install |
|---|---|---|
| Unreal Engine | 5.7 | Epic Games Launcher |
| Python | 3.11 – 3.13 | python.org |
| uv | any | `pip install uv` or `winget install astral-sh.uv` |
| Visual Studio 2022 | any | with **C++ game development** workload |
| Claude Code | latest | `npm install -g @anthropic-ai/claude-code` |

## Step 1 — Clone the repo

```powershell
git clone <repo-url>
cd unreal-dms-mcp
```

## Step 2 — Open Claude Code in the repo

```powershell
claude
```

Claude Code must be started from inside the `unreal-dms-mcp` directory so it picks up the `.claude/commands/` skill files.

## Step 3 — Run the skill

Type this prompt in the Claude Code session:

```
/install-unreal-dms
```

Claude will guide you through five phases:

| Phase | What happens |
|---|---|
| **1 – Prerequisites** | Checks Python, uv, and MSBuild; asks for your UE project path |
| **2 – Plugin build** | Edits your `.uproject`, copies `UnrealMCP/` into your project's `Plugins/` folder, guides the VS2022 build |
| **3 – Python server** | Runs `uv sync`, then runs the offline test suite (no live editor required) |
| **4 – Wire Claude Code** | Writes `.mcp.json` with the correct paths and registers the MCP server |
| **5 – Smoke test** | Steps through foundation checks against a live editor: spawn actors, run Python, create blueprints |

Claude blocks on each phase and won't advance until it succeeds, so you can't accidentally skip a broken step.

## What you'll need to provide

Claude will ask you for two paths during Phase 1:

- **Your UE project path** — e.g. `C:/Dev/MyProject/MyProject.uproject`
- **Confirmation of the repo path** — Claude reads this from the working directory, just confirm or correct it

For the MetaHuman, vehicle, and capture smoke checks (Phases 2–5 of the smoke checklist) you'll also need project-specific asset paths. Those are optional — the foundation checks cover the core installation.

## After installation

Once the skill completes, you should see:

```
✓ Phase 1  Prerequisites satisfied
✓ Phase 2  UnrealMCP plugin compiled and running on :55557
✓ Phase 3  Python deps installed, offline tests passing
✓ Phase 4  MCP server wired into Claude Code
✓ Phase 5  Foundation smoke checks passed
```

From that point, open Claude Code in any directory containing a `.mcp.json` that points to this server and start talking to Unreal:

> "List all actors in the level"
> "Spawn a MetaHuman named Driver at the origin"
> "Create a level sequence with 120 frames at 30fps"

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/install-unreal-dms` not found | Make sure Claude Code is started from inside the `unreal-dms-mcp` directory |
| Connection refused on 55557 | Plugin didn't compile — check UE Output Log for `EpicUnrealMCPBridge` |
| `execute_python` returns "Python not available" | `PythonScriptPlugin` missing from `.uproject` — re-run Phase 2 |
| MCP server shows disconnected | Wrong absolute path in `.mcp.json`, or `uv` not on the PATH Claude Code uses |
| Offline tests fail | Run `uv sync` again inside the `Python/` directory |

Full setup reference: [`docs/setup.md`](setup.md)
Full smoke checklist: [`docs/smoke.md`](smoke.md)
