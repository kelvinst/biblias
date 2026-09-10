from dataclasses import fields

import pytest

from catalog import CATALOG, Assessment, CatalogEntry, get


def test_has_eighteen_versions():
    assert len(CATALOG) == 18
    assert "KJA" in CATALOG
    assert "BLIVRE" in CATALOG


def test_biblia_livre_is_public_domain_full():
    entry = get("BLIVRE")
    assert entry.license == "public-domain"
    assert entry.scope == "full"


def test_get_returns_entry():
    entry = get("KJA")
    assert entry.name == "King James Atualizada"
    assert entry.scope == "full"


def test_tb_is_public_domain():
    assert get("TB").license == "public-domain"


def test_unknown_code_raises():
    with pytest.raises(KeyError):
        get("ZZZ")


# --- classificação editorial ---------------------------------------------------

def _assessments():
    for entry in CATALOG.values():
        yield entry.code, "trust", entry.trust
        yield entry.code, "respect", entry.respect


def test_every_assessment_has_exactly_four_factors():
    for code, kind, assessment in _assessments():
        assert len(assessment.scores) == 4, f"{code}.{kind}"


def test_every_factor_is_within_zero_and_twenty_five():
    for code, kind, assessment in _assessments():
        for i, score in enumerate(assessment.scores):
            assert 0 <= score <= 25, f"{code}.{kind}[{i}] = {score}"


def test_every_assessment_has_a_note():
    for code, kind, assessment in _assessments():
        assert assessment.note.strip(), f"{code}.{kind} sem nota"


def test_total_is_the_sum_of_the_factors():
    for code, kind, assessment in _assessments():
        assert assessment.total == sum(assessment.scores), f"{code}.{kind}"


def test_assessment_rejects_the_wrong_number_of_factors():
    with pytest.raises(ValueError):
        Assessment(scores=(25, 25, 25), note="três fatores")


def test_assessment_rejects_a_factor_out_of_range():
    with pytest.raises(ValueError):
        Assessment(scores=(26, 0, 0, 0), note="acima do teto")


def test_assessment_rejects_an_empty_note():
    """Nota vazia é número sem justificativa — o modo de falha que este desenho impede."""
    with pytest.raises(ValueError):
        Assessment(scores=(25, 25, 25, 25), note="   ")


# --- method, derivado de formality ---------------------------------------------

def _method_for(formality: int) -> str:
    return CatalogEntry("X", "x", None, None, "copyright", "full", None, formality,
                        Assessment((1, 1, 1, 1), "n"), Assessment((1, 1, 1, 1), "n")).method


def test_method_boundaries():
    assert _method_for(100) == "formal"
    assert _method_for(75) == "formal"
    assert _method_for(74) == "balanced"
    assert _method_for(55) == "balanced"
    assert _method_for(54) == "functional"
    assert _method_for(35) == "functional"
    assert _method_for(34) == "paraphrase"
    assert _method_for(0) == "paraphrase"


def test_method_is_not_stored():
    """Um número e um rótulo guardados lado a lado divergem no primeiro ajuste."""
    assert "method" not in {f.name for f in fields(CatalogEntry)}


def test_paraphrases_are_exactly_ol_and_mens():
    assert {c for c, e in CATALOG.items() if e.method == "paraphrase"} == {"OL", "MENS"}


def test_text_base_uses_the_closed_vocabulary():
    allowed = {"textus-receptus", "critical", "eclectic", None}
    for entry in CATALOG.values():
        assert entry.text_base in allowed, f"{entry.code}: {entry.text_base}"


def test_formality_is_always_a_percentage():
    for entry in CATALOG.values():
        assert 0 <= entry.formality <= 100, entry.code
