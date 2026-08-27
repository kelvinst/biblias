import re
from pathlib import Path

import books
from exporters.markdown import (
    MarkdownExporter,
    _book_dirname,
    _book_note_filename,
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
    assert (out / "2-Novo Testamento" / "1-Evangelhos" / "KJA-40-Mateus"
            / "KJA-40-MAT-001.md").exists()


def test_testament_folders_sort_in_canonical_order():
    names = sorted({_testament_dirname(_ref_book(ref)) for ref in books.BOOKS})
    assert names == ["1-Antigo Testamento", "2-Novo Testamento"]
    assert _testament_dirname(_ref_book(books.by_code("MAL"))) == "1-Antigo Testamento"
    assert _testament_dirname(_ref_book(books.by_code("MAT"))) == "2-Novo Testamento"


def test_export_writes_a_file_per_chapter(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert sorted(p.name for p in (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis").iterdir()) == [
        "KJA-01-GEN-001.md", "KJA-01-GEN-002.md", "KJA-01-Genesis.md",
    ]
    assert sorted(p.name for p in (out / "1-Antigo Testamento" / "3-Sabedoria" / "KJA-20-Proverbios").iterdir()) == [
        "KJA-20-PRO-001.md", "KJA-20-Proverbios.md",
    ]


def test_chapter_file_shape(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis" / "KJA-01-GEN-001.md").read_text(encoding="utf-8") == (
        "# Gênesis 1\n"
        "\n"
        "[[KJA-01-Genesis|Gênesis]] · [[KJA-01-GEN-002|Gênesis 2 →]]\n"
        "\n"
        "1. No princípio... ^kja-gen-1-1\n"
        "2. E a terra... ^kja-gen-1-2\n"
    )
    assert (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis" / "KJA-01-GEN-002.md").read_text(encoding="utf-8") == (
        "# Gênesis 2\n"
        "\n"
        "[[KJA-01-GEN-001|← Gênesis 1]] · [[KJA-01-Genesis|Gênesis]] "
        "· [[KJA-20-PRO-001|Provérbios 1 →]]\n"
        "\n"
        "1. Assim foram... ^kja-gen-2-1\n"
    )


def test_book_folder_note_indexes_every_chapter(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis"
            / "KJA-01-Genesis.md").read_text(encoding="utf-8") == (
        "# Gênesis\n"
        "\n"
        "| [[KJA-01-GEN-001\\|1]] | [[KJA-01-GEN-002\\|2]] |\n"
        "|:-:|:-:|\n"
    )


def test_folder_note_lists_chapters_in_order_whatever_the_source_gave(tmp_path: Path):
    """Chapter file names sort by their zero-padded number; the index must too."""
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=n, verses=[Verse(number=1, text="t")]) for n in (10, 1, 2)
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    note = (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis"
            / "KJA-01-Genesis.md").read_text(encoding="utf-8")
    assert note.splitlines()[2:] == [
        "| [[KJA-01-GEN-001\\|1]] | [[KJA-01-GEN-002\\|2]] | [[KJA-01-GEN-010\\|10]] |",
        "|:-:|:-:|:-:|",
    ]


def _cells(row: str) -> list[str]:
    """Split a table row on its real cell borders, not the escaped ones."""
    return re.split(r"(?<!\\)\|", row)[1:-1]


def test_folder_note_wraps_every_ten_chapters(tmp_path: Path):
    """Salmos must be a 15-row grid, not a 150-item list you scroll through."""
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=19, code="PSA", name="Salmos", abbrev="Sl", chapters=[
            Chapter(number=n, verses=[Verse(number=1, text="t")]) for n in range(1, 151)
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    lines = (out / "1-Antigo Testamento" / "3-Sabedoria" / "KJA-19-Salmos"
             / "KJA-19-Salmos.md").read_text(encoding="utf-8").splitlines()
    header, delimiter, body = lines[2], lines[3], lines[4:]
    assert header.startswith("| [[KJA-19-PSA-001\\|1]] |")
    assert header.endswith("| [[KJA-19-PSA-010\\|10]] |")
    assert delimiter == "|" + ":-:|" * 10
    assert len(body) == 14  # 15 rows of ten, the first of them the header
    assert body[-1].startswith("| [[KJA-19-PSA-141\\|141]] |")
    assert all(len(_cells(row)) == 10 for row in [header, *body])


def test_folder_note_pads_a_short_last_row(tmp_path: Path):
    """Every row carries ten cells, so the grid stays rectangular."""
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=n, verses=[Verse(number=1, text="t")]) for n in range(1, 13)
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    rows = (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis"
            / "KJA-01-Genesis.md").read_text(encoding="utf-8").splitlines()[4:]
    assert len(rows) == 1
    assert rows[0] == ("| [[KJA-01-GEN-011\\|11]] | [[KJA-01-GEN-012\\|12]] "
                       "|  |  |  |  |  |  |  |  |")


def test_folder_note_of_a_one_chapter_book_is_a_single_cell(tmp_path: Path):
    """Obadias should not render nine empty cells to reach ten columns."""
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=31, code="OBA", name="Obadias", abbrev="Ob", chapters=[
            Chapter(number=1, verses=[Verse(number=1, text="t")]),
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    assert (out / "1-Antigo Testamento" / "4-Profetas" / "KJA-31-Obadias"
            / "KJA-31-Obadias.md").read_text(encoding="utf-8") == (
        "# Obadias\n"
        "\n"
        "| [[KJA-31-OBA-001\\|1]] |\n"
        "|:-:|\n"
    )


def test_folder_note_is_named_after_its_folder():
    """Obsidian only treats the note as the folder's index when the names match."""
    for ref in books.BOOKS:
        book = _ref_book(ref)
        assert _book_note_filename("ARA", book) == f"{_book_dirname('ARA', book)}.md"
        assert _book_note_filename("ARA", book).isascii(), ref.name


def test_folder_notes_of_two_versions_do_not_collide():
    """The prefix is what keeps both translations' Genesis notes distinct."""
    book = _ref_book(books.by_code("GEN"))
    assert _book_note_filename("ARA", book) == "ARA-01-Genesis.md"
    assert _book_note_filename("NVI", book) == "NVI-01-Genesis.md"


def test_export_replaces_whatever_was_in_the_folder(tmp_path: Path):
    """A rename must not leave the previous layout sitting beside the new one."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    old_dir = out / "1-Antigo Testamento" / "1-Lei" / "01-Genesis"  # pre-prefix folder
    old_dir.mkdir()
    (old_dir / "KJA-01-Genesis-003.md").write_text("velho", encoding="utf-8")

    MarkdownExporter().export(_bible(), out)

    assert not old_dir.exists()
    assert sorted(p.name for p in (out / "1-Antigo Testamento" / "1-Lei"
                                   / "KJA-01-Genesis").iterdir()) == [
        "KJA-01-GEN-001.md", "KJA-01-GEN-002.md", "KJA-01-Genesis.md",
    ]


def test_export_works_when_the_folder_does_not_exist_yet(tmp_path: Path):
    out = tmp_path / "nova" / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis"
            / "KJA-01-Genesis.md").exists()


def test_chapter_nav_crosses_into_the_next_book(tmp_path: Path):
    """The last chapter of a book points at the first of the one after it."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    nav = (out / "1-Antigo Testamento" / "3-Sabedoria" / "KJA-20-Proverbios"
           / "KJA-20-PRO-001.md").read_text(encoding="utf-8").splitlines()[2]
    assert nav == ("[[KJA-01-GEN-002|← Gênesis 2]] · [[KJA-20-Proverbios|Provérbios]]")


def test_first_and_last_chapter_drop_the_link_they_have_no_neighbour_for(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    first = (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis"
             / "KJA-01-GEN-001.md").read_text(encoding="utf-8").splitlines()[2]
    last = (out / "1-Antigo Testamento" / "3-Sabedoria" / "KJA-20-Proverbios"
            / "KJA-20-PRO-001.md").read_text(encoding="utf-8").splitlines()[2]
    assert "←" not in first
    assert "→" not in last


def test_verse_text_is_flattened_to_one_line(tmp_path: Path):
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=1, text="linha um\n  linha dois")]),
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    body = (out / "1-Antigo Testamento" / "1-Lei" / "KJA-01-Genesis" / "KJA-01-GEN-001.md").read_text(encoding="utf-8")
    assert "1. linha um linha dois ^kja-gen-1-1" in body


def _ref_book(ref: books.BookRef) -> Book:
    return Book(id=ref.id, code=ref.code, name=ref.name, abbrev=ref.abbrev, chapters=[])


def test_book_folders_sort_in_canonical_order():
    names = [_book_dirname("ARA", _ref_book(ref)) for ref in books.BOOKS]
    assert names == sorted(names)
    assert names[0] == "ARA-01-Genesis"
    assert names[8] == "ARA-09-1 Samuel"
    assert names[24] == "ARA-25-Lamentacoes de Jeremias"
    assert names[65] == "ARA-66-Apocalipse"


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
        assert _book_dirname("ARA", book).isascii(), ref.name
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
