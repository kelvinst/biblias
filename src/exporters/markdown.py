from pathlib import Path

from model import Bible, Book


class MarkdownExporter:
    """Writes one Markdown file per book under a per-version directory.

    Each verse is a single line ending in an Obsidian block id
    (``^acf-gen-1-1``) so verses stay individually linkable.
    """

    def export(self, bible: Bible, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for book in bible.books:
            (path / f"{book.code}.md").write_text(
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
