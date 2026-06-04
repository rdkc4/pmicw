from typing import TypeAlias

Record:           TypeAlias = dict[str, float]
RecordList:       TypeAlias = list[Record]
RecordGroup:      TypeAlias = dict[str, RecordList]
FlatRecords:      TypeAlias = dict[str, list[float]]