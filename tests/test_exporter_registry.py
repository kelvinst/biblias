from pathlib import Path

import pytest

from exporters.json import JsonExporter
from exporters.markdown import MarkdownExporter
from exporters.registry import EXTENSIONS, make_exporter, output_path
from exporters.sqlite import SqliteExporter
from exporters.zefania import ZefaniaExporter


def test_make_known_exporters():
    assert isinstance(make_exporter("zefania"), ZefaniaExporter)
    assert isinstance(make_exporter("sqlite"), SqliteExporter)
    assert isinstance(make_exporter("json"), JsonExporter)
    assert isinstance(make_exporter("markdown"), MarkdownExporter)


def test_extensions():
    assert EXTENSIONS == {"zefania": "xml", "sqlite": "sqlite", "json": "json",
                          "markdown": "md"}


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        make_exporter("pdf")


def test_output_path_is_a_file_for_single_file_formats():
    assert output_path("json", Path("dist"), "KJA") == Path("dist/KJA.json")


def test_output_path_is_a_directory_for_markdown():
    assert output_path("markdown", Path("dist"), "KJA") == Path("dist/KJA")
