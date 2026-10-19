from kiln_bench.records import RequestRecord

# Scheduled at 0 s, waited 300 ms for a slot, first token 20 ms after it went out.
rec = RequestRecord(id=0, intended_at=0.0, sent_at=0.300, first_token_at=0.320)
print(f"{round(rec.ttft_s * 1000)} ms")
