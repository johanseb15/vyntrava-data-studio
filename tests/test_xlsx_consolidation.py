"""First synthetic two-workbook integration through the recipe publisher."""

import csv
import hashlib
import json

import pytest
from openpyxl import Workbook

from vyntrava_data_studio.delivery import DeliveryError
from vyntrava_data_studio.package_verifier import verify_recipe_package
from vyntrava_data_studio.recipes import RecipeError
from vyntrava_data_studio.sprint02 import run_recipe


def _book(path, headers, rows):
    book = Workbook()
    sheet = book.active
    sheet.title = "Datos"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    book.save(path)
    book.close()


def _setup(tmp_path, second_headers=("id", "producto", "cantidad")):
    root = tmp_path / "clientes"
    job = root / "cliente_demo" / "encargo_demo"
    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (job / folder).mkdir(parents=True)
    first = job / "originales" / "lote_a.xlsx"
    second = job / "originales" / "lote_b.xlsx"
    _book(first, ("id", "producto", "cantidad"),
          (("001", "Libro", 2), ("002", "Lápiz", 3)))
    _book(second, second_headers,
          (("003", "Libro", 1), ("004", "Cuaderno", 0)))
    recipe_data = {
        "id": "consolidacion_sintetica", "version": "1.1.0",
        "tipo_encargo": "consolidacion_xlsx",
        "entradas": [
            {"id": "lote_a", "ruta": first.name, "formato": "xlsx", "hoja": "Datos"},
            {"id": "lote_b", "ruta": second.name, "formato": "xlsx", "hoja": "Datos"},
        ],
        "esquema": {
            "lote_a": {"columnas": ["id", "producto", "cantidad"], "extras": "rechazar"},
            "lote_b": {"columnas": list(second_headers), "extras": "rechazar"},
        },
        "parametros": {},
        "reglas": [{"id": "unir", "op": "unir_filas", "entrada": "lote_a",
                    "params": {"otra_entrada": "lote_b"}}],
        "validaciones": [{"id": "cantidad", "op": "entero_positivo",
                          "entrada": "lote_a", "params": {"columna": "cantidad"},
                          "severidad": "advertir"}],
        "analisis": [],
        "salidas": [
            {"id": "resumen", "tipo": "resumen_json", "ruta": "resumen.json"},
            {"id": "tabla", "tipo": "tabla_csv", "ruta": "consolidado.csv",
             "fuente": "lote_a"},
        ],
    }
    recipe = tmp_path / "receta.json"
    recipe.write_text(json.dumps(recipe_data, ensure_ascii=False), encoding="utf-8")
    return root, job, recipe, first, second


def test_two_synthetic_xlsx_publish_csv_and_verifiable_provenance(tmp_path):
    root, job, recipe, first, second = _setup(tmp_path)
    originals = {path.name: path.read_bytes() for path in (first, second)}

    result = run_recipe(recipe, root, "cliente_demo", "encargo_demo")

    assert result.status == "revision_requerida"
    with result.outputs["tabla"].open(encoding="utf-8", newline="") as stream:
        assert list(csv.reader(stream)) == [
            ["id", "producto", "cantidad"],
            ["001", "Libro", "2"], ["002", "Lápiz", "3"],
            ["003", "Libro", "1"], ["004", "Cuaderno", "0"],
        ]
    report = json.loads(result.outputs["resumen"].read_text(encoding="utf-8"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert report["reglas"]["unir"] == {"op": "unir_filas", "cambios": 2}
    assert report["validaciones"]["cantidad"]["incidencias"] == 1
    for name, source in (("lote_a", first), ("lote_b", second)):
        digest = hashlib.sha256(originals[source.name]).hexdigest()
        assert report["procedencia"][name]["sha256"] == digest
        assert manifest["entradas"][name]["sha256"] == digest
        assert source.read_bytes() == originals[source.name]
    assert verify_recipe_package(recipe, root, "cliente_demo", "encargo_demo").ok


def test_mismatched_xlsx_headers_publish_nothing(tmp_path):
    root, job, recipe, _, _ = _setup(tmp_path, ("id", "producto", "unidades"))

    with pytest.raises(DeliveryError) as exc:
        run_recipe(recipe, root, "cliente_demo", "encargo_demo")

    assert exc.value.code == "schema_mismatch"
    assert list((job / "salidas").iterdir()) == []
    assert list((job / "evidencia").iterdir()) == []


@pytest.mark.parametrize("other,code", [("missing", "unknown_reference"),
                                         ("lote_a", "invalid_value")])
def test_invalid_join_source_is_rejected_before_publication(tmp_path, other, code):
    root, job, recipe, _, _ = _setup(tmp_path)
    data = json.loads(recipe.read_text(encoding="utf-8"))
    data["reglas"][0]["params"]["otra_entrada"] = other
    recipe.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(RecipeError) as exc:
        run_recipe(recipe, root, "cliente_demo", "encargo_demo")

    assert exc.value.code == code
    assert list((job / "salidas").iterdir()) == []
