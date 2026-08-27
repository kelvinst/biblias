from pathlib import Path

import books
from exporters.markdown import (
    MarkdownExporter,
    _book_dirname,
    _category_dirname,
    _chapter_filename,
    _testament_dirname,
)
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


def test_export_groups_books_under_a_testament_folder(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert [p.name for p in out.iterdir()] == ["1-Antigo Testamento"]
    assert sorted(p.name for p in (out / "1-Antigo Testamento").iterdir()) == [
        "1-Lei", "3-Sabedoria",
    ]


def test_new_testament_books_land_in_their_own_folder(tmp_path: Path):
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=40, code="MAT", name="Mateus", abbrev="Mt", chapters=[
            Chapter(number=1, verses=[Verse(number=1, text="Livro da genealogia...")]),
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    assert (out / "2-Novo Testamento" / "1-Evangelhos" / "40-Mateus"
            / "KJA-40-MAT-001.md").exists()


def test_testament_folders_sort_in_canonical_order():
    names = sorted({_testament_dirname(_ref_book(ref)) for ref in books.BOOKS})
    assert names == ["1-Antigo Testamento", "2-Novo Testamento"]
    assert _testament_dirname(_ref_book(books.by_code("MAL"))) == "1-Antigo Testamento"
    assert _testament_dirname(_ref_book(books.by_code("MAT"))) == "2-Novo Testamento"


def test_export_writes_a_file_per_chapter(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert sorted(p.name for p in (out / "1-Antigo Testamento" / "1-Lei" / "01-Genesis").iterdir()) == [
        "KJA-01-GEN-001.md", "KJA-01-GEN-002.md",
    ]
    assert [p.name for p in (out / "1-Antigo Testamento" / "3-Sabedoria" / "20-Proverbios").iterdir()] == [
        "KJA-20-PRO-001.md",
    ]


def test_chapter_file_shape(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "1-Antigo Testamento" / "1-Lei" / "01-Genesis" / "KJA-01-GEN-001.md").read_text(encoding="utf-8") == (
        "# Gênesis 1\n"
        "\n"
        "**1** No princípio... ^kja-gen-1-1\n"
        "\n"
        "**2** E a terra... ^kja-gen-1-2\n"
    )
    assert (out / "1-Antigo Testamento" / "1-Lei" / "01-Genesis" / "KJA-01-GEN-002.md").read_text(encoding="utf-8") == (
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
    body = (out / "1-Antigo Testamento" / "1-Lei" / "01-Genesis" / "KJA-01-GEN-001.md").read_text(encoding="utf-8")
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
    names = [_chapter_filename("ARA", book, Chapter(number=n, verses=[]))
             for n in (1, 2, 10, 100, 150)]
    assert names == sorted(names)
    assert names[0] == "ARA-19-PSA-001.md"
    assert names[-1] == "ARA-19-PSA-150.md"


def test_chapter_filenames_differ_only_by_the_version_prefix():
    """A version calling book 22 "Cantares" must still write ``<code>-22-SNG-001.md``."""
    chapter = Chapter(number=1, verses=[])
    ara = Book(id=22, code="SNG", name="Cânticos", abbrev="Ct", chapters=[])
    nvi = Book(id=22, code="SNG", name="Cantares de Salomão", abbrev="Ct", chapters=[])
    assert _chapter_filename("ARA", ara, chapter) == "ARA-22-SNG-001.md"
    assert _chapter_filename("NVI", nvi, chapter) == "NVI-22-SNG-001.md"


def test_names_have_no_accents():
    for ref in books.BOOKS:
        book = _ref_book(ref)
        assert _book_dirname(book).isascii(), ref.name
        assert _chapter_filename("ARA", book, Chapter(number=1, verses=[])).isascii(), ref.name


_EXPECTED_CATEGORIES = {
    "1-Lei": ["GEN", "EXO", "LEV", "NUM", "DEU"],
    "2-Historia": ["JOS", "JDG", "RUT", "1SA", "2SA", "1KI", "2KI", "1CH", "2CH", "EZR",
                   "NEH", "EST", "ACT"],
    "3-Sabedoria": ["JOB", "PSA", "PRO", "ECC", "SNG"],
    "4-Profetas": ["ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO", "OBA", "JON",
                   "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL"],
    "1-Evangelhos": ["MAT", "MRK", "LUK", "JHN"],
    "3-Cartas": ["ROM", "1CO", "2CO", "GAL", "EPH", "PHP", "COL", "1TH", "2TH", "1TI",
                 "2TI", "TIT", "PHM", "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD"],
    "4-Profecia": ["REV"],
}


def test_every_book_lands_in_its_category():
    grouped: dict[str, list[str]] = {}
    for ref in books.BOOKS:
        grouped.setdefault(_category_dirname(_ref_book(ref)), []).append(ref.code)
    assert grouped == _EXPECTED_CATEGORIES


def test_category_names_are_ascii_and_ordered():
    for testament in ("OT", "NT"):
        names = sorted({_category_dirname(_ref_book(ref)) for ref in books.BOOKS
                        if ref.testament == testament})
        assert all(n.isascii() for n in names), names
        assert [n[0] for n in names] == sorted(n[0] for n in names)
