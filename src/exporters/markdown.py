import shutil
from pathlib import Path

from model import Bible, BibleMeta, Book, Chapter

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
    note unique in a vault holding several translations. The chapter body is one
    verse per paragraph, the number in a ``<sup>`` tag rather than a list marker
    so no indent eats into the line, each verse ending in a block id
    (``^acf-gen-1-1``) so verses stay individually linkable; the id keeps using
    the USFM code, so renaming files never invalidates a link.

    Beside them sits one folder note per version, ``ARA/ARA.md``, carrying
    everything about the version that the file names cannot: its full title,
    year, publisher, licence, scope and source as frontmatter properties, and
    the books it holds as a table -- the only place the version's own
    abbreviation for a book (``Gn``) survives the export.

    Nothing else is written: the index of a book and the links from a chapter to
    its neighbours are navigation, and an Obsidian plugin builds those from the
    file names, so they need not be baked into the export.

    Exporting replaces the version folder wholesale, so a rename never leaves
    the previous layout sitting beside the new one.
    """

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
        lines = ["---"]
        lines += [f"{key}: {_yaml_scalar(value)}".rstrip()
                  for key, value in self._properties(meta)]
        lines += ["---", "", f"# {meta.name}", "",
                  "| # | Código | Livro | Abreviação |",
                  "| --: | --- | --- | --- |"]
        lines += [f"| {book.id} | {book.code} | {book.name} | {book.abbrev} |"
                  for book in bible.books]
        return "\n".join(lines) + "\n"

    def _properties(self, meta: BibleMeta) -> tuple[tuple[str, str | int | None], ...]:
        """The canonical metadata, keyed the way ``BibleMeta`` and the JSON export
        already key it. The bodies of these notes are Portuguese, but a property
        name is queried, not read, and a query written against one version's vault
        should keep working against the JSON the vault was built from."""
        return (("code", meta.code), ("name", meta.name), ("year", meta.year),
                ("publisher", meta.publisher), ("license", meta.license),
                ("scope", meta.scope), ("source", meta.source))

    def _render_chapter(self, book: Book, chapter: Chapter, code: str) -> str:
        lines = [f"# {book.name} {chapter.number}", ""]
        for verse in chapter.verses:
            text = " ".join(verse.text.split())
            block_id = f"{code}-{book.code}-{chapter.number}-{verse.number}".lower()
            lines += [f"<sup>{verse.number}</sup> {text} ^{block_id}", ""]
        return "\n".join(lines)
