from pathlib import Path

import books
from exporters.markdown import MarkdownExporter, _book_dirname, _chapter_filename
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


def test_export_writes_a_folder_per_book(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert sorted(p.name for p in out.iterdir()) == ["01-Genesis", "20-Proverbios"]


def test_export_writes_a_file_per_chapter(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert sorted(p.name for p in (out / "01-Genesis").iterdir()) == [
        "Genesis-001.md", "Genesis-002.md",
    ]
    assert [p.name for p in (out / "20-Proverbios").iterdir()] == ["Proverbios-001.md"]


def test_chapter_file_shape(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "01-Genesis" / "Genesis-001.md").read_text(encoding="utf-8") == (
        "# Gênesis 1\n"
        "\n"
        "**1** No princípio... ^kja-gen-1-1\n"
        "\n"
        "**2** E a terra... ^kja-gen-1-2\n"
    )
    assert (out / "01-Genesis" / "Genesis-002.md").read_text(encoding="utf-8") == (
        "# Gênesis 2\n"
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
    body = (out / "01-Genesis" / "Genesis-001.md").read_text(encoding="utf-8")
    assert "**1** linha um linha dois ^kja-gen-1-1" in body


def _ref_book(ref: books.BookRef) -> Book:
    return Book(id=ref.id, code=ref.code, name=ref.name, abbrev=ref.abbrev, chapters=[])


def test_book_folders_sort_in_canonical_order():
    names = [_book_dirname(_ref_book(ref)) for ref in books.BOOKS]
    assert names == sorted(names)
    assert names[0] == "01-Genesis"
    assert names[8] == "09-1 Samuel"
    assert names[24] == "25-Lamentacoes de Jeremias"
    assert names[65] == "66-Apocalipse"


def test_chapter_files_sort_numerically():
    book = _ref_book(books.by_code("PSA"))
    names = [_chapter_filename(book, Chapter(number=n, verses=[])) for n in (1, 2, 10, 100, 150)]
    assert names == sorted(names)
    assert names[0] == "Salmos-001.md"
    assert names[-1] == "Salmos-150.md"


def test_names_have_no_accents():
    for ref in books.BOOKS:
        book = _ref_book(ref)
        assert _book_dirname(book).isascii(), ref.name
        assert _chapter_filename(book, Chapter(number=1, verses=[])).isascii(), ref.name
