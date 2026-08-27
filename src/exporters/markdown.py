import unicodedata
from pathlib import Path

import books
from model import Bible, Book, Chapter


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


_TESTAMENT_DIRS = {"OT": "1-Antigo Testamento", "NT": "2-Novo Testamento"}

# (last book id in the category, folder name). Every category is a contiguous
# id range, so the first entry a book fits under is its category.
_CATEGORY_DIRS: tuple[tuple[int, str], ...] = (
    (5, "1-Lei"),               # Gênesis..Deuteronômio
    (17, "2-História"),         # Josué..Ester
    (22, "3-Sabedoria"),        # Jó..Cânticos
    (39, "4-Profetas"),         # Isaías..Malaquias
    (43, "1-Evangelhos"),       # Mateus..João
    (44, "2-História"),         # Atos
    (65, "3-Cartas"),           # Romanos..Judas
    (66, "4-Profecia"),         # Apocalipse
)


def _testament_dirname(book: Book) -> str:
    """``1-Antigo Testamento``: numbered so the two sort in canonical order."""
    return _TESTAMENT_DIRS[books.by_id(book.id).testament]


def _category_dirname(book: Book) -> str:
    """``1-Lei``: numbered within its testament so the categories stay in order."""
    return next(_strip_accents(name) for last_id, name in _CATEGORY_DIRS
                if book.id <= last_id)


def _book_dirname(book: Book) -> str:
    """``01-Genesis``: zero-padded id so lexical order matches canon order."""
    return f"{book.id:02d}-{_strip_accents(book.name)}"


def _book_note_filename(book: Book) -> str:
    """``01-Genesis.md``: an Obsidian folder note, so it must match the folder name.

    That means it is *not* version-qualified like the chapter files are: the
    folder it indexes is not either, and the name has to match exactly for
    Obsidian to fold the note into the folder.
    """
    return f"{_book_dirname(book)}.md"


def _chapter_filename(code: str, book: Book, chapter: Chapter) -> str:
    """``ARA-01-GEN-001.md``: version-qualified, so it is unique across a vault.

    The USFM code, not the Portuguese name, keeps the name identical in every
    version -- only the prefix changes -- so notes line up across translations.
    """
    return f"{code}-{book.id:02d}-{book.code}-{chapter.number:03d}.md"


class MarkdownExporter:
    """Writes one Markdown file per chapter, grouped in a folder per book.

    Layout is ``<version>/1-Antigo Testamento/1-Lei/01-Genesis/
    ARA-01-GEN-001.md``, with an ``01-Genesis.md`` folder note beside the
    chapters indexing them. Testament, category, book and chapter names are
    numbered so Finder and Obsidian sort them in canonical order, accents are
    stripped, and the version prefix keeps the note unique in a vault holding
    several translations. The chapter body is a plain Markdown ordered list --
    no HTML -- one verse per line, each ending in a block id (``^acf-gen-1-1``)
    so verses stay individually linkable; the id keeps using the USFM code, so
    renaming files never invalidates a link.
    """

    def export(self, bible: Bible, path: Path) -> None:
        for book in bible.books:
            book_dir = (path / _testament_dirname(book) / _category_dirname(book)
                        / _book_dirname(book))
            book_dir.mkdir(parents=True, exist_ok=True)
            (book_dir / _book_note_filename(book)).write_text(
                self._render_book_note(bible.meta.code, book), encoding="utf-8"
            )
            for chapter in book.chapters:
                (book_dir / _chapter_filename(bible.meta.code, book, chapter)).write_text(
                    self._render_chapter(bible.meta.code, book, chapter), encoding="utf-8"
                )

    def _render_book_note(self, code: str, book: Book) -> str:
        """Index page for the book: the title, then one link per chapter."""
        lines = [f"# {book.name}", ""]
        for chapter in book.chapters:
            note = _chapter_filename(code, book, chapter).removesuffix(".md")
            lines.append(f"- [[{note}|{chapter.number}]]")
        return "\n".join(lines + [""])

    def _render_chapter(self, code: str, book: Book, chapter: Chapter) -> str:
        lines = [f"# {book.name} {chapter.number}", ""]
        for verse in chapter.verses:
            text = " ".join(verse.text.split())
            block_id = f"{code}-{book.code}-{chapter.number}-{verse.number}".lower()
            lines.append(f"{verse.number}. {text} ^{block_id}")
        return "\n".join(lines) + "\n"
