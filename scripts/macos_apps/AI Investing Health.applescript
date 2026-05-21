set projectDir to "/Users/michielburger/Claude Code/AI-investing-system"
set healthUrl to "http://127.0.0.1:8001/health"

try
	set resultText to do shell script "cd " & quoted form of projectDir & " && /usr/bin/curl -s " & quoted form of healthUrl
	display dialog resultText with title "AI Investing Health" buttons {"OK"} default button "OK"
on error errMsg number errNum
	display dialog "Health check failed (" & errNum & "): " & errMsg with title "AI Investing Health" buttons {"OK"} default button "OK" with icon stop
end try
