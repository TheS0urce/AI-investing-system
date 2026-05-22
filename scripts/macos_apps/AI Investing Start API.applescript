set projectDir to "/Users/michielburger/Claude Code/AI-investing-system"

try
	set resultText to do shell script "cd " & quoted form of projectDir & " && ./scripts/install_launch_agent.sh"
	display dialog resultText with title "AI Investing Start API" buttons {"OK"} default button "OK"
on error errMsg number errNum
	display dialog "Start failed (" & errNum & "): " & errMsg with title "AI Investing Start API" buttons {"OK"} default button "OK" with icon stop
end try
