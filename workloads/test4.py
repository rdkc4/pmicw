#!/usr/bin/env python3
import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from concurrent.futures import ThreadPoolExecutor
import numpy as np

def gil_released_heavy_worker(matrix_size: int = 512):
    a = np.random.randn(matrix_size, matrix_size).astype(np.float32)
    U, S, Vt = np.linalg.svd(a)
    return float(np.sum(S))

def run_parallel_workload():
    cpu_cores = os.cpu_count() or 4
    
    num_workers = cpu_cores 
    
    total_tasks = num_workers * 3
    results = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(gil_released_heavy_worker) for _ in range(total_tasks)]
        
        for i, future in enumerate(futures):
            res = future.result()
            results.append(res)
            print(f" -> Task {i+1}/{total_tasks} completed.")
            

if __name__ == "__main__":
    run_parallel_workload()