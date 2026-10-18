Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd.exe /c cd /d C:\Users\404DESIGNLAB\.gemini\antigravity\scratch\habermat-otomasyon && python main.py >> output\cron.log 2>&1", 0, False
Set WshShell = Nothing
