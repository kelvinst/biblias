from pathlib import Path

import books
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
    assert sorted(p.name for p in out.iterdir()) == ["01-Genesis.md", "20-Proverbios.md"]


def test_book_file_shape(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "01-Genesis.md").read_text(encoding="utf-8") == (
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
    body = (out / "01-Genesis.md").read_text(encoding="utf-8")
    assert "**1** linha um linha dois ^kja-gen-1-1" in body


def test_filenames_sort_in_canonical_order():
    from exporters.markdown import _filename

    names = [_filename(Book(id=ref.id, code=ref.code, name=ref.name, abbrev=ref.abbrev,
                            chapters=[])) for ref in books.BOOKS]
    assert names == sorted(names)
    assert names[0] == "01-Genesis.md"
    assert names[8] == "09-1 Samuel.md"
    assert names[24] == "25-Lamentacoes de Jeremias.md"
    assert names[65] == "66-Apocalipse.md"


def test_filenames_have_no_accents():
    from exporters.markdown import _filename

    for ref in books.BOOKS:
        name = _filename(Book(id=ref.id, code=ref.code, name=ref.name, abbrev=ref.abbrev,
                              chapters=[]))
        assert name.isascii(), name
