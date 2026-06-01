from __future__ import annotations
import duckdb
import pandas as pd
pd.set_option("display.max_columns", None)

def get_connection():
    return duckdb.connect()

def base_table(csv_path: str) -> str:
    return f"read_csv_auto('{csv_path}')"

def compare_last_n(n: int, workload: str, csv_path: str) -> str:
    where_clause = f"WHERE workload_name = '{workload}'"

    return f"""
    SELECT *
    FROM {base_table(csv_path)}
    {where_clause}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY workload_name
        ORDER BY timestamp DESC
    ) <= {n}
    """

def compare_two(run_id_1: str, run_id_2: str, workload: str, csv_path: str) -> str:
    where_clause = f"WHERE run_id IN ('{run_id_1}', '{run_id_2}') AND workload_name = '{workload}'"
    
    return f"""
    SELECT *
    FROM {base_table(csv_path)}
    {where_clause}
    """

def compare_with(run_id: str, workload: str, csv_path: str) -> str:
    where_clause = f"WHERE run_id = '{run_id}' AND workload_name = '{workload}'"
    
    return f"""
    SELECT *
    FROM {base_table(csv_path)}
    {where_clause}
    """

def execute_query(query: str) -> pd.DataFrame:
    con = get_connection()
    return con.execute(query).df()
