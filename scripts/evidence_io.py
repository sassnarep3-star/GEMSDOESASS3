"""Keep published evidence immutable when a verification is reproduced."""
from datetime import datetime, timezone
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]


def choose_output(published: Path, explicit: str | None = None) -> Path:
    """Use a new cache receipt by default if the published one already exists."""
    if explicit:
        target = Path(explicit)
    elif not published.exists():
        target = published
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        target = ROOT / ".cache/reproductions" / f"{published.stem}-{stamp}-{time.time_ns()}{published.suffix}"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target
