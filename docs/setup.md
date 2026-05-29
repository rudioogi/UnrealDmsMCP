# Setup Guide

## Prerequisites

- Unreal Engine 5.7
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Visual Studio 2022 (Windows) with C++ game development workload

## 1. Enable Unreal Editor plugins

In your `.uproject`, add the following to the `Plugins` array:

```json
{ "Name": "PythonScriptPlugin",        "Enabled": true },
{ "Name": "EditorScriptingUtilities",  "Enabled": true }
```

Enable **Python Remote Execution** in Editor Preferences → Plugins → Python → Enable Remote Execution (optional; only needed if you use the built-in UDP remote exec separately).

## 2. Add the UnrealMCP plugin to your project

Copy (or symlink) the `UnrealMCP/` folder from this repo into your project's `Plugins/` folder:

```
<YourProject>/Plugins/UnrealMCP/
```

Right-click the `.uproject` → **Generate Visual Studio project files**, then build the project. The `UnrealMCP` plugin will compile and the TCP bridge will start automatically when you open the project in the editor.

Default port: **55557**. Confirm in the Output Log: `EpicUnrealMCPBridge: Server started on 127.0.0.1:55557`.

## 3. Install the Python MCP server

```powershell
cd unreal-dms-mcp/Python
uv sync
```

## 4. Wire Claude Code

Copy `.mcp.json.example` to your project root as `.mcp.json` and update the absolute path:

```json
{
  "mcpServers": {
    "unreal-dms": {
      "command": "uv",
      "args": ["--directory", "C:/Dev/Repos/Unreal/unreal-dms-mcp/Python", "run", "unreal_dms_mcp_server.py"]
    }
  }
}
```

Then:

```
claude mcp add unreal-dms
```

## 5. Verify

With the editor open and the project loaded, ask Claude:

> "List all actors in the level"

Expected: Claude calls `get_actors_in_level` and returns the actor list.

## Troubleshooting

- **Connection refused on 55557**: The plugin didn't compile or load. Check the Output Log for `EpicUnrealMCPBridge` messages.
- **`execute_python` returns "Python not available"**: `PythonScriptPlugin` is not enabled in the project. Add it to the `.uproject` Plugins array.
- **Tool returns error in MCP Inspector**: Run `npx @modelcontextprotocol/inspector uv --directory Python run unreal_dms_mcp_server.py` and check the stdio log.
