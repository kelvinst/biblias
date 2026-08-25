import unicodedata
from pathlib import Path

from model import Bible, Book


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _filename(book: Book) -> str:
    """``01-Genesis.md``: zero-padded id so lexical order matches canon order."""
    return f"{book.id:02d}-{_strip_accents(book.name)}.md"


class MarkdownExporter:
    """Writes one Markdown file per book under a per-version directory.

    Files are named ``01-Genesis.md`` so Finder and Obsidian sort them in
    canonical order. Each verse is a single line ending in an Obsidian block
    id (``^acf-gen-1-1``) so verses stay individually linkable; the id keeps
    using the USFM code, so renaming files never invalidates a link.
    """

    def export(self, bible: Bible, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for book in bible.books:
            (path / _filename(book)).write_text(
                self._render_book(bible.meta.code, book), encoding="utf-8"
            )

    def _render_book(self, code: str, book: Book) -> str:
        lines = [f"# {book.name}", ""]
        for chapter in book.chapters:
            lines += [f"## {chapter.number}", ""]
            for verse in chapter.verses:
                text = " ".join(verse.text.split())
                block_id = f"{code}-{book.code}-{chapter.number}-{verse.number}".lower()
                lines += [f"**{verse.number}** {text} ^{block_id}", ""]
        return "\n".join(lines)
