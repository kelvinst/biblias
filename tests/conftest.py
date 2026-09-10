import pytest

import cli


@pytest.fixture(autouse=True)
def _metrics_in_a_temp_file(tmp_path, monkeypatch):
    """Nenhum teste escreve no `data/stats/metrics.json` versionado.

    O `validate` grava as métricas junto das worklists, e um teste que só redireciona a
    pasta de worklist deixava códigos sintéticos ("A", "B") no arquivo real — foi assim
    que eles apareceram lá na primeira geração.
    """
    monkeypatch.setattr(cli, "METRICS_PATH", tmp_path / "metrics-isolado.json")
