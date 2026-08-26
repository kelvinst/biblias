import unicodedata
from pathlib import Path

from model import Bible, Book, Chapter


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _book_dirname(book: Book) -> str:
    """``01-Genesis``: zero-padded id so lexical order matches canon order."""
    return f"{book.id:02d}-{_strip_accents(book.name)}"


def _chapter_filename(book: Book, chapter: Chapter) -> str:
    """``Genesis-001.md``: book name repeated so the note stays unique in a vault."""
    return f"{_strip_accents(book.name)}-{chapter.number:03d}.md"


class MarkdownExporter:
    """Writes one Markdown file per chapter, grouped in a folder per book.

    Layout is ``<version>/01-Genesis/Genesis-001.md``. Both names are
    zero-padded so Finder and Obsidian sort them in canonical order, and
    accents are stripped. Each verse is a single line ending in an Obsidian
    block id (``^acf-gen-1-1``) so verses stay individually linkable; the id
    keeps using the USFM code, so renaming files never invalidates a link.
    """

    def export(self, bible: Bible, path: Path) -> None:
        for book in bible.books:
            book_dir = path / _book_dirname(book)
            book_dir.mkdir(parents=True, exist_ok=True)
            for chapter in book.chapters:
                (book_dir / _chapter_filename(book, chapter)).write_text(
                    self._render_chapter(bible.meta.code, book, chapter), encoding="utf-8"
                )

    def _render_chapter(self, code: str, book: Book, chapter: Chapter) -> str:
        lines = [f"# {book.name} {chapter.number}", ""]
        for verse in chapter.verses:
            text = " ".join(verse.text.split())
            block_id = f"{code}-{book.code}-{chapter.number}-{verse.number}".lower()
            lines += [f"**{verse.number}** {text} ^{block_id}", ""]
        return "\n".join(lines)
