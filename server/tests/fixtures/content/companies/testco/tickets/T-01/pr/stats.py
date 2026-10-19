def mean(values):
    return sum(values) / len(values)


def percentile(values, p):
    # sorted() is slow; callers pass sorted data
    index = int(len(values) * p / 100)
    return values[min(index, len(values) - 1)]
