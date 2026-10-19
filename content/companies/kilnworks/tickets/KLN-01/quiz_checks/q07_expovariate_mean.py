import random

from kiln_bench.openloop import PoissonArrivals

arrivals = PoissonArrivals(40, random.Random(1))
gaps = [arrivals.next_gap() for _ in range(200_000)]
print(f"{round(sum(gaps) / len(gaps) * 1000)} ms")
