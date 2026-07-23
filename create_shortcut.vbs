Set oWS = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
sLink = oWS.SpecialFolders("Desktop") & "\Timex Editor.lnk"
Set oLink = oWS.CreateShortcut(sLink)
oLink.TargetPath = appDir & "\run.vbs"
oLink.WorkingDirectory = appDir
oLink.WindowStyle = 1
oLink.Description = "مدیریت رکوردهای ورود و خروج"
oLink.IconLocation = "shell32.dll,13"
oLink.Save
MsgBox "میانبر Timex Editor روی دسکتاپ ساخته شد.", vbInformation, "Timex Editor"
