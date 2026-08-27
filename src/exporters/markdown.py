import unicodedata
from pathlib import Path

import books
from model import Bible, Book, Chapter


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


_TESTAMENT_DIRS = {"OT": "1-Antigo Testamento", "NT": "2-Novo Testamento"}


def _testament_dirname(book: Book) -> str:
    """``1-Antigo Testamento``: numbered so the two sort in canonical order."""
    return _TESTAMENT_DIRS[books.by_id(book.id).testament]


def _book_dirname(book: Book) -> str:
    """``01-Genesis``: zero-padded id so lexical order matches canon order."""
    return f"{book.id:02d}-{_strip_accents(book.name)}"


def _chapter_filename(code: str, book: Book, chapter: Chapter) -> str:
    """``ARA-01-Genesis-001.md``: version-qualified, so it is unique across a vault."""
    return f"{code}-{_book_dirname(book)}-{chapter.number:03d}.md"


class MarkdownExporter:
    """Writes one Markdown file per chapter, grouped in a folder per book.

    Layout is ``<version>/1-Antigo Testamento/01-Genesis/ARA-01-Genesis-001.md``.
    Testament, book and chapter numbers are zero-padded or prefixed so Finder
    and Obsidian sort them in canonical order, accents are stripped, and the
    version prefix keeps the note unique in a vault holding several
    translations. Each verse is a single line ending in an Obsidian block id
    (``^acf-gen-1-1``) so verses stay individually linkable; the id keeps
    using the USFM code, so renaming files never invalidates a link.
    """

    def export(self, bible: Bible, path: Path) -> None:
        for book in bible.books:
            book_dir = path / _testament_dirname(book) / _book_dirname(book)
            book_dir.mkdir(parents=True, exist_ok=True)
            for chapter in book.chapters:
                (book_dir / _chapter_filename(bible.meta.code, book, chapter)).write_text(
                    self._render_chapter(bible.meta.code, book, chapter), encoding="utf-8"
                )

    def _render_chapter(self, code: str, book: Book, chapter: Chapter) -> str:
        lines = [f"# {book.name} {chapter.number}", ""]
        for verse in chapter.verses:
            text = " ".join(verse.text.split())
            block_id = f"{code}-{book.code}-{chapter.number}-{verse.number}".lower()
            lines += [f"**{verse.number}** {text} ^{block_id}", ""]
        return "\n".join(lines)
