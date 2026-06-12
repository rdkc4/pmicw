import hashlib
import re
from pathlib import Path
import sys
from typing import Sequence

from measurement import Measurement
from paths import DATA_DIR

def repo_to_filename(repository: str, workload_name: str, header: str) -> str:
    """
    Transforms repository into a csv storage file name

    repository: url to the repository\n
    workload_name: name of the workload that is being benchmarked\n
    header: csv header

    Returns formatted filename: account_repository_workload-name_md5(header)

    Note: md5(header) prevents invalidation of csv storage files if workload remains the same and config is changes
    """
    filename = ""
    if not repository or repository == "N/A":
        filename = f"measurements_{workload_name}"

    else:
        parts = repository.replace("\\", "/").replace(":", "/").rstrip("/").split("/")
        parts = [part for part in parts if part]

        if len(parts) < 2:
            filename = f"measurements_{workload_name}"

        else:
            account, repo = parts[-2], parts[-1]
            repo          = re.sub(r"\.git$", "", repo, flags = re.IGNORECASE)
            filename      = f"{account}_{repo}_{workload_name}"

    header_hash = generate_header_hash(header)
    filename    = f"{filename}_{header_hash}"
    filename    = re.sub(r"[^\w\-]", "_", filename)
    filename    = re.sub(r"_+", "_", filename).strip("_")

    return f"{filename}.csv"

def resolve(filename: str, data_dir: Path) -> Path:
    return data_dir / filename

def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)

def needs_header(path: Path) -> bool:
    return not path.exists() or path.stat().st_size == 0

def generate_header_hash(header_string: str) -> str:
    if not header_string:
        return "empty"

    return hashlib.md5(header_string.encode("utf-8")).hexdigest()[:8]

def write(
    measurement: Measurement,
    data_dir:    str | Path = DATA_DIR,
    encoding:    str        = "utf-8",
) -> Path | None:
    """
    Appends csv storage with a new measurement

    measurement: benchmarking results of the current run
    data_dir: csv storage directory
    encoding: text encoding

    Returns path to a csv storage file if write was successful,
    None otherwise
    """

    filename = repo_to_filename(
        measurement.metadata.version.repository, 
        measurement.workload.name, 
        measurement.to_csv_header()
    )
    
    path = resolve(filename, Path(data_dir))
    ensure_dir(path)

    try:
        with path.open("a", encoding = encoding, newline = "") as f:
            if needs_header(path):
                f.write(measurement.to_csv_header() + "\n")

            f.write(measurement.data_to_csv() + "\n")

    except OSError as e:
        print(f"Failed to write measurement: {e}", file = sys.stderr)
        return None

    return path

def write_batch(
    measurements: Sequence[Measurement],
    data_dir:     str | Path = DATA_DIR,
    encoding:     str        = "utf-8",
) -> tuple[Path | None, int, int]:
    """
    Appends csv storage with a sequence of measurements

    measurements: sequence of measurements
    data_dir: csv storage directory
    encoding: text encoding

    Returns path, number of successful writes, number of failed writes,
    or None, 0, 0 if it fails to open the storage or if sequence is empty
    """

    if not measurements:
        return None, 0, 0

    # assumption: all measurements in a sequence are from the same workload
    filename = repo_to_filename(
        measurements[0].metadata.version.repository, 
        measurements[0].workload.name,
        measurements[0].to_csv_header()
    )
    
    path = resolve(filename, Path(data_dir))
    ensure_dir(path)

    written = 0
    errors  = 0

    try:
        with path.open("a", encoding = encoding, newline = "") as f:
            if needs_header(path):
                f.write(measurements[0].to_csv_header() + "\n")

            for measurement in measurements:
                try:
                    f.write(measurement.data_to_csv() + "\n")
                    written += 1

                except Exception:
                    errors += 1

    except OSError as e:
        print(f"Failed to write measurements: {e}", file = sys.stderr)
        return None, 0, 0

    return path, written, errors