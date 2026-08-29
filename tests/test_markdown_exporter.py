from pathlib import Path

import books
from exporters.markdown import (
    MarkdownExporter,
    _book_dirname,
    _category_dirname,
    _chapter_filename,
)
from model import Bible, BibleMeta, Book, Chapter, Verse


def _bible() -> Bible:
    return Bible(
        meta=BibleMeta(code="KJA", name="King James Atualizada", year=1999,
                       publisher="Abba Press", license="copyright", scope="full",
                       source="openlp_sqlite"),
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


def test_export_groups_books_under_a_category_folder(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert sorted(p.name for p in out.iterdir()) == ["1-OT-Law", "3-OT-Wisdom", "KJA.md"]


def test_new_testament_books_land_in_their_own_category(tmp_path: Path):
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=40, code="MAT", name="Mateus", abbrev="Mt", chapters=[
            Chapter(number=1, verses=[Verse(number=1, text="Livro da genealogia...")]),
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    assert (out / "5-NT-Gospels" / "KJA-40-MAT"
            / "KJA-40-MAT-001.md").exists()


def test_the_testament_is_a_prefix_on_the_category_not_a_folder_of_its_own():
    """One flat level: the last OT category and the first NT one are siblings."""
    assert _category_dirname(_ref_book(books.by_code("MAL"))) == "4-OT-Prophets"
    assert _category_dirname(_ref_book(books.by_code("MAT"))) == "5-NT-Gospels"


def test_export_writes_a_file_per_chapter(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert sorted(p.name for p in (out / "1-OT-Law" / "KJA-01-GEN").iterdir()) == [
        "KJA-01-GEN-001.md", "KJA-01-GEN-002.md",
    ]
    assert sorted(p.name for p in (out / "3-OT-Wisdom" / "KJA-20-PRO").iterdir()) == [
        "KJA-20-PRO-001.md",
    ]


def test_export_writes_no_index_for_a_book(tmp_path: Path):
    """The book index is navigation, and an Obsidian plugin builds that itself."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert not (out / "1-OT-Law" / "KJA-01-GEN" / "KJA-01-GEN.md").exists()


def test_the_folder_note_is_named_after_the_version_folder(tmp_path: Path):
    """Obsidian binds a folder note to its folder by the name they share."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "KJA.md").exists()


def test_the_folder_note_carries_the_version_metadata(tmp_path: Path):
    """The one place the licence, the publisher and the full title survive."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "KJA.md").read_text(encoding="utf-8") == (
        "---\n"
        'code: "KJA"\n'
        'name: "King James Atualizada"\n'
        "year: 1999\n"
        'publisher: "Abba Press"\n'
        'license: "copyright"\n'
        'scope: "full"\n'
        'source: "openlp_sqlite"\n'
        "---\n"
        "\n"
        "# King James Atualizada\n"
        "\n"
        "| # | Código | Livro | Abreviação |\n"
        "| --: | --- | --- | --- |\n"
        "| 1 | GEN | Gênesis | Gn |\n"
        "| 20 | PRO | Provérbios | Pv |\n"
    )


def test_the_book_table_is_the_only_place_the_abbreviation_survives(tmp_path: Path):
    """Nothing else in the export spells a book the version's own short way."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert "| 20 | PRO | Provérbios | Pv |" in (out / "KJA.md").read_text(encoding="utf-8")


def test_a_missing_property_is_written_blank_rather_than_dropped(tmp_path: Path):
    """The property exists in every version's note, so a query can find the gap."""
    bible = Bible(
        meta=BibleMeta(code="NVI", name="Nova Versão Internacional", license="copyright",
                       scope="full", source="openlp_sqlite"),
        books=[],
    )
    out = tmp_path / "NVI"
    MarkdownExporter().export(bible, out)
    body = (out / "NVI.md").read_text(encoding="utf-8")
    assert "\nyear:\n" in body
    assert "\npublisher:\n" in body


def test_the_folder_note_carries_no_links(tmp_path: Path):
    """The book table is data; listing the chapters would be navigation."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert "[[" not in (out / "KJA.md").read_text(encoding="utf-8")


def test_a_quote_in_a_property_is_escaped(tmp_path: Path):
    bible = Bible(
        meta=BibleMeta(code="XX", name='Bíblia "Aspas"', license="copyright",
                       scope="full", source="t"),
        books=[],
    )
    out = tmp_path / "XX"
    MarkdownExporter().export(bible, out)
    assert 'name: "Bíblia \\"Aspas\\""' in (out / "XX.md").read_text(encoding="utf-8")


def test_chapter_file_shape(tmp_path: Path):
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "1-OT-Law" / "KJA-01-GEN" / "KJA-01-GEN-001.md").read_text(encoding="utf-8") == (
        "# Gênesis 1\n"
        "\n"
        "1. No princípio... ^kja-gen-1-1\n"
        "2. E a terra... ^kja-gen-1-2\n"
    )
    assert (out / "1-OT-Law" / "KJA-01-GEN" / "KJA-01-GEN-002.md").read_text(encoding="utf-8") == (
        "# Gênesis 2\n"
        "\n"
        "1. Assim foram... ^kja-gen-2-1\n"
    )


def test_a_chapter_carries_no_links_to_its_neighbours(tmp_path: Path):
    """The plugin derives the neighbours from the file names; the export need not."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    body = (out / "3-OT-Wisdom" / "KJA-20-PRO"
            / "KJA-20-PRO-001.md").read_text(encoding="utf-8")
    assert "[[" not in body


def test_export_replaces_whatever_was_in_the_folder(tmp_path: Path):
    """A rename must not leave the previous layout sitting beside the new one."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    old_dir = out / "1-OT-Law" / "KJA-01-Genesis"  # pre-code folder
    old_dir.mkdir()
    (old_dir / "KJA-01-Genesis.md").write_text("velho", encoding="utf-8")

    MarkdownExporter().export(_bible(), out)

    assert not old_dir.exists()
    assert sorted(p.name for p in (out / "1-OT-Law"
                                   / "KJA-01-GEN").iterdir()) == [
        "KJA-01-GEN-001.md", "KJA-01-GEN-002.md",
    ]


def test_export_works_when_the_folder_does_not_exist_yet(tmp_path: Path):
    out = tmp_path / "nova" / "KJA"
    MarkdownExporter().export(_bible(), out)
    assert (out / "1-OT-Law" / "KJA-01-GEN"
            / "KJA-01-GEN-001.md").exists()


def test_verse_text_is_flattened_to_one_line(tmp_path: Path):
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=1, text="linha um\n  linha dois")]),
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    body = (out / "1-OT-Law" / "KJA-01-GEN" / "KJA-01-GEN-001.md").read_text(encoding="utf-8")
    assert "1. linha um linha dois ^kja-gen-1-1" in body


def _ref_book(ref: books.BookRef) -> Book:
    return Book(id=ref.id, code=ref.code, name=ref.name, abbrev=ref.abbrev, chapters=[])


def test_book_folders_sort_in_canonical_order():
    names = [_book_dirname("ARA", _ref_book(ref)) for ref in books.BOOKS]
    assert names == sorted(names)
    assert names[0] == "ARA-01-GEN"
    assert names[8] == "ARA-09-1SA"
    assert names[24] == "ARA-25-LAM"
    assert names[65] == "ARA-66-REV"


def test_chapter_files_sort_numerically():
    book = _ref_book(books.by_code("PSA"))
    names = [_chapter_filename("ARA", book, Chapter(number=n, verses=[]))
             for n in (1, 2, 10, 100, 150)]
    assert names == sorted(names)
    assert names[0] == "ARA-19-PSA-001.md"
    assert names[-1] == "ARA-19-PSA-150.md"


def test_book_folders_differ_only_by_the_version_prefix():
    """A version calling book 22 "Cantares" must still get ``<code>-22-SNG``."""
    ara = Book(id=22, code="SNG", name="Cânticos", abbrev="Ct", chapters=[])
    nvi = Book(id=22, code="SNG", name="Cantares de Salomão", abbrev="Ct", chapters=[])
    assert _book_dirname("ARA", ara) == "ARA-22-SNG"
    assert _book_dirname("NVI", nvi) == "NVI-22-SNG"


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
    "1-OT-Law": ["GEN", "EXO", "LEV", "NUM", "DEU"],
    "2-OT-History": ["JOS", "JDG", "RUT", "1SA", "2SA", "1KI", "2KI", "1CH", "2CH", "EZR",
                     "NEH", "EST"],
    "3-OT-Wisdom": ["JOB", "PSA", "PRO", "ECC", "SNG"],
    "4-OT-Prophets": ["ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO", "OBA", "JON",
                      "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL"],
    "5-NT-Gospels": ["MAT", "MRK", "LUK", "JHN"],
    "6-NT-History": ["ACT"],
    "7-NT-Letters": ["ROM", "1CO", "2CO", "GAL", "EPH", "PHP", "COL", "1TH", "2TH", "1TI",
                     "2TI", "TIT", "PHM", "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN",
                     "JUD"],
    "8-NT-Prophecy": ["REV"],
}


def test_every_book_lands_in_its_category():
    grouped: dict[str, list[str]] = {}
    for ref in books.BOOKS:
        grouped.setdefault(_category_dirname(_ref_book(ref)), []).append(ref.code)
    assert grouped == _EXPECTED_CATEGORIES


def test_category_folders_are_ascii_and_sort_in_canonical_order():
    """One flat level, so the numbering has to run straight through both testaments."""
    names = [_category_dirname(_ref_book(ref)) for ref in books.BOOKS]
    assert all(n.isascii() for n in names), names
    assert sorted(set(names), key=names.index) == sorted(set(names))
