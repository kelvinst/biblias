from pathlib import Path

from exporters.markdown import MarkdownExporter
from model import Bible, BibleMeta, Book, Chapter, Verse


def _bible() -> Bible:
    return Bible(
        meta=BibleMeta(code="KJA", name="King James Atualizada", license="copyright",
                       scope="full", source="t"),
        books=[
            Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
                Chapter(number=1, verses=[Verse(number=1, text="No princípio..."),
                                          Verse(number=2, text="E a terra...")]),
                Chapter(number=2, verses=[Verse(number=1, text="Assim foram...")]),
            ]),
            Book(id=20, code="PRO", name="Provérbios", abbrev="Pv", chapters=[
                Chapter(number=1, verses=[Verse(number=1, text="Provérbios de Salomão...")]),
            ]),
        ],
    )


def test_export_writes_one_file_per_book(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert sorted(p.name for p in out.iterdir()) == ["GEN.md", "PRO.md"]


def test_book_file_shape(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "GEN.md").read_text(encoding="utf-8") == (
        "# Gênesis\n"
        "\n"
        "## 1\n"
        "\n"
        "**1** No princípio... ^kja-gen-1-1\n"
        "\n"
        "**2** E a terra... ^kja-gen-1-2\n"
        "\n"
        "## 2\n"
        "\n"
        "**1** Assim foram... ^kja-gen-2-1\n"
    )


def test_verse_text_is_flattened_to_one_line(tmp_path: Path):
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=1, text="linha um\n  linha dois")]),
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    body = (out / "GEN.md").read_text(encoding="utf-8")
    assert "**1** linha um linha dois ^kja-gen-1-1" in body
