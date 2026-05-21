set projectDir to "/Users/michielburger/Claude Code/AI-investing-system"
set launcherCommand to "cd " & quoted form of projectDir & " && ./scripts/launch_dashboard.sh"

tell application "Terminal"
	activate
	do script launcherCommand
end tell
