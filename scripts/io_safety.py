"""Small helpers for read-only audit commands that optionally emit JSON."""
from pathlib import Path


def protect_inputs(output: Path, inputs: list[Path]) -> None:
    """Refuse same path, symlink, or existing hardlink aliases to an input."""
    output = Path(output)
    for source in inputs:
        source = Path(source)
        same_name = output.resolve() == source.resolve()
        same_inode = output.exists() and source.exists() and output.samefile(source)
        if same_name or same_inode:
            raise ValueError(f"report output would overwrite an input: {source}")
