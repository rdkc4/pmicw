#!/usr/bin/env python3
import math
import time
import threading

def io_simulation_task(files: int = 10):
    print("Starting I/O simulation task...")
    data_store = []

    for _ in range(files):
        data = [math.sqrt(j % 5000) for j in range(500_000)]
        processed = sum(data)
        data_store.append(processed)
        time.sleep(0.05)

    print("I/O simulation task done.")
    return sum(data_store)


def cpu_heavy_transform(n: int = 5_000_000):
    print("Starting CPU transform task...")
    result = 0

    for i in range(n):
        result += math.sin(i % 1000) * math.cos(i % 500)

    print("CPU transform task done.")
    return result


def parallel_hash_task(workers: int = 6):
    print("Starting parallel hash task...")
    results = []

    def worker(idx):
        local = 0
        for i in range(2_000_000):
            local += hash((idx, i)) % 1000
        results.append(local)
        print(f"Worker {idx} done")

    threads = []
    for i in range(workers):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("Parallel hash task done.")
    return sum(results)


if __name__ == "__main__":
    io_result = io_simulation_task()
    cpu_result = cpu_heavy_transform()
    parallel_hash_task()