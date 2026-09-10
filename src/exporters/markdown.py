import re
import shutil
from pathlib import Path

import catalog
import metrics as metrics_mod
from catalog import Assessment, CatalogEntry
from model import Bible, BibleMeta, Book, Chapter, Verse

DEFAULT_METRICS_PATH = Path("data/stats/metrics.json")

# Rótulo de leitura para os valores que o frontmatter guarda em inglês: propriedade é
# consultada por query, corpo é lido por gente. O mapa mora aqui, no exportador, e não
# no catálogo, que registra o valor e não a forma de dizê-lo.
_TEXT_BASE_LABELS: dict[str | None, str] = {
    "textus-receptus": "Textus Receptus",
    "critical": "texto crítico",
    "eclectic": "texto eclético",
    None: "não declarada",
}
_METHOD_LABELS: dict[str, str] = {
    "formal": "equivalência formal",
    "balanced": "equivalência equilibrada",
    "functional": "equivalência funcional",
    "paraphrase": "paráfrase",
}
_TRUST_FACTORS = ("Origem direta", "Base manuscrita", "Comissão", "Transparência")
_RESPECT_FACTORS = ("Púlpito", "Seminário", "Literatura", "Transversalidade")

# A ressalva não é decoração: sem ela, quatro percentuais lado a lado numa nota de
# aparência técnica leem-se todos como dado apurado, quando dois são julgamento.
_CAVEAT = (
    "<sub>Confiança e aceitação são avaliações editoriais deste repositório, somadas "
    "de quatro fatores de 25 pontos cada, e não medições — a rubrica está em "
    "`src/catalog.py`. Integridade e legibilidade são calculadas a partir do texto "
    "canônico por `uv run biblias validate`.</sub>"
)

# (last book id in the category, folder name). Every category is a contiguous
# id range, so the first entry a book fits under is its category. The testament
# is a prefix rather than a folder of its own: nine entries read at a glance,
# and every path is a level shorter for it. Numbered straight through both
# testaments so they sort in canon order, and English, like the USFM codes
# below them -- a path names nothing in the version's own language, only the
# note bodies do.
_CATEGORY_DIRS: tuple[tuple[int, str], ...] = (
    (5, "1-OT-Law"),                # Gênesis..Deuteronômio
    (17, "2-OT-History"),           # Josué..Ester
    (22, "3-OT-Wisdom"),            # Jó..Cânticos
    (39, "4-OT-Prophets"),          # Isaías..Malaquias
    (43, "5-NT-Gospels"),           # Mateus..João
    (44, "6-NT-History"),           # Atos
    (57, "7-NT-Pauline-Epistles"),  # Romanos..Filemom
    (65, "8-NT-General-Epistles"),  # Hebreus..Judas
    (66, "9-NT-Prophecy"),          # Apocalipse
)


def _category_dirname(book: Book) -> str:
    """``1-OT-Law``: numbered across both testaments, so they sort in canon order."""
    return next(name for last_id, name in _CATEGORY_DIRS if book.id <= last_id)


def _book_dirname(code: str, book: Book) -> str:
    """``ARA-01-GEN``: zero-padded id so lexical order matches canon order.

    The USFM code, not the version's own name for the book, so the folder is
    spelled the same in every translation and needs no accents stripped out of
    it. Version-qualified like the files inside it, so two translations' Genesis
    folders stay apart in a vault holding both.
    """
    return f"{code}-{book.id:02d}-{book.code}"


def _book_dir(path: Path, code: str, book: Book) -> Path:
    return path / _category_dirname(book) / _book_dirname(code, book)


def _folder_note_filename(code: str) -> str:
    """``ARA.md``: named after the folder holding it, which is how Obsidian's
    folder-note convention binds a note to its folder. ``output_path`` names the
    version folder after the code, so the two always agree."""
    return f"{code}.md"


def _yaml_scalar(value: str | int | None) -> str:
    """A frontmatter value. ``None`` becomes an empty one, so the property still
    exists in every version's note and a query can tell blank from absent."""
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _decimal(value: float) -> str:
    """``21,4``: vírgula decimal, como o resto do corpo, que é português."""
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _rubric_table(factors: tuple[str, ...], assessment: Assessment) -> list[str]:
    return ["| Fator | Nota |", "| --- | --: |"] + [
        f"| {name} | {score} |" for name, score in zip(factors, assessment.scores)
    ]


def _superscript(label: str) -> str:
    """``176`` as ``^176^``: Markdown's own superscript, so the raising is
    markup a renderer applies rather than a separate set of characters, and the
    number in the source stays the ordinary digits a search or a script reads.

    The whole label sits inside one pair of carets, so a verse past nine -- or a
    range like ``1-2`` -- is raised as a single number rather than as digits
    raised one at a time.
    """
    return f"^{label}^"


_RANGE_PREFIX = re.compile(r"^(\d+)-(\d+)\s+")


def _verse_label_and_text(verse: Verse, numbers: frozenset[int]) -> tuple[str, str]:
    """The number to raise and the text to follow it with.

    A version that merges verses -- A Mensagem does it throughout -- carries the
    range it merged at the head of the text itself (``1-2 Em primeiro lugar``).
    Left there it prints twice: once as the raised verse number the exporter
    adds, once as the ordinary digits opening the paragraph. So the range is
    lifted out of the text and raised in place of the number, and the reader
    sees which verses the paragraph covers instead of only where it starts. A
    bare number is left alone: verses legitimately open with one (``435 camelos
    e 6.720 jumentos``), and only a range says a merge happened.

    A range is only believed when it opens at the verse's own number and climbs:
    the source carries a handful that do neither (``32-31``, ``26-1``, ``6-6``,
    and a ``28-34`` sitting at verse 25), and raising those puts a label on the
    paragraph that reads backwards or contradicts the verse it labels. Those
    stay ordinary text at the head of the line, where they are at least plainly
    part of the paragraph rather than its number.

    ``numbers`` is every verse number the chapter stores, and the range is cut
    back to stop below the next of them: a chapter that opens verse 2 with
    ``2-5`` and then stores a verse 5 of its own would otherwise raise 5 twice,
    so the first paragraph is labelled ``2-4``. Cut back to nothing, it is
    labelled with its own number alone.

    The block id keeps using the verse's own number, so a link into a merged
    paragraph stays the link it always was.
    """
    text = " ".join(verse.text.split())
    match = _RANGE_PREFIX.match(text)
    if match is None:
        return str(verse.number), text
    start, end = int(match.group(1)), int(match.group(2))
    if start != verse.number or end <= start:
        return str(verse.number), text
    end = min([end] + [number - 1 for number in numbers if start < number <= end])
    label = f"{start}-{end}" if end > start else str(start)
    return label, text[match.end():]


def _chapter_filename(code: str, book: Book, chapter: Chapter) -> str:
    """``ARA-01-GEN-001.md``: version-qualified, so it is unique across a vault.

    The USFM code, not the Portuguese name, keeps the name identical in every
    version -- only the prefix changes -- so notes line up across translations.
    """
    return f"{code}-{book.id:02d}-{book.code}-{chapter.number:03d}.md"


class MarkdownExporter:
    """Writes one Markdown file per chapter, grouped in a folder per book.

    Layout is ``<version>/1-OT-Law/ARA-01-GEN/ARA-01-GEN-001.md``. Category,
    book and chapter names are numbered so Finder and Obsidian sort them in
    canonical order, and spelled in English or as a USFM code, so a path is the
    same in every version and carries no accents; the version prefix keeps the
    note unique in a vault holding several translations. A chapter's heading
    ends in the version code (``Gênesis 1 - ARA``), so the version is named
    wherever the note itself is read -- in a search hit, a graph node or an
    embed -- and not only in its path. The chapter body is one
    verse per paragraph, opened by the verse number in Markdown superscript
    (``^1^``) -- markup, no HTML and no list marker, so the number reads as an
    ordinary number in the source and raised in a preview -- and closed by a
    block id (``^acf-gen-1-1``) so verses stay individually linkable; the id
    keeps using the USFM code, so renaming files never invalidates a link. Where
    a version merges verses and says so at the head of the text (``1-2 Em
    primeiro lugar``), that range is raised instead of the number and printed
    once rather than twice.

    Beside them sits one folder note per version, ``ARA/ARA.md``, carrying
    everything about the version that the file names cannot. Fourteen
    frontmatter properties: its full title, year, publisher, licence, scope and
    source, then the editorial classification -- Greek text base and translation
    method with the formality behind it, and the trust, respect, integrity and
    readability percentages, every one of them a bare integer so a Dataview
    query can sort and compare on it. A ``## Classificação`` section spells the
    same thing out in Portuguese prose: the two rubrics factor by factor with
    the note that argues them, the computed measures with the parts they were
    made of, and a caveat saying which two of the four numbers are judgement and
    which two are measurement. Then the books it holds as a table -- the only
    place the version's own abbreviation for a book (``Gn``) survives the export.

    The descriptive and editorial fields are read from ``catalog`` at render
    time and the computed ones from ``data/stats/metrics.json``, neither of them
    from ``BibleMeta``: the rubric prose would bloat every canonical ``meta.json``
    for no query anyone runs, and a computed number stored beside the text goes
    stale the moment a verse is corrected. A version absent from the catalog
    still exports -- it just carries no classification.

    Nothing else is written: the index of a book and the links from a chapter to
    its neighbours are navigation, and an Obsidian plugin builds those from the
    file names, so they need not be baked into the export.

    Exporting replaces the version folder wholesale, so a rename never leaves
    the previous layout sitting beside the new one.
    """

    def __init__(self, metrics_path: Path = DEFAULT_METRICS_PATH):
        self._metrics = metrics_mod.load_metrics(metrics_path)

    def export(self, bible: Bible, path: Path) -> None:
        # Rebuild from scratch: every rename of the layout used to leave the old
        # spelling on disk next to the new one. The folder holds nothing but this
        # export -- it is copied into a vault, not written inside one.
        # Only a missing folder is expected here: anything else -- a symlink, a
        # regular file, a permission error -- means the wipe did not happen, and
        # raising says so instead of leaving the old layout behind in silence.
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass
        code = bible.meta.code
        path.mkdir(parents=True, exist_ok=True)
        (path / _folder_note_filename(code)).write_text(
            self._render_folder_note(bible), encoding="utf-8"
        )
        for book in bible.books:
            book_dir = _book_dir(path, code, book)
            book_dir.mkdir(parents=True, exist_ok=True)
            for chapter in book.chapters:
                (book_dir / _chapter_filename(code, book, chapter)).write_text(
                    self._render_chapter(book, chapter, code), encoding="utf-8"
                )

    def _render_folder_note(self, bible: Bible) -> str:
        meta = bible.meta
        entry = catalog.CATALOG.get(meta.code)
        measures = self._metrics.get(meta.code)
        lines = ["---"]
        lines += [f"{key}: {_yaml_scalar(value)}".rstrip()
                  for key, value in self._properties(meta, entry, measures)]
        lines += ["---", "", f"# {meta.name}", ""]
        lines += self._classification(entry, measures)
        lines += ["| # | Código | Livro | Abreviação |",
                  "| --: | --- | --- | --- |"]
        lines += [f"| {book.id} | {book.code} | {book.name} | {book.abbrev} |"
                  for book in bible.books]
        return "\n".join(lines) + "\n"

    def _properties(
        self,
        meta: BibleMeta,
        entry: CatalogEntry | None,
        measures: dict | None,
    ) -> tuple[tuple[str, str | int | None], ...]:
        """The canonical metadata plus the classification, keyed the way ``BibleMeta``
        and the JSON export already key it. The bodies of these notes are Portuguese,
        but a property name is queried, not read, and a query written against one
        version's vault should keep working against the JSON the vault was built from.

        Every key is emitted for every version, empty value and all, so a query can tell
        blank from absent; the percentages stay bare integers, because ``"95%"`` would
        stop ``sort respect_pct desc`` and ``where trust_pct > 80`` from working.
        """
        measures = measures or {}
        return (("code", meta.code), ("name", meta.name), ("year", meta.year),
                ("publisher", meta.publisher), ("license", meta.license),
                ("scope", meta.scope), ("source", meta.source),
                ("text_base", entry.text_base if entry else None),
                ("method", entry.method if entry else None),
                ("formality_pct", entry.formality if entry else None),
                ("trust_pct", entry.trust.total if entry else None),
                ("respect_pct", entry.respect.total if entry else None),
                ("integrity_pct", measures.get("integrity")),
                ("readability_pct", measures.get("readability")))

    def _classification(self, entry: CatalogEntry | None, measures: dict | None) -> list[str]:
        """The classification in Portuguese prose. Absent for a version the catalog does
        not know; the measures subsection absent for one ``metrics.json`` does not cover."""
        if entry is None:
            return []
        lines = [
            "## Classificação", "",
            f"Base textual do Novo Testamento: **{_TEXT_BASE_LABELS[entry.text_base]}**. "
            f"Método: **{_METHOD_LABELS[entry.method]}** (formalidade {entry.formality}%).",
            "",
            f"### Confiança quanto aos originais — {entry.trust.total}%", "",
            entry.trust.note, "",
            *_rubric_table(_TRUST_FACTORS, entry.trust), "",
            f"### Aceitação — {entry.respect.total}%", "",
            entry.respect.note, "",
            *_rubric_table(_RESPECT_FACTORS, entry.respect), "",
        ]
        if measures:
            lines += [
                "### Medidas do texto", "",
                "| Medida | Valor |", "| --- | --: |",
                f"| Integridade | {measures['integrity']}% |",
                f"| Capítulos presentes | {measures['chapters_present']} de "
                f"{measures['chapters_expected']} |",
                f"| Achados graves | {measures['high']} |",
                f"| Achados leves | {measures['low']} |",
                f"| Legibilidade | {measures['readability']}% |",
                f"| Palavras por frase | {_decimal(measures['words_per_sentence'])} |",
                f"| Sílabas por palavra | {_decimal(measures['syllables_per_word'])} |",
                "",
            ]
        return lines + [_CAVEAT, ""]

    def _render_chapter(self, book: Book, chapter: Chapter, code: str) -> str:
        lines = [f"# {book.name} {chapter.number} - {code}", ""]
        numbers = frozenset(verse.number for verse in chapter.verses)
        for verse in chapter.verses:
            label, text = _verse_label_and_text(verse, numbers)
            block_id = f"{code}-{book.code}-{chapter.number}-{verse.number}".lower()
            lines += [f"{_superscript(label)} {text} ^{block_id}", ""]
        return "\n".join(lines)
