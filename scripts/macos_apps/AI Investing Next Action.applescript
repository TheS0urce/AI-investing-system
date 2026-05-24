set projectDir to "/Users/michielburger/Claude Code/AI-investing-system"

try
	set resultText to do shell script "cd " & quoted form of projectDir & " && .venv/bin/python scripts/paper_next_action.py"
	display dialog resultText with title "AI Investing Next Action" buttons {"OK"} default button "OK"
on error errMsg number errNum
	display dialog "Next action check failed (" & errNum & "): " & errMsg with title "AI Investing Next Action" buttons {"OK"} default button "OK" with icon stop
end try
