import json
from pathlib import Path

import pytest

import metrics
import versification
from model import Bible, BibleMeta, Book, Chapter, Verse
from validate import Finding, Tier


def _bible(verses: list[str], code: str = "X", scope: str = "full") -> Bible:
    return Bible(
        meta=BibleMeta(code=code, name="Teste", license="public-domain", scope=scope, source="t"),
        books=[Book(id=1, code="GEN", name="Gênesis", abbrev="Gn", chapters=[
            Chapter(number=1, verses=[Verse(number=i, text=t) for i, t in enumerate(verses, 1)]),
        ])],
    )


# --- sílabas -------------------------------------------------------------------

@pytest.mark.parametrize("word,expected", [
    ("casa", 2),
    ("terra", 2),
    ("palavra", 3),
    ("pai", 1),          # ditongo decrescente
    ("céu", 1),          # acento na primeira vogal não desfaz o ditongo
    ("Deus", 1),
    ("saudade", 3),
    ("saúde", 3),        # acento na segunda vogal desfaz: sa-ú-de
    ("país", 2),         # pa-ís
    ("história", 3),     # ditongo crescente final: his-tó-ria
    ("diante", 3),       # o mesmo par fora da posição final é hiato: di-an-te
    ("piano", 3),
    ("aqui", 2),         # o u de "qu" não forma sílaba
    ("guerra", 2),       # nem o de "gue"
    ("quando", 2),
    ("água", 2),
    ("coração", 3),      # ditongo nasal
    ("não", 1),
    ("irmãos", 2),
    ("espírito", 4),
    ("Jesus", 2),
    ("graça", 2),
])
def test_syllable_count(word: str, expected: int):
    assert metrics.count_syllables(word) == expected


# --- legibilidade ---------------------------------------------------------------

def test_readability_uses_the_adapted_flesch_formula():
    bible = _bible(["Casa casa casa casa."])   # 4 palavras, 1 frase, 2 sílabas cada
    r = metrics.readability(bible)
    assert r.words_per_sentence == pytest.approx(4.0)
    assert r.syllables_per_word == pytest.approx(2.0)
    expected = 248.835 - 1.015 * 4.0 - 84.6 * 2.0
    assert r.score == max(0, min(100, round(expected)))


def test_a_verse_without_terminal_punctuation_counts_as_one_sentence():
    assert metrics.readability(_bible(["casa casa"])).words_per_sentence == pytest.approx(2.0)


def test_semicolon_ends_a_sentence():
    assert metrics.readability(_bible(["casa casa; casa casa."])).words_per_sentence == pytest.approx(2.0)


def test_numerals_and_loose_punctuation_are_not_words():
    assert metrics.readability(_bible(["casa 3 — casa"])).words_per_sentence == pytest.approx(2.0)


def test_readability_is_clamped_to_the_zero_hundred_range():
    assert 0 <= metrics.readability(_bible(["antidesestabelecimentalissimamente."])).score <= 100


# --- integridade ----------------------------------------------------------------

def _finding(verse: int, tier: Tier) -> Finding:
    return Finding("GEN", 1, verse, tier, "teste")


def test_integrity_is_completeness_times_sanity():
    bible = _bible(["a.", "b.", "c.", "d."])
    m = metrics.integrity(bible, [])
    assert m.chapters_present == 1
    assert m.chapters_expected == sum(versification.CHAPTERS.values())
    assert m.verses == 4
    assert m.score == round(100 * (1 / 1189) * 1.0)


def test_info_findings_weigh_nothing():
    bible = _bible(["a.", "b.", "c.", "d."])
    clean = metrics.integrity(bible, []).score
    with_info = metrics.integrity(bible, [_finding(1, Tier.INFO), _finding(2, Tier.INFO)])
    assert with_info.score == clean
    assert with_info.info == 2


def test_a_high_finding_weighs_three_times_a_low_one():
    bible = _bible(["a.", "b.", "c.", "d."])
    one_high = metrics.integrity(bible, [_finding(1, Tier.HIGH)])
    three_low = metrics.integrity(bible, [_finding(i, Tier.LOW) for i in (1, 2, 3)])
    assert one_high.sanity == pytest.approx(three_low.sanity)
    assert one_high.high == 1 and three_low.low == 3


def test_sanity_never_goes_below_zero():
    bible = _bible(["a."])
    assert metrics.integrity(bible, [_finding(1, Tier.HIGH)] * 10).sanity == 0.0


def test_a_high_finding_is_counted_once_per_reference():
    """O mesmo versículo sinalizado pelo validador e pela comparação entre versões
    é um defeito, não dois."""
    bible = _bible(["a.", "b."])
    twice = metrics.integrity(bible, [_finding(1, Tier.HIGH), _finding(1, Tier.HIGH)])
    assert twice.high == 1


def test_new_testament_scope_expects_only_the_new_testament_chapters():
    m = metrics.integrity(_bible(["a."], scope="nt"), [])
    assert m.chapters_expected == 260


def _bible_with_chapters(count: int, scope: str) -> Bible:
    return Bible(
        meta=BibleMeta(code="X", name="Teste", license="public-domain", scope=scope, source="t"),
        books=[Book(id=40, code="MAT", name="Mateus", abbrev="Mt", chapters=[
            Chapter(number=n, verses=[Verse(number=1, text="a.")]) for n in range(1, count + 1)
        ])],
    )


def test_completeness_never_passes_one():
    """Uma versão com mais capítulos que o cânon espera não tem integridade extra: a
    cobertura satura em 100%, e o excesso aparece em `chapters_present`, para ser visto."""
    m = metrics.integrity(_bible_with_chapters(300, "nt"), [])
    assert m.chapters_present == 300
    assert m.chapters_expected == 260
    assert m.completeness == 1.0
    assert m.score == 100


def test_a_missing_book_counts_as_all_of_its_chapters_missing():
    full = metrics.integrity(_bible(["a."]), [])
    assert full.chapters_present == 1
    assert full.chapters_expected == 1189


# --- metrics.json ---------------------------------------------------------------

def test_write_and_load_round_trip(tmp_path: Path):
    bible = _bible(["Casa casa casa casa."])
    path = tmp_path / "metrics.json"
    metrics.write_metrics({"X": metrics.compute(bible, [])}, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data["X"]) == {
        "integrity", "chapters_present", "chapters_expected", "verses", "high", "low", "info",
        "readability", "words_per_sentence", "syllables_per_word",
    }
    assert metrics.load_metrics(path)["X"]["integrity"] == data["X"]["integrity"]


def test_load_metrics_of_a_missing_file_is_empty(tmp_path: Path):
    assert metrics.load_metrics(tmp_path / "nope.json") == {}
