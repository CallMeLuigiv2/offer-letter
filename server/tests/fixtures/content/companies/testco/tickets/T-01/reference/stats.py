def mean(values):
    return sum(values) / len(values) if values else 0.0


def percentile(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(len(ordered) * p / 100)
    return ordered[min(index, len(ordered) - 1)]
