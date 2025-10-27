import time, statistics
from typing import Callable, Any, List

def measure_p95(fn: Callable[[], Any], warmup=5, runs=100) -> float:
    for _ in range(warmup): fn()
    samples: List[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter()-t0)*1000.0)
    samples.sort()
    idx = int(0.95*len(samples))-1
    return samples[max(0, idx)]
