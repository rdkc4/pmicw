#!/usr/bin/env python3
import math
import threading
import numpy as np

def cpu_task(n: int = 10_000_000):
    print("Starting CPU task...")
    acc = 0
    for i in range(n):
        acc += math.sqrt(i % 1000)
    print("CPU task done.")
    return acc

def memory_task(size_mb: int = 100):
    print("Starting Memory task...")
    arr = np.random.rand(size_mb * 250_000)
    total = np.sum(arr)
    print("Memory task done.")
    return total

def thread_task(workers: int = 4):
    print("Starting Threaded task...")
    threads = []

    def worker(idx):
        print(f"Thread {idx} starting")
        s = sum(math.sin(i) for i in range(1_000_000))
        print(f"Thread {idx} done")

    for i in range(workers):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    print("Threaded task done.")

if __name__ == "__main__":
    cpu_result = cpu_task()
    mem_result = memory_task()
    thread_task()