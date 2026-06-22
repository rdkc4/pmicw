from dataclasses import dataclass
import threading

from record_types import RecordGroup

@dataclass
class WorkloadMonitors:
    active_pid:     list[int]
    interval:       float
    activity_event: threading.Event
    shutdown_event: threading.Event
    daemon_threads: list[threading.Thread]

@dataclass
class WorkloadMetricSelection:
    wall_time: bool
    cpu:       bool
    gpu:       bool
    memory:    bool
    thread:    bool
    startup:   bool

@dataclass
class WorkloadContext:
    iterations:        int
    warmup_iterations: int
    selected_metrics:  WorkloadMetricSelection
    command:           list[str]
    env:               dict[str, str]
    records:           RecordGroup
    monitors:          WorkloadMonitors