"""Métricas calculadas a partir do texto canônico.

Estes números não são opinião e não se escrevem à mão: um campo calculado escrito à
mão apodrece em silêncio na primeira correção de versículo. São regerados por
``uv run biblias validate`` e gravados em ``data/stats/metrics.json``, junto das
parcelas que os produziram — um número sem as parcelas não é auditável, e
auditabilidade é a razão de eles existirem em vez de mais uma avaliação editorial.
"""

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import books
import versification
from model import Bible
from validate import Finding, Tier

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)   # letras, acentos incluídos; sem numerais
_SENTENCE_END = re.compile(r"[.!?…;]+")
_VOWELS = "aeiouáéíóúâêôàãõäëïöüy"
# Ditongos decrescentes, com os nasais. A primeira vogal do par é normalizada antes da
# consulta, de modo que `céu` case como `eu`; a segunda não, porque é o acento nela que
# desfaz o ditongo (`saúde` é sa-ú-de, `país` é pa-ís).
_FALLING = frozenset({"ai", "ei", "oi", "ui", "au", "eu", "ou", "iu", "ão", "ãe", "õe"})
# Ditongos crescentes: só contam como uma sílaba em posição final (`his-tó-ria`).
_RISING_FINAL = frozenset({"ia", "ie", "io", "ua", "ue", "uo"})
# O u de `qu`/`gu` não forma sílaba própria. A regra da fórmula fala de `e` e `i`
# (`aqui`, `guerra`); estendida às demais vogais porque ali o u também é glide e não
# núcleo (`quando` é quan-do, `água` é á-gua).
_MUTE_U = re.compile(f"(?<=[qg])u(?=[{_VOWELS}])", re.IGNORECASE)


def _strip_accent(char: str) -> str:
    """Tira o acento agudo/grave/circunflexo, preservando o til: o til é nasalidade,
    e é ele que forma `ão`, `ãe` e `õe`."""
    if char in "ãõ":
        return char
    return unicodedata.normalize("NFD", char)[0]


def count_syllables(word: str) -> int:
    """Grupos vocálicos contíguos, resolvendo ditongos e hiatos do português.

    Não há hifenizador no projeto e não vale a pena acrescentar dependência para isto;
    a contagem aproxima a separação silábica pelas regras acima, que é a parte da
    fórmula de legibilidade que erra fácil e em silêncio.
    """
    low = _MUTE_U.sub("", word.lower())
    total = 0
    for match in re.finditer(f"[{_VOWELS}]+", low):
        group = match.group()
        # "Posição final" tolera o s do plural e nada mais: sem ele `his-tó-rias` sairia
        # com uma sílaba a mais que `his-tó-ria`; com qualquer consoante o par voltaria a
        # ser ditongo em `cri-am` e `es-ta-ri-am`, que são hiato. `di-an-te` traz o mesmo
        # par com vogal adiante, e também é hiato.
        word_final = low[match.end():] in ("", "s")
        i = 0
        while i < len(group):
            pair = _strip_accent(group[i]) + group[i + 1] if i + 1 < len(group) else ""
            if pair in _FALLING or (pair in _RISING_FINAL and word_final and i + 2 == len(group)):
                i += 2
            else:
                i += 1
            total += 1
    # Uma palavra sem grupo vocálico reconhecível ainda é uma sílaba falada.
    return max(1, total)


@dataclass(frozen=True)
class Readability:
    """Índice de Legibilidade de Flesch adaptado ao português (Martins et al., 1996)."""

    score: int
    words_per_sentence: float
    syllables_per_word: float


@dataclass(frozen=True)
class Integrity:
    """Quanto do texto canônico está íntegro e completo, medido pelo próprio validador."""

    score: int
    chapters_present: int
    chapters_expected: int
    verses: int
    high: int
    low: int
    info: int
    completeness: float
    sanity: float


def _texts(bible: Bible):
    for book in bible.books:
        for chapter in book.chapters:
            for verse in chapter.verses:
                yield verse.text


def readability(bible: Bible) -> Readability:
    words = sentences = syllables = 0
    for text in _texts(bible):
        found = _WORD.findall(text)
        if not found:
            continue
        words += len(found)
        syllables += sum(count_syllables(w) for w in found)
        # Um versículo sem pontuação terminal é uma frase, não zero.
        sentences += max(1, sum(1 for part in _SENTENCE_END.split(text) if _WORD.search(part)))
    if not words or not sentences:
        return Readability(score=0, words_per_sentence=0.0, syllables_per_word=0.0)
    wps = words / sentences
    spw = syllables / words
    ilf = 248.835 - 1.015 * wps - 84.6 * spw
    return Readability(score=max(0, min(100, round(ilf))),
                       words_per_sentence=wps, syllables_per_word=spw)


def _expected_chapters(scope: str) -> int:
    if scope == "nt":
        return sum(versification.chapters_for(b.code) for b in books.BOOKS if b.id >= 40)
    return sum(versification.CHAPTERS.values())


def integrity(bible: Bible, findings: list[Finding]) -> Integrity:
    """Completude estrutural vezes sanidade do texto.

    `Tier.INFO` pesa zero por definição: split de versificação e omissão intencional são
    características da versão, não defeito dela. `HIGH` pesa o triplo de `LOW` porque
    corrupção e truncamento perdem texto, enquanto pontuação terminal faltando é
    cosmético.

    `high`, `low` e `info` contam versículos distintos, não achados, e em cascata: um
    versículo aparece no pior tier em que foi sinalizado e em nenhum outro. Sem isso todo
    truncamento pesaria 4 em vez de 3, porque a comparação entre versões só devolve HIGH
    para versículo sem pontuação terminal, que o validador já marcou como LOW. É também
    por isso que estes números podem ficar abaixo dos da worklist, que lista achados.
    """
    chapters_present = sum(len(b.chapters) for b in bible.books)
    chapters_expected = _expected_chapters(bible.meta.scope)
    verses = sum(1 for _ in _texts(bible))

    def refs(tier: Tier) -> set[tuple[str, int, int]]:
        return {(f.book_code, f.chapter, f.verse) for f in findings if f.tier is tier}

    high_refs = refs(Tier.HIGH)
    low_refs = refs(Tier.LOW) - high_refs
    info_refs = refs(Tier.INFO) - high_refs - low_refs
    high, low, info = len(high_refs), len(low_refs), len(info_refs)
    # Satura em 1: cobertura acima do cânon não é integridade extra, e deixaria um
    # defeito de sanidade escondido atrás do excesso. O excesso continua visível em
    # `chapters_present`.
    completeness = min(1.0, chapters_present / chapters_expected) if chapters_expected else 0.0
    sanity = max(0.0, 1 - (3 * high + low) / verses) if verses else 0.0
    return Integrity(score=round(100 * completeness * sanity),
                     chapters_present=chapters_present, chapters_expected=chapters_expected,
                     verses=verses, high=high, low=low, info=info,
                     completeness=completeness, sanity=sanity)


@dataclass(frozen=True)
class VersionMetrics:
    integrity: Integrity
    readability: Readability

    def as_json(self) -> dict[str, int | float]:
        """As parcelas junto do total: um número sozinho não é auditável."""
        i, r = asdict(self.integrity), asdict(self.readability)
        return {
            "integrity": i["score"],
            "chapters_present": i["chapters_present"],
            "chapters_expected": i["chapters_expected"],
            "verses": i["verses"],
            "high": i["high"], "low": i["low"], "info": i["info"],
            "readability": r["score"],
            "words_per_sentence": round(r["words_per_sentence"], 2),
            "syllables_per_word": round(r["syllables_per_word"], 3),
        }


def compute(bible: Bible, findings: list[Finding]) -> VersionMetrics:
    return VersionMetrics(integrity=integrity(bible, findings), readability=readability(bible))


def write_metrics(
    computed: dict[str, VersionMetrics],
    path: Path,
    known: set[str] | None = None,
) -> Path:
    """Grava o arquivo inteiro, ordenado por código, mesclando com o que já está lá:
    validar uma versão só não pode apagar as métricas das outras.

    `known` são os códigos que ainda existem; o que estiver fora deles sai do arquivo.
    Sem essa poda, uma versão renomeada ou removida do canônico deixa a linha antiga no
    arquivo versionado para sempre, e nada avisa.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = load_metrics(path) | {code: m.as_json() for code, m in computed.items()}
    payload = {code: merged[code] for code in sorted(merged)
               if known is None or code in known}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_metrics(path: Path) -> dict[str, dict]:
    """Ausente ou ilegível, devolve vazio: a nota sai sem a seção de medidas em vez de
    quebrar a build."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    # Um JSON válido que não seja objeto — ou uma linha que não seja objeto — estouraria
    # só lá adiante, no exportador, com a pasta de destino já apagada.
    if not isinstance(data, dict):
        return {}
    return {code: row for code, row in data.items() if isinstance(row, dict)}
