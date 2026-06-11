#!/usr/bin/env python3
import numpy as np
import threading

def large_matrix_task(n: int = 2000):
    print("Starting matrix computation task...")
    a = np.random.rand(n, n)
    b = np.random.rand(n, n)

    c = np.dot(a, b)
    result = np.sum(c)

    print("Matrix task done.")
    return result


def vectorized_math_task(size: int = 20_000_000):
    print("Starting vectorized math task...")
    arr = np.random.rand(size)

    arr = np.sqrt(arr)
    arr = np.sin(arr)
    arr = np.log1p(arr)

    print("Vectorized task done.")
    return np.sum(arr)


def mixed_thread_vector_task(workers: int = 4):
    print("Starting mixed thread-vector task...")
    results = []

    def worker(idx):
        arr = np.random.rand(5_000_000)
        val = np.sum(np.sqrt(arr) * np.cos(arr))
        results.append(val)
        print(f"Thread {idx} done")

    threads = []
    for i in range(workers):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("Mixed thread-vector task done.")
    return sum(results)


if __name__ == "__main__":
    m = large_matrix_task()
    v = vectorized_math_task()
    mixed_thread_vector_task()