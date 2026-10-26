import json

import pytest

from vyntrava_data_studio.recipes import RecipeError, load_recipe


@pytest.fixture
def recipe():
    return {
        "id": "piloto_clientes", "version": "1.0.0",
        "tipo_encargo": "limpieza_clientes",
        "entradas": [{"id": "clientes", "ruta": "clientes.csv", "formato": "csv",
                      "codificacion": "utf-8", "delimitador": ","}],
        "esquema": {"clientes": {"columnas": ["id", "nombre", "email"], "extras": "rechazar"}},
        "parametros": {"campo": "nombre"},
        "reglas": [{"id": "r1", "op": "recortar_espacios", "entrada": "clientes",
                    "params": {"columnas": ["nombre"]}}],
        "validaciones": [{"id": "v1", "op": "columnas_requeridas", "entrada": "clientes",
                          "params": {"columnas": ["id", "email"]}, "severidad": "bloquear"}],
        "analisis": [],
        "salidas": [{"id": "diagnostico", "tipo": "resumen_json", "ruta": "diagnostico.json"}],
    }


def load(tmp_path, value):
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return load_recipe(path)


def rejects(tmp_path, recipe, code, location):
    with pytest.raises(RecipeError) as exc:
        load(tmp_path, recipe)
    assert (exc.value.code, exc.value.location) == (code, location)


def test_accepts_spec_shape(tmp_path, recipe):
    result = load(tmp_path, recipe)
    assert result.id == "piloto_clientes"
    assert result.version == "1.0.0"
    assert result.data["reglas"][0]["params"]["columnas"] == ["nombre"]


@pytest.mark.parametrize("change,code,location", [
    (lambda r: r.update(extra=True), "unknown_field", "$.extra"),
    (lambda r: r.pop("salidas"), "missing_field", "$.salidas"),
    (lambda r: r["reglas"][0]["params"].update(extra=1), "unknown_field", "$.reglas[0].params.extra"),
    (lambda r: r.update(version="2.0.0"), "unsupported_version", "$.version"),
    (lambda r: r.update(version="1.1.0"), "unsupported_version", "$.version"),
    (lambda r: r["reglas"][0].update(op="ejecutar_python"), "unknown_operation", "$.reglas[0].op"),
    (lambda r: r["reglas"][0].update(entrada="otro"), "unknown_reference", "$.reglas[0].entrada"),
    (lambda r: r["reglas"][0]["params"].update(columnas=["fantasma"]), "unknown_reference", "$.reglas[0].params.columnas[0]"),
])
def test_rejects_invalid_recipe(tmp_path, recipe, change, code, location):
    change(recipe)
    rejects(tmp_path, recipe, code, location)


def test_rejects_duplicate_json_key(tmp_path):
    path = tmp_path / "recipe.json"
    path.write_text('{"id":"uno","id":"dos"}', encoding="utf-8")
    with pytest.raises(RecipeError) as exc:
        load_recipe(path)
    assert (exc.value.code, exc.value.location) == ("duplicate_key", "$.id")


def test_rejects_non_json_number(tmp_path, recipe):
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(recipe).replace('"parametros": {"campo": "nombre"}',
                                                '"parametros": {"campo": NaN}'), encoding="utf-8")
    with pytest.raises(RecipeError) as exc:
        load_recipe(path)
    assert exc.value.code == "invalid_json"


def test_resolves_scalar_parameter_reference(tmp_path, recipe):
    recipe["validaciones"] = [{"id": "v1", "op": "email_simple", "entrada": "clientes",
                                "params": {"columna": {"parametro": "campo"}}, "severidad": "advertir"}]
    assert load(tmp_path, recipe).data["validaciones"][0]["params"] == {"columna": "nombre"}


def test_accepts_large_json_integer_parameter(tmp_path, recipe):
    recipe["parametros"]["conteo"] = 10 ** 400
    assert load(tmp_path, recipe).data["parametros"]["conteo"] == 10 ** 400


def test_rejects_oversized_version_without_leaking_value_error(tmp_path, recipe):
    recipe["version"] = "1." + "9" * 5000 + ".0"
    rejects(tmp_path, recipe, "unsupported_version", "$.version")


def test_accepts_informational_job_type_label(tmp_path, recipe):
    recipe["tipo_encargo"] = "Limpieza de clientes"
    assert load(tmp_path, recipe).data["tipo_encargo"] == "Limpieza de clientes"


def test_rejects_parameter_type_mismatch(tmp_path, recipe):
    recipe["parametros"]["campo"] = True
    recipe["validaciones"][0]["params"]["columnas"] = ["id"]
    recipe["reglas"] = [{"id": "r1", "op": "eliminar_duplicados_exactos", "entrada": "clientes",
                          "params": {"aprobacion": {"parametro": "campo"}}}]
    rejects(tmp_path, recipe, "invalid_type", "$.reglas[0].params.aprobacion")


@pytest.mark.parametrize("change,code,location", [
    (lambda r: r["reglas"][0].update(entrada=["clientes"]), "unknown_reference", "$.reglas[0].entrada"),
    (lambda r: r["salidas"].append({"id": "tabla", "tipo": "tabla_csv", "ruta": "tabla.csv", "fuente": []}),
     "unknown_reference", "$.salidas[1].fuente"),
    (lambda r: r["salidas"].append({"id": "grafico", "tipo": "grafico_png", "ruta": "grafico.png", "fuente": []}),
     "unknown_reference", "$.salidas[1].fuente"),
    (lambda r: r["entradas"][0].update(ruta="../clientes.csv"), "invalid_path", "$.entradas[0].ruta"),
    (lambda r: r["salidas"].append({"id": "otro", "tipo": "resumen_json", "ruta": "diagnostico.json"}),
     "duplicate_path", "$.salidas[1].ruta"),
    (lambda r: r["validaciones"][0].update(severidad="ignorar"), "invalid_value", "$.validaciones[0].severidad"),
])
def test_returns_recipe_error_for_invalid_fields(tmp_path, recipe, change, code, location):
    change(recipe)
    rejects(tmp_path, recipe, code, location)
