import hashlib
import re
from pathlib import Path
import sys
from typing import Sequence

from measurement import Measurement

DATA_DIR = Path.cwd() / "data"

def repo_to_filename(repository: str, header: str) -> str:
    filename = ""
    if not repository or repository == "N/A":
        filename = "measurements"
    else:
        parts = repository.replace("\\", "/").replace(":", "/").rstrip("/").split("/")
        parts = [part for part in parts if part]

        if len(parts) < 2:
            filename = "measurements.csv"

        else:
            account, repo = parts[-2], parts[-1]
            repo          = re.sub(r"\.git$", "", repo, flags = re.IGNORECASE)
            filename      = f"{account}_{repo}"

    header_hash = generate_header_hash(header)
    filename    = f"{filename}_{header_hash}"
    filename    = re.sub(r"[^\w\-]", "_", filename)
    filename    = re.sub(r"_+", "_", filename).strip("_")

    return f"{filename or 'measurements'}.csv"


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
    filename = repo_to_filename(measurement.metadata.version.repository, measurement.to_csv_header())
    path     = resolve(filename, Path(data_dir))
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

    if not measurements:
        path = resolve("measurements.csv", Path(data_dir))
        return path, 0, 0

    filename = repo_to_filename(
        measurements[0].metadata.version.repository, 
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