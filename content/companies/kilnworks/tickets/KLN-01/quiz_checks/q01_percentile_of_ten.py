from kiln_bench.metrics import percentile

xs = [12, 15, 11, 14, 13, 2050, 16, 12, 15, 14]
print(percentile(sorted(xs), 99))
