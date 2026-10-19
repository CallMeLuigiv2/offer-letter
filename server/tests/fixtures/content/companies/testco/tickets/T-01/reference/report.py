from stats import mean, percentile


def summarize(latencies):
    return {"mean_ms": round(mean(latencies), 1), "p99_ms": percentile(latencies, 99)}
