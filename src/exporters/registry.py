from pathlib import Path

from exporters.base import Exporter
from exporters.json import JsonExporter
from exporters.markdown import MarkdownExporter
from exporters.sqlite import SqliteExporter
from exporters.zefania import ZefaniaExporter

EXTENSIONS: dict[str, str] = {
    "zefania": "xml", "sqlite": "sqlite", "json": "json", "markdown": "md",
}

# Formats that write a tree of files into a directory instead of a single file.
DIRECTORY_FORMATS: frozenset[str] = frozenset({"markdown"})


def make_exporter(fmt: str) -> Exporter:
    if fmt == "zefania":
        return ZefaniaExporter()
    if fmt == "sqlite":
        return SqliteExporter()
    if fmt == "json":
        return JsonExporter()
    if fmt == "markdown":
        return MarkdownExporter()
    raise ValueError(f"Formato desconhecido: {fmt}")


def output_path(fmt: str, out_dir: Path, code: str) -> Path:
    """Target handed to the exporter: a directory for tree formats, a file otherwise."""
    if fmt in DIRECTORY_FORMATS:
        return out_dir / code
    return out_dir / f"{code}.{EXTENSIONS[fmt]}"
