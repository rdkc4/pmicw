def parse_perf_json_records(perf_json_records: list[dict]) -> dict[str, float]:
    metrics: dict[str, float] = {}

    for record in perf_json_records:
        event = record.get("event")
        value = record.get("counter-value")

        if event and value:
            try:
                metrics[event] = float(value)
            except ValueError:
                continue

    return metrics