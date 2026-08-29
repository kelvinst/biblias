from pathlib import Path

import typer

import canon
import corrections
import validate as validate_mod
import worklist
from validate import Report
from exporters.registry import EXTENSIONS, make_exporter, output_path
from sources.registry import make_source

app = typer.Typer(help="Ferramenta para gerar Bíblias em português a partir de uma fonte canônica.")

SQL_DIR = Path("inst/sql")
CANON_DIR = Path("data/canonical")
CORRECTIONS_DIR = Path("data/corrections")
WORKLIST_DIR = Path("data/worklist")


def canonical_codes() -> list[str]:
    """Versões presentes no canônico, em ordem alfabética."""
    if not CANON_DIR.exists():
        return []
    return sorted(p.name for p in CANON_DIR.iterdir() if (p / "meta.json").exists())


def resolve_codes(code: str | None) -> list[str]:
    """Resolve o argumento de versão: vazio ou `all` = todas; senão, lista por vírgula."""
    if code is None or code.strip().lower() == "all":
        codes = canonical_codes()
        if not codes:
            raise typer.BadParameter(f"Nenhuma versão no canônico ({CANON_DIR}).")
        return codes
    codes = [c.strip() for c in code.split(",") if c.strip()]
    if not codes:
        raise typer.BadParameter("Nenhuma versão informada.")
    available = canonical_codes()
    unknown = [c for c in codes if c not in available]
    if unknown:
        raise typer.BadParameter(f"Sem canônico para: {', '.join(unknown)}.")
    return codes


@app.command()
def fetch(code: str, source: str = "openlp", force: bool = False) -> None:
    """Busca uma versão de uma fonte e grava no canônico."""
    if not force and corrections.corrected_refs(code, CORRECTIONS_DIR):
        raise typer.BadParameter(
            f"{code} tem correções manuais registradas; use --force para sobrescrever."
        )
    adapter = make_source(source, SQL_DIR)
    bible = adapter.fetch(code)
    canon.save_bible(bible, CANON_DIR)
    chapters = sum(len(b.chapters) for b in bible.books)
    typer.echo(f"{code}: {chapters} capítulos gravados no canônico.")


@app.command()
def build(
    code: str | None = typer.Argument(None, help="Versão, lista separada por vírgula, ou `all`."),
    format: str = "zefania",
    out: Path = Path("dist"),
) -> None:
    """Gera um ou mais formatos de saída a partir do canônico.

    Sem argumento (ou com `all`), gera todas as versões do canônico.
    """
    formats = [f.strip() for f in format.split(",") if f.strip()]
    for fmt in formats:
        if fmt not in EXTENSIONS:
            raise typer.BadParameter(f"Formato desconhecido: {fmt}")
    for version in resolve_codes(code):
        bible = canon.load_bible(version, CANON_DIR)
        for fmt in formats:
            make_exporter(fmt).export(bible, output_path(fmt, out, version))
        typer.echo(f"{version}: {', '.join(formats)} gerado(s) em {out}.")


@app.command(name="diff-sources")
def diff_sources(code: str, sources: str = "bolls,getbible") -> None:
    """Compara uma versão entre fontes, validando cada uma."""
    for name in [s.strip() for s in sources.split(",") if s.strip()]:
        try:
            bible = make_source(name, SQL_DIR).fetch(code)
        except Exception as exc:  # noqa: BLE001 - report any source failure as a row
            typer.echo(f"{name}: indisponível ({type(exc).__name__})")
            continue
        counts = validate_mod.validate_bible(bible).counts
        typer.echo(f"{name}: {counts[validate_mod.Tier.HIGH]} alta, "
                   f"{counts[validate_mod.Tier.LOW]} baixa, {counts[validate_mod.Tier.INFO]} info")


@app.command()
def validate(
    code: str | None = typer.Argument(None, help="Versão, lista separada por vírgula, ou `all`."),
) -> None:
    """Valida o canônico e grava worklists por versão.

    Sem argumento (ou com `all`), valida todas as versões do canônico.
    """
    bibles = [canon.load_bible(c, CANON_DIR) for c in resolve_codes(code)]
    cross = validate_mod.cross_version_findings(bibles)
    for bible in bibles:
        single = validate_mod.validate_bible(bible)
        merged = Report(code=bible.meta.code,
                        findings=single.findings + cross.get(bible.meta.code, []))
        worklist.write_worklist(merged, WORKLIST_DIR)
        c = merged.counts
        typer.echo(f"{bible.meta.code}: {c[validate_mod.Tier.HIGH]} alta, "
                   f"{c[validate_mod.Tier.LOW]} baixa, {c[validate_mod.Tier.INFO]} info")
