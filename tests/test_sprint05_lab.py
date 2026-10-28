"""Sprint 05 synthetic operator workflow, using disposable workspaces."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from vyntrava_data_studio.synthetic_lab import run_pilot, verify_pilot


FIXTURES = Path(__file__).resolve().parents[1] / "examples"
KEY = b"runtime-synthetic-only-key"


@pytest.mark.parametrize("pilot,client", [("a", "piloto_a"), ("b", "piloto_b")])
def test_run_repeat_and_verify_oracles(tmp_path, pilot, client):
    root = tmp_path / "clientes"
    first = run_pilot(pilot, root, "first_job", "first", KEY, FIXTURES)
    repeat = run_pilot(pilot, root, "repeat_job", "repeat", KEY, FIXTURES)
    for item in (first, repeat):
        assert item["client"] == client
        assert item["status"] == "revision_requerida"
        assert item["verification"]["ok"] is True
        assert all(item["oracle_checks"].values())
        assert item["outcomes"]["initial_rows"] == 6
        assert item["outcomes"]["duplicates_initial"] == 1
        assert item["timing_seconds"]["execution"] >= 0
        assert item["timing_seconds"]["verification"] >= 0
        assert item["operator_durations_minutes"] == {"preparation": None, "human_review": None}
        assert verify_pilot(pilot, root, item["job"], FIXTURES)["ok"] is True
        assert KEY.decode() not in json.dumps(item)
        assert (root / "mediciones" / client / f'{item["job"]}.json').is_file()
        assert hashlib.sha256((root / client / item["job"] / "originales" /
                               ("clientes.csv" if pilot == "a" else "ventas.csv")).read_bytes()).hexdigest() == item["hashes"]["inputs"]["clientes" if pilot == "a" else "ventas"]
    assert first["hashes"]["inputs"] == repeat["hashes"]["inputs"]
    assert first["hashes"]["recipe"] == repeat["hashes"]["recipe"]
    assert first["hashes"]["outputs"] == repeat["hashes"]["outputs"]
    report = json.loads((root / client / "first_job" / "salidas" / "resumen.json").read_text(encoding="utf-8"))
    data = report["entradas"]["clientes" if pilot == "a" else "ventas"]
    assert data["antes"]["filas"] == 6
    assert data["antes"]["duplicados_exactos"] == 1
    assert data["despues"]["filas"] == 5
    if pilot == "a":
        assert data["antes"]["columnas"] == 4
        assert data["antes"]["celdas_vacias"] == 3
        assert data["antes"]["celdas_solo_espacios"] == 1
        assert data["despues"]["duplicados_exactos"] == 0
        assert report["validaciones"]["ausencias"]["incidencias"] == 3
        assert report["validaciones"]["email"]["incidencias"] == 1
    else:
        analysis = report["analisis"]["ventas_fecha"]
        assert report["validaciones"]["cantidad_valida"]["incidencias"] == 1
        assert analysis["filas_incluidas"] == 4
        assert analysis["filas_excluidas"] == 1
        assert analysis["unidades"] == 8
        assert analysis["total"] == "42.50"
        assert analysis["grupos"] == {"2026-01-05": "27.50", "2026-01-06": "10.00", "2026-01-07": "5.00"}


def test_wrong_workspace_and_missing_key_are_rejected(tmp_path):
    root = tmp_path / "clientes"
    run_pilot("a", root, "job_a", "first", KEY, FIXTURES)
    run_pilot("b", root, "job_b", "first", KEY, FIXTURES)
    assert not verify_pilot("a", root, "job_b", FIXTURES)["ok"]
    assert not verify_pilot("b", root, "job_a", FIXTURES)["ok"]
    from vyntrava_data_studio.package_verifier import verify_recipe_package
    assert not verify_recipe_package(FIXTURES / "piloto_a" / "receta_v1.json", root, "piloto_b", "job_b").ok
    assert not verify_recipe_package(FIXTURES / "piloto_b" / "receta_v1.json", root, "piloto_a", "job_a").ok
    with pytest.raises(ValueError, match="approval_key_required"):
        run_pilot("a", root, "no_key", "first", None, FIXTURES)
    with pytest.raises(ValueError, match="job_exists"):
        run_pilot("a", root, "job_a", "repeat", KEY, FIXTURES)
