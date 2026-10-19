def mean(values):
    return sum(values) / len(values)


def percentile(values, p):
    ordered = sorted(values)
    index = int(len(ordered) * p / 100)
    return ordered[min(index, len(ordered) - 1)]
