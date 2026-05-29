#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * Handles the "execute_python" MCP command.
 *
 * Runs a Python script inside the live Unreal Editor using IPythonScriptPlugin,
 * captures stdout/log output, and returns a structured JSON response.
 *
 * The script should end with:
 *   import json; print(json.dumps(result))
 * so the bridge can parse the structured return value from the last JSON line.
 */
class UNREALMCP_API FEpicUnrealMCPPythonCommands
{
public:
    FEpicUnrealMCPPythonCommands() = default;
    ~FEpicUnrealMCPPythonCommands() = default;

    /**
     * Execute a Python script in the editor and return:
     *   { "success": true, "output": "<captured stdout>", "result": <last JSON line parsed> }
     * or on error:
     *   { "success": false, "error": "<error message>", "output": "<any captured output>" }
     */
    TSharedPtr<FJsonObject> HandleExecutePython(const TSharedPtr<FJsonObject>& Params);
};
