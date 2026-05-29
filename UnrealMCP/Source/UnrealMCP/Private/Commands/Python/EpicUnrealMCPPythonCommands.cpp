#include "Commands/Python/EpicUnrealMCPPythonCommands.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"

// IPythonScriptPlugin is only available when the Python editor plugin is enabled.
// Guard the include so the plugin still compiles when Python is absent (the tool
// will return an informative error instead of a build failure).
#if WITH_PYTHON
#include "IPythonScriptPlugin.h"
#endif

TSharedPtr<FJsonObject> FEpicUnrealMCPPythonCommands::HandleExecutePython(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> Result = MakeShareable(new FJsonObject);

#if !WITH_PYTHON
    Result->SetBoolField(TEXT("success"), false);
    Result->SetStringField(TEXT("error"), TEXT("PythonScriptPlugin is not enabled in this project. "
        "Enable it in Edit > Plugins and add PythonScriptPlugin to your .uproject."));
    return Result;
#else
    // Extract the script string from params
    FString Script;
    if (!Params->TryGetStringField(TEXT("script"), Script) || Script.IsEmpty())
    {
        Result->SetBoolField(TEXT("success"), false);
        Result->SetStringField(TEXT("error"), TEXT("Missing or empty 'script' parameter"));
        return Result;
    }

    IPythonScriptPlugin* PythonPlugin = IPythonScriptPlugin::Get();
    if (!PythonPlugin || !PythonPlugin->IsPythonAvailable())
    {
        Result->SetBoolField(TEXT("success"), false);
        Result->SetStringField(TEXT("error"), TEXT("Python is not available in the editor. "
            "Check that PythonScriptPlugin is enabled and the Editor has fully started."));
        return Result;
    }

    // Build the command descriptor
    FPythonCommandEx PythonCmd;
    PythonCmd.Command = Script;
    PythonCmd.ExecutionMode = EPythonCommandExecutionMode::ExecuteFile;
    PythonCmd.FileExecutionScope = EPythonFileExecutionScope::Public;

    const bool bOk = PythonPlugin->ExecPythonCommandEx(PythonCmd);

    // Collect all log output lines into a single string
    FString CapturedOutput;
    for (const FPythonLogOutputEntry& LogEntry : PythonCmd.LogOutput)
    {
        CapturedOutput += LogEntry.Output;
        CapturedOutput += TEXT("\n");
    }
    CapturedOutput.TrimEndInline();

    Result->SetBoolField(TEXT("success"), bOk);
    Result->SetStringField(TEXT("output"), CapturedOutput);

    if (!bOk)
    {
        // Surface the last error/log line as the human-readable error message
        FString ErrorMsg = PythonCmd.CommandResult.IsEmpty()
            ? TEXT("Python script execution failed")
            : PythonCmd.CommandResult;
        Result->SetStringField(TEXT("error"), ErrorMsg);
        return Result;
    }

    // Try to parse the last non-empty line of output as JSON so the Python bridge
    // can receive structured data without an extra parsing step.
    TArray<FString> Lines;
    CapturedOutput.ParseIntoArrayLines(Lines, true);
    FString LastLine;
    for (int32 i = Lines.Num() - 1; i >= 0; --i)
    {
        FString Trimmed = Lines[i].TrimStartAndEnd();
        if (!Trimmed.IsEmpty())
        {
            LastLine = Trimmed;
            break;
        }
    }

    if (!LastLine.IsEmpty())
    {
        TSharedPtr<FJsonObject> ParsedJson;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(LastLine);
        if (FJsonSerializer::Deserialize(Reader, ParsedJson) && ParsedJson.IsValid())
        {
            Result->SetObjectField(TEXT("result"), ParsedJson);
        }
        else
        {
            // Not JSON — store raw last line for the bridge to inspect
            Result->SetStringField(TEXT("last_line"), LastLine);
        }
    }

    return Result;
#endif
}
