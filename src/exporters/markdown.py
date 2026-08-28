import shutil
from pathlib import Path

from model import Bible, Book, Chapter

# Chapters per row in a book's index table. Ten keeps Salmos at 15 rows, so any
# chapter is one glance away instead of a scroll down a 150-item list.
_NOTE_COLUMNS = 10

# (last book id in the category, folder name). Every category is a contiguous
# id range, so the first entry a book fits under is its category. The testament
# is a prefix rather than a folder of its own: eight entries read at a glance,
# and every path is a level shorter for it. Numbered straight through both
# testaments so they sort in canon order, and English, like the USFM codes
# below them -- a path names nothing in the version's own language, only the
# note bodies do.
_CATEGORY_DIRS: tuple[tuple[int, str], ...] = (
    (5, "1-OT-Law"),            # Gênesis..Deuteronômio
    (17, "2-OT-History"),       # Josué..Ester
    (22, "3-OT-Wisdom"),        # Jó..Cânticos
    (39, "4-OT-Prophets"),      # Isaías..Malaquias
    (43, "5-NT-Gospels"),       # Mateus..João
    (44, "6-NT-History"),       # Atos
    (65, "7-NT-Letters"),       # Romanos..Judas
    (66, "8-NT-Prophecy"),      # Apocalipse
)


def _category_dirname(book: Book) -> str:
    """``1-OT-Law``: numbered across both testaments, so they sort in canon order."""
    return next(name for last_id, name in _CATEGORY_DIRS if book.id <= last_id)


def _book_dirname(code: str, book: Book) -> str:
    """``ARA-01-GEN``: zero-padded id so lexical order matches canon order.

    The USFM code, not the version's own name for the book, so the folder is
    spelled the same in every translation and needs no accents stripped out of
    it. Version-qualified like the files inside it, because its folder note has
    to carry the same name -- see :func:`_book_note_filename`.
    """
    return f"{code}-{book.id:02d}-{book.code}"


def _book_note_filename(code: str, book: Book) -> str:
    """``ARA-01-GEN.md``: matches the folder name, as a folder note must.

    Obsidian only folds the note into the folder when the two names are equal,
    so the folder carries the version prefix that keeps this note unique in a
    vault holding several translations.
    """
    return f"{_book_dirname(code, book)}.md"


def _book_dir(path: Path, code: str, book: Book) -> Path:
    return path / _category_dirname(book) / _book_dirname(code, book)


def _chapter_filename(code: str, book: Book, chapter: Chapter) -> str:
    """``ARA-01-GEN-001.md``: version-qualified, so it is unique across a vault.

    The USFM code, not the Portuguese name, keeps the name identical in every
    version -- only the prefix changes -- so notes line up across translations.
    """
    return f"{code}-{book.id:02d}-{book.code}-{chapter.number:03d}.md"


class MarkdownExporter:
    """Writes one Markdown file per chapter, grouped in a folder per book.

    Layout is ``<version>/1-OT-Law/ARA-01-GEN/ARA-01-GEN-001.md``, with an
    ``ARA-01-GEN.md`` folder note beside the chapters indexing them. Category,
    book and chapter names are numbered so Finder and Obsidian sort them in
    canonical order, and spelled in English or as a USFM code, so a path is the
    same in every version and carries no accents; the version prefix keeps the
    note unique in a vault holding several translations. The chapter body is a
    plain Markdown ordered list -- no HTML -- one verse per line, each ending in
    a block id (``^acf-gen-1-1``) so verses stay individually linkable; the id
    keeps using the USFM code, so renaming files never invalidates a link.

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
        for book in bible.books:
            book_dir = _book_dir(path, code, book)
            book_dir.mkdir(parents=True, exist_ok=True)
            (book_dir / _book_note_filename(code, book)).write_text(
                self._render_book_note(code, book), encoding="utf-8"
            )
        # One flat run of chapters, so a chapter's neighbours are the ones the
        # reader would turn to -- Gênesis 50 is followed by Êxodo 1, not by
        # nothing.
        sequence = [(book, chapter) for book in bible.books
                    for chapter in sorted(book.chapters, key=lambda c: c.number)]
        for position, (book, chapter) in enumerate(sequence):
            previous = sequence[position - 1] if position else None
            following = sequence[position + 1] if position + 1 < len(sequence) else None
            (_book_dir(path, code, book) / _chapter_filename(code, book, chapter)).write_text(
                self._render_chapter(code, book, chapter, previous, following),
                encoding="utf-8",
            )

    def _render_book_note(self, code: str, book: Book) -> str:
        """Index page for the book: the title, then a grid of chapter links.

        A Markdown table, ten chapters to a row, so the whole book fits on one
        screen -- a plain list put chapter 30 below the fold. Markdown has no
        table without a header, so the first ten chapters are the header rather
        than a blank strip above the grid. The pipe in a wikilink alias is
        escaped so it does not end the cell.

        Chapters are sorted by number rather than taken in source order, the
        way the zero-padded chapter file names already are.
        """
        chapters = sorted(book.chapters, key=lambda c: c.number)
        # Obadias has one chapter and should not render nine empty cells.
        columns = min(_NOTE_COLUMNS, len(chapters))

        def row(cells: list[str]) -> str:
            return "| " + " | ".join(cells + [""] * (columns - len(cells))) + " |"

        def link(chapter: Chapter) -> str:
            note = _chapter_filename(code, book, chapter).removesuffix(".md")
            return f"[[{note}\\|{chapter.number}]]"

        lines = [f"# {book.name}", "",
                 row([link(c) for c in chapters[:columns]]),
                 "|" + ":-:|" * columns]
        for start in range(columns, len(chapters), columns):
            lines.append(row([link(c) for c in chapters[start:start + columns]]))
        return "\n".join(lines + [""])

    def _render_nav(self, code: str, book: Book,
                    previous: tuple[Book, Chapter] | None,
                    following: tuple[Book, Chapter] | None) -> str:
        """``← Gênesis 1 · Gênesis · Gênesis 3 →``: the two neighbours and the index.

        The neighbours name their book because the run crosses book boundaries,
        and the first and last chapter of the export simply have one fewer link.
        """
        def link(pair: tuple[Book, Chapter], label: str) -> str:
            other, chapter = pair
            note = _chapter_filename(code, other, chapter).removesuffix(".md")
            return f"[[{note}|{label}]]"

        parts = []
        if previous:
            parts.append(link(previous, f"← {previous[0].name} {previous[1].number}"))
        parts.append(f"[[{_book_dirname(code, book)}|{book.name}]]")
        if following:
            parts.append(link(following, f"{following[0].name} {following[1].number} →"))
        return " · ".join(parts)

    def _render_chapter(self, code: str, book: Book, chapter: Chapter,
                        previous: tuple[Book, Chapter] | None,
                        following: tuple[Book, Chapter] | None) -> str:
        lines = [f"# {book.name} {chapter.number}", "",
                 self._render_nav(code, book, previous, following), ""]
        for verse in chapter.verses:
            text = " ".join(verse.text.split())
            block_id = f"{code}-{book.code}-{chapter.number}-{verse.number}".lower()
            lines.append(f"{verse.number}. {text} ^{block_id}")
        return "\n".join(lines) + "\n"
