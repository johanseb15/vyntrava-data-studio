import hashlib
import hmac
import json

from vyntrava_data_studio.sprint02 import run_recipe


PILOT_B = (
    "\ufeffid;fecha;producto;cantidad;precio\n"
    "V001;2026-01-05;Libro;2;10.00\n"
    "V002;2026-01-05;L\u00e1piz;3;2.50\n"
    "V003;2026-01-06;Libro;1;10.00\n"
    "V003;2026-01-06;Libro;1;10.00\n"
    "V004;2026-01-06;Libro;0;10.00\n"
    "V005;2026-01-07;L\u00e1piz;2;2.50\n"
).encode("utf-8")


def test_pilot_b_sales_analysis_red(tmp_path):
    root = tmp_path / "clientes"
    job = root / "cliente_b" / "encargo_b"

    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (job / folder).mkdir(parents=True)

    source = job / "originales" / "ventas.csv"
    source.write_bytes(PILOT_B)

    data = {
        "id": "piloto_ventas",
        "version": "1.0.0",
        "tipo_encargo": "analisis_ventas",
        "entradas": [{
            "id": "ventas",
            "ruta": "ventas.csv",
            "formato": "csv",
            "codificacion": "utf-8-sig",
            "delimitador": ";",
        }],
        "esquema": {
            "ventas": {
                "columnas": [
                    "id", "fecha", "producto",
                    "cantidad", "precio"
                ],
                "extras": "rechazar",
            }
        },
        "parametros": {},
        "reglas": [{
            "id": "deduplicar",
            "op": "eliminar_duplicados_exactos",
            "entrada": "ventas",
            "params": {"aprobacion": "aprobacion_b"},
        }],
        "validaciones": [{
            "id": "cantidad_valida",
            "op": "entero_positivo",
            "entrada": "ventas",
            "params": {"columna": "cantidad"},
            "severidad": "advertir",
        }],
        "analisis": [{
            "id": "ventas_fecha",
            "op": "suma_producto",
            "entrada": "ventas",
            "params": {
                "cantidad": "cantidad",
                "precio": "precio",
                "grupo": "fecha",
            },
        }],
        "salidas": [{
            "id": "resumen",
            "tipo": "resumen_json",
            "ruta": "resumen.json",
        }],
    }

    recipe = tmp_path / "receta.json"
    recipe.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )

    key = b"clave-solo-pruebas-sinteticas"

    approval = {
        "id": "aprobacion_b",
        "responsable": "revisor_sintetico",
        "receta_sha256": hashlib.sha256(
            recipe.read_bytes()
        ).hexdigest(),
        "entradas_sha256": {
            "ventas": hashlib.sha256(
                source.read_bytes()
            ).hexdigest()
        },
    }

    payload = json.dumps(
        approval,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    approval["firma"] = hmac.new(
        key, payload, hashlib.sha256
    ).hexdigest()

    result = run_recipe(
        recipe,
        root,
        "cliente_b",
        "encargo_b",
        approvals={"aprobacion_b": approval},
        approval_key=key,
    )

    assert result.status == "revision_requerida"

    report = json.loads(
        result.outputs["resumen"].read_bytes()
    )

    # Contrato propuesto para el resultado de Sprint 03.
    analysis = report["analisis"]["ventas_fecha"]

    assert analysis["filas_incluidas"] == 4
    assert analysis["filas_excluidas"] == 1
    assert analysis["unidades"] == 8
    assert analysis["total"] == "42.50"

    assert analysis["grupos"] == {
        "2026-01-05": "27.50",
        "2026-01-06": "10.00",
        "2026-01-07": "5.00",
    }

    assert source.read_bytes() == PILOT_B