import json
from pathlib import Path

import books
import catalog
from exporters.markdown import (
    _CAVEAT,
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
    """The one place the licence, the publisher, the full title and the editorial
    classification survive. Rendered without ``metrics.json``, so the note shows the
    shape a version has before anything is computed for it."""
    entry = catalog.get("KJA")
    out = tmp_path / "KJA"
    MarkdownExporter(metrics_path=tmp_path / "absent.json").export(_bible(), out)
    assert (out / "KJA.md").read_text(encoding="utf-8") == (
        "---\n"
        'code: "KJA"\n'
        'name: "King James Atualizada"\n'
        "year: 1999\n"
        'publisher: "Abba Press"\n'
        'license: "copyright"\n'
        'scope: "full"\n'
        'source: "openlp_sqlite"\n'
        'text_base: "eclectic"\n'
        'method: "balanced"\n'
        "formality_pct: 62\n"
        "trust_pct: 65\n"
        "respect_pct: 50\n"
        "integrity_pct:\n"
        "readability_pct:\n"
        "---\n"
        "\n"
        "# King James Atualizada\n"
        "\n"
        "## Classificação\n"
        "\n"
        "Base textual do Novo Testamento: **texto eclético**. "
        "Método: **equivalência equilibrada** (formalidade 62%).\n"
        "\n"
        "### Confiança quanto aos originais — 65%\n"
        "\n"
        f"{entry.trust.note}\n"
        "\n"
        "| Fator | Nota |\n"
        "| --- | --: |\n"
        "| Origem direta | 18 |\n"
        "| Base manuscrita | 17 |\n"
        "| Comissão | 15 |\n"
        "| Transparência | 15 |\n"
        "\n"
        "### Aceitação — 50%\n"
        "\n"
        f"{entry.respect.note}\n"
        "\n"
        "| Fator | Nota |\n"
        "| --- | --: |\n"
        "| Púlpito | 14 |\n"
        "| Seminário | 11 |\n"
        "| Literatura | 12 |\n"
        "| Transversalidade | 13 |\n"
        "\n"
        f"{_CAVEAT}\n"
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
        "# Gênesis 1 - KJA\n"
        "\n"
        "^1^ No princípio... ^kja-gen-1-1\n"
        "\n"
        "^2^ E a terra... ^kja-gen-1-2\n"
    )
    assert (out / "1-OT-Law" / "KJA-01-GEN" / "KJA-01-GEN-002.md").read_text(encoding="utf-8") == (
        "# Gênesis 2 - KJA\n"
        "\n"
        "^1^ Assim foram... ^kja-gen-2-1\n"
    )


def test_a_chapter_heading_names_the_version(tmp_path: Path):
    """A search hit or a graph node shows the heading, not the path, so the
    version has to be spelled inside the note for two translations of the same
    chapter to be told apart."""
    out = tmp_path / "KJA"
    MarkdownExporter().export(_bible(), out)
    body = (out / "3-OT-Wisdom" / "KJA-20-PRO"
            / "KJA-20-PRO-001.md").read_text(encoding="utf-8")
    assert body.startswith("# Provérbios 1 - KJA\n")


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
    assert "^1^ linha um linha dois ^kja-gen-1-1" in body


def test_a_multi_digit_verse_number_sits_inside_one_pair_of_carets(tmp_path: Path):
    """Psalm 119 runs to 176; a caret per digit would read as three numbers."""
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=176, text="texto")]),
        ])],
    )
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    body = (out / "1-OT-Law" / "KJA-01-GEN" / "KJA-01-GEN-001.md").read_text(encoding="utf-8")
    assert "^176^ texto ^kja-gen-1-176" in body


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
    "7-NT-Pauline-Epistles": ["ROM", "1CO", "2CO", "GAL", "EPH", "PHP", "COL", "1TH", "2TH",
                              "1TI", "2TI", "TIT", "PHM"],
    "8-NT-General-Epistles": ["HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD"],
    "9-NT-Prophecy": ["REV"],
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


def _one_verse(text: str, number: int = 1) -> Bible:
    return Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=number, text=text)]),
        ])],
    )


def _first_chapter(bible: Bible, tmp_path: Path) -> str:
    out = tmp_path / "KJA"
    MarkdownExporter().export(bible, out)
    return (out / "1-OT-Law" / "KJA-01-GEN"
            / "KJA-01-GEN-001.md").read_text(encoding="utf-8")


def test_a_merged_verse_range_is_raised_in_place_of_the_number(tmp_path: Path):
    """A Mensagem opens a merged paragraph with the range it merged; printing the
    exporter's number beside it would print the verse number twice."""
    body = _first_chapter(_one_verse("1-2 Em primeiro lugar..."), tmp_path)
    assert "^1-2^ Em primeiro lugar... ^kja-gen-1-1" in body


def test_a_merged_range_keeps_the_block_id_of_the_verse_it_starts_at(tmp_path: Path):
    """Links into a merged paragraph stay the links they always were."""
    body = _first_chapter(_one_verse("3-5 Deus disse...", number=3), tmp_path)
    assert "^3-5^ Deus disse... ^kja-gen-1-3" in body


def test_text_opening_with_a_bare_number_is_left_alone(tmp_path: Path):
    """Verses legitimately open with a number; only a range says a merge happened."""
    body = _first_chapter(_one_verse("435 camelos e 6.720 jumentos."), tmp_path)
    assert "^1^ 435 camelos e 6.720 jumentos. ^kja-gen-1-1" in body


def test_a_range_that_does_not_climb_is_left_as_ordinary_text(tmp_path: Path):
    """`32-31`, `6-6` and the like occur in the source; raised, they read backwards."""
    body = _first_chapter(_one_verse("32-31 “No dia do juízo...", number=32), tmp_path)
    assert "^32^ 32-31 “No dia do juízo... ^kja-gen-1-32" in body


def test_a_range_starting_at_another_verse_is_left_as_ordinary_text(tmp_path: Path):
    """A `28-34` sitting at verse 25 would contradict its own block id."""
    body = _first_chapter(_one_verse("28-34 O Eterno disse...", number=25), tmp_path)
    assert "^25^ 28-34 O Eterno disse... ^kja-gen-1-25" in body


def test_a_range_stops_below_the_next_verse_the_chapter_stores(tmp_path: Path):
    """A chapter opening verse 2 with `2-5` and storing a verse 5 of its own would
    otherwise raise 5 twice."""
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=2, text="2-5 Toda vez..."),
                                      Verse(number=5, text="5-6 Vocês prestaram...")]),
        ])],
    )
    body = _first_chapter(bible, tmp_path)
    assert "^2-4^ Toda vez... ^kja-gen-1-2" in body
    assert "^5-6^ Vocês prestaram... ^kja-gen-1-5" in body


def test_a_range_cut_back_to_nothing_keeps_the_verse_number_alone(tmp_path: Path):
    bible = Bible(
        meta=BibleMeta(code="KJA", name="n", license="copyright", scope="full", source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=1, text="1-2 Em primeiro lugar..."),
                                      Verse(number=2, text="Segundo...")]),
        ])],
    )
    body = _first_chapter(bible, tmp_path)
    assert "^1^ Em primeiro lugar... ^kja-gen-1-1" in body
# --- nota de pasta: propriedades e classificação ---------------------------------

_METRICS = {
    "KJA": {"integrity": 97, "chapters_present": 1189, "chapters_expected": 1189,
            "verses": 31102, "high": 12, "low": 340, "info": 900,
            "readability": 54, "words_per_sentence": 21.4, "syllables_per_word": 2.31},
}


def _folder_note(tmp_path: Path, bible: Bible | None = None, metrics: dict | None = None) -> str:
    metrics_path = tmp_path / "metrics.json"
    if metrics is not None:
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    out = tmp_path / "out"
    bible = bible or _bible()
    MarkdownExporter(metrics_path=metrics_path).export(bible, out)
    return (out / f"{bible.meta.code}.md").read_text(encoding="utf-8")


def _frontmatter(note: str) -> list[str]:
    return note.split("---\n")[1].strip().splitlines()


def test_the_frontmatter_carries_fourteen_properties_in_order(tmp_path: Path):
    keys = [line.split(":")[0] for line in _frontmatter(_folder_note(tmp_path, metrics=_METRICS))]
    assert keys == ["code", "name", "year", "publisher", "license", "scope", "source",
                    "text_base", "method", "formality_pct", "trust_pct", "respect_pct",
                    "integrity_pct", "readability_pct"]


def test_percentages_are_bare_integers(tmp_path: Path):
    note = _folder_note(tmp_path, metrics=_METRICS)
    assert "formality_pct: 62" in note
    assert "trust_pct: 65" in note
    assert "respect_pct: 50" in note
    assert "integrity_pct: 97" in note
    assert "readability_pct: 54" in note


def test_a_property_without_a_value_is_still_emitted(tmp_path: Path):
    """Vazio e ausente precisam ser distinguíveis por uma query."""
    note = _folder_note(tmp_path)   # sem metrics.json
    assert "integrity_pct:" in note
    assert "integrity_pct: " not in note.replace("integrity_pct:\n", "")
    assert "readability_pct:" in note


def test_text_base_and_method_are_english_in_the_frontmatter(tmp_path: Path):
    note = _folder_note(tmp_path)
    assert 'text_base: "eclectic"' in note
    assert 'method: "balanced"' in note


def test_the_body_names_the_text_base_and_method_in_portuguese(tmp_path: Path):
    body = _folder_note(tmp_path)
    assert "Base textual do Novo Testamento: **texto eclético**." in body
    assert "Método: **equivalência equilibrada** (formalidade 62%)." in body


def test_an_undeclared_text_base_reads_as_undeclared(tmp_path: Path):
    bible = Bible(meta=BibleMeta(code="BLIVRE", name="Bíblia Livre", license="public-domain",
                                 scope="full", source="getbible"), books=_bible().books)
    assert "Base textual do Novo Testamento: **não declarada**." in _folder_note(tmp_path, bible)


def test_the_classification_section_carries_both_rubric_tables(tmp_path: Path):
    note = _folder_note(tmp_path)
    assert "## Classificação" in note
    assert "### Confiança quanto aos originais — 65%" in note
    assert "### Aceitação — 50%" in note
    for factor in ("Origem direta", "Base manuscrita", "Comissão", "Transparência"):
        assert f"| {factor} |" in note
    for factor in ("Púlpito", "Seminário", "Literatura", "Transversalidade"):
        assert f"| {factor} |" in note


def test_the_rubric_prose_is_rendered(tmp_path: Path):
    note = _folder_note(tmp_path)
    assert catalog.get("KJA").trust.note in note
    assert catalog.get("KJA").respect.note in note


def test_the_caveat_footer_separates_judgement_from_measurement(tmp_path: Path):
    """A única defesa contra o número editorial ser lido como medição."""
    assert (
        "<sub>Confiança e aceitação são avaliações editoriais deste repositório, somadas "
        "de quatro fatores de 25 pontos cada, e não medições — a rubrica está em "
        "`src/catalog.py`. Integridade e legibilidade são calculadas a partir do texto "
        "canônico por `uv run biblias validate`.</sub>"
    ) in _folder_note(tmp_path)


def test_the_text_measures_subsection_renders_the_computed_parts(tmp_path: Path):
    note = _folder_note(tmp_path, metrics=_METRICS)
    assert "### Medidas do texto" in note
    assert "| Integridade | 97% |" in note
    assert "| Capítulos presentes | 1189 de 1189 |" in note
    assert "| Achados graves | 12 |" in note
    assert "| Achados leves | 340 |" in note
    assert "| Legibilidade | 54% |" in note
    assert "| Palavras por frase | 21,4 |" in note
    assert "| Sílabas por palavra | 2,31 |" in note


def test_the_text_measures_subsection_is_absent_without_metrics(tmp_path: Path):
    note = _folder_note(tmp_path)
    assert "### Medidas do texto" not in note
    assert "### Confiança quanto aos originais — 65%" in note


def test_metrics_for_another_version_do_not_leak_into_this_note(tmp_path: Path):
    assert "### Medidas do texto" not in _folder_note(tmp_path, metrics={"ARA": _METRICS["KJA"]})


def test_a_version_outside_the_catalog_still_exports(tmp_path: Path):
    """Um `BibleMeta` sintético não pode derrubar a build por não estar no catálogo."""
    bible = Bible(meta=BibleMeta(code="ZZZ", name="Sintética", license="copyright",
                                 scope="full", source="t"), books=_bible().books)
    note = _folder_note(tmp_path, bible)
    assert "## Classificação" not in note
    assert 'code: "ZZZ"' in note
    assert "text_base:" in note


def test_the_book_table_follows_the_classification(tmp_path: Path):
    note = _folder_note(tmp_path)
    assert note.index("## Classificação") < note.index("| # | Código | Livro | Abreviação |")
