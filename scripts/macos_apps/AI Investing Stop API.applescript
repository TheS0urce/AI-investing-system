set projectDir to "/Users/michielburger/Claude Code/AI-investing-system"

display dialog "Stop and remove the persistent AI Investing API service?" with title "AI Investing Stop API" buttons {"Cancel", "Stop API"} default button "Stop API" cancel button "Cancel" with icon caution

try
	set resultText to do shell script "cd " & quoted form of projectDir & " && ./scripts/uninstall_launch_agent.sh"
	display dialog resultText with title "AI Investing Stop API" buttons {"OK"} default button "OK"
on error errMsg number errNum
	display dialog "Stop failed (" & errNum & "): " & errMsg with title "AI Investing Stop API" buttons {"OK"} default button "OK" with icon stop
end try
