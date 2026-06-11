from __future__ import annotations
import duckdb
import pandas as pd

def get_connection():
    return duckdb.connect()

def base_table(csv_path: str) -> str:
    return f"read_csv_auto('{csv_path}')"

def fetch_last_n(n: int, contender_id: str, workload_name: str, csv_path: str) -> str:
    table     = base_table(csv_path)
    condition = f"run_id = '{contender_id}' AND workload_name = '{workload_name}'"

    return f"""
    WITH contender AS (
        SELECT *
        FROM {table}
        WHERE {condition}
    ),
    baselines AS (
        SELECT *
        FROM {table}
        WHERE NOT ({condition})
        ORDER BY timestamp DESC
        LIMIT {n}
    )
    SELECT * FROM baselines
    UNION ALL
    SELECT * FROM contender
    """

def fetch_two(baseline_id: str, contender_id: str, workload_name: str, csv_path: str) -> str:
    where_clause = f"WHERE run_id IN ('{baseline_id}', '{contender_id}') AND workload_name = '{workload_name}'"
    
    return f"""
    SELECT *
    FROM {base_table(csv_path)}
    {where_clause}
    """

def fetch(run_id: str, workload_name: str, csv_path: str) -> str:
    where_clause = f"WHERE run_id = '{run_id}' AND workload_name = '{workload_name}'"
    
    return f"""
    SELECT *
    FROM {base_table(csv_path)}
    {where_clause}
    """

def execute_query(query: str) -> pd.DataFrame:
    con = get_connection()
    return con.execute(query).df()
