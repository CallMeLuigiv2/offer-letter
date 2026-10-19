from stats import mean, percentile


def summarize(latencies):
    """Mean and p99 of request latencies in ms."""
    avg = mean(latencies)
    p99 = percentile(latencies, 99)
    return {"mean_ms": round(avg, 1), "p99_ms": p99}


def format_line(name, stats):
    return f"{name}: mean={stats['mean_ms']}ms p99={stats['p99_ms']}ms"
