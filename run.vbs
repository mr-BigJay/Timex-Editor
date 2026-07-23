' اجرای برنامه بدون پنجرهٔ CMD — با یافتن خودکار Python
Option Explicit

Dim fso, sh, appDir, appScript, launcher, i, logPath, errMsg

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = appDir
logPath = fso.BuildPath(appDir, "launch_error.log")

appScript = fso.BuildPath(appDir, "attendance_app.pyw")
If Not fso.FileExists(appScript) Then
    appScript = fso.BuildPath(appDir, "attendance_app.py")
End If

If Not fso.FileExists(appScript) Then
    MsgBox "فایل attendance_app.pyw یافت نشد." & vbCrLf & appDir, vbCritical, "Timex Editor"
    WScript.Quit 1
End If

' نصب وابستگی‌ها (بدون انتظار طولانی)
On Error Resume Next
launcher = FindLauncher()
If launcher <> "" Then
    sh.Run "cmd /c " & launcher & " -m pip install -r requirements.txt -q", 0, False
End If
On Error GoTo 0

' امتحان لانچرها به ترتیب
Dim launchers(5)
launchers(0) = "pyw"
launchers(1) = "py -3w"
launchers(2) = "pythonw"
launchers(3) = "py -3"
launchers(4) = "python"
launchers(5) = FindPythonwPath()

For i = 0 To 5
    launcher = launchers(i)
    If launcher <> "" Then
        If LaunchWith(launcher, appScript) Then
            WScript.Quit 0
        End If
    End If
Next

' خطا — ثبت لاگ و نمایش پیام
errMsg = "Python یافت نشد یا برنامه اجرا نشد." & vbCrLf & vbCrLf & _
    "راه‌حل:" & vbCrLf & _
    "1) Python را از python.org نصب کنید" & vbCrLf & _
    "2) هنگام نصب گزینه Add to PATH را بزنید" & vbCrLf & _
    "3) فایل START.bat را امتحان کنید" & vbCrLf & vbCrLf & _
    "مسیر: " & appDir

WriteLog logPath, errMsg
MsgBox errMsg, vbCritical, "Timex Editor — خطا در اجرا"
WScript.Quit 1


Function FindLauncher()
    Dim candidates, c
    candidates = Array("pyw", "py -3w", "pythonw", "py -3", "python")
    For Each c In candidates
        If TestCmd(c) Then
            FindLauncher = c
            Exit Function
        End If
    Next
    FindLauncher = ""
End Function


Function TestCmd(cmd)
    On Error Resume Next
    TestCmd = (sh.Run("cmd /c " & cmd & " --version >nul 2>&1", 0, True) = 0)
    On Error GoTo 0
End Function


Function LaunchWith(launcher, script)
    Dim cmd, rc
    On Error Resume Next
    cmd = "cmd /c " & launcher & " """ & script & """"
    rc = sh.Run(cmd, 0, False)
    If Err.Number <> 0 Then
        LaunchWith = False
        Exit Function
    End If
    ' اگر لانچر شناخته‌شده است، فرض بر موفقیت
    LaunchWith = True
    On Error GoTo 0
End Function


Function FindPythonwPath()
    Dim ver, base, p, versions, v
    base = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\")
    If Not fso.FolderExists(base) Then
        FindPythonwPath = ""
        Exit Function
    End If
    versions = Array("Python313", "Python312", "Python311", "Python310", "Python39")
    For Each v In versions
        p = fso.BuildPath(base, v & "\pythonw.exe")
        If fso.FileExists(p) Then
            FindPythonwPath = """" & p & """"
            Exit Function
        End If
    Next
    FindPythonwPath = ""
End Function


Sub WriteLog(path, msg)
    On Error Resume Next
    Dim stream
    Set stream = fso.OpenTextFile(path, 2, True)
    stream.WriteLine Now & " — " & msg
    stream.Close
End Sub
