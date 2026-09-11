import pytest

import cli
import exporters.markdown as markdown


@pytest.fixture(autouse=True)
def _metrics_in_a_temp_file(tmp_path, monkeypatch):
    """Nenhum teste escreve no `data/stats/metrics.json` versionado.

    O `validate` grava as métricas junto das worklists, e um teste que só redireciona a
    pasta de worklist deixava códigos sintéticos ("A", "B") no arquivo real — foi assim
    que eles apareceram lá na primeira geração.
    """
    monkeypatch.setattr(cli, "METRICS_PATH", tmp_path / "metrics-isolado.json")


@pytest.fixture(autouse=True)
def _exporter_metrics_in_a_temp_file(tmp_path, monkeypatch):
    """Nenhum teste lê o `data/stats/metrics.json` versionado.

    O exportador passou a depender desse arquivo, e os testes que constroem
    `MarkdownExporter()` sem argumento renderizavam com os números reais das dezoito
    versões — uma nota de um `Bible` sem livro nenhum saía dizendo 1189 capítulos.
    """
    monkeypatch.setattr(markdown, "DEFAULT_METRICS_PATH", tmp_path / "metrics-isolado.json")
