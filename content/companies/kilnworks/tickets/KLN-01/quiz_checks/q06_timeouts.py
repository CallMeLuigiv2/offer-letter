"""PR branch, every 5th request stalls 3 s, --timeout 1: what does the summary say?"""

from _common import ServerThread, answer, run_cli

server = ServerThread(prefill_ms=5, itl_ms=1, stall_every=5, stall_s=3)
try:
    summary = run_cli("--url", server.url, "--rate", "10", "--arrival", "constant", "--duration", "2",
                      "--timeout", "1")
    seen = server.server.requests_seen
finally:
    server.close()

stalled = seen // 5
if summary["errors"] == 0 and summary["requests"] == seen - stalled:
    answer("They are missing: errors is 0 and the request count is lower")
if summary["errors"] == stalled:
    answer("They are counted in errors as timeouts")
answer(f"unexpected: {summary['requests']} requests, {summary['errors']} errors, server saw {seen}")
