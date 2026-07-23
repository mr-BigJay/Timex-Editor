' اجرای برنامه بدون نمایش پنجرهٔ CMD
Option Explicit

Dim fso, sh, appDir, pythonw, appScript

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = appDir

pythonw = "pythonw"
On Error Resume Next
sh.Run pythonw & " -m pip install -r requirements.txt -q", 0, True
On Error GoTo 0

appScript = fso.BuildPath(appDir, "attendance_app.pyw")
If fso.FileExists(appScript) Then
    sh.Run """" & pythonw & """ """ & appScript & """", 0, False
Else
    appScript = fso.BuildPath(appDir, "attendance_app.py")
    sh.Run """" & pythonw & """ """ & appScript & """", 0, False
End If
