import hashlib
import io
import json

from PIL import Image

from vyntrava_data_studio import charts
from vyntrava_data_studio.charts import grouped_amounts_png
from vyntrava_data_studio.sprint02 import run_recipe


def test_chart_png_from_grouped_sales(tmp_path):
    root = tmp_path / "clients"
    job = root / "synthetic" / "sales"

    for folder in ("originales", "trabajo", "salidas", "evidencia"):
        (job / folder).mkdir(parents=True)

    original = (
        "fecha;cantidad;precio\n"
        "2026-01-05;2;10.00\n"
        "2026-01-05;3;2.50\n"
        "2026-01-06;1;10.00\n"
        "2026-01-07;2;2.50\n"
    ).encode("utf-8")

    source = job / "originales" / "ventas.csv"
    source.write_bytes(original)

    recipe_data = {
        "id": "ventas_grafico",
        "version": "1.0.0",
        "tipo_encargo": "analisis_ventas",
        "entradas": [{
            "id": "ventas",
            "ruta": "ventas.csv",
            "formato": "csv",
            "codificacion": "utf-8",
            "delimitador": ";"
        }],
        "esquema": {
            "ventas": {
                "columnas": ["fecha", "cantidad", "precio"],
                "extras": "rechazar"
            }
        },
        "parametros": {},
        "reglas": [],
        "validaciones": [],
        "analisis": [{
            "id": "por_fecha",
            "op": "suma_producto",
            "entrada": "ventas",
            "params": {
                "cantidad": "cantidad",
                "precio": "precio",
                "grupo": "fecha"
            }
        }],
        "salidas": [
            {
                "id": "resumen",
                "tipo": "resumen_json",
                "ruta": "resumen.json"
            },
            {
                "id": "grafico",
                "tipo": "grafico_png",
                "ruta": "ventas.png",
                "fuente": "por_fecha"
            }
        ]
    }

    recipe = tmp_path / "recipe.json"
    recipe.write_text(
        json.dumps(recipe_data, ensure_ascii=False),
        encoding="utf-8"
    )

    result = run_recipe(recipe, root, "synthetic", "sales")

    assert result.status == "validado"
    assert set(result.outputs) == {"resumen", "grafico"}

    summary = json.loads(result.outputs["resumen"].read_bytes())
    assert summary["analisis"]["por_fecha"]["total"] == "42.50"
    assert summary["analisis"]["por_fecha"]["grupos"] == {
        "2026-01-05": "27.50",
        "2026-01-06": "10.00",
        "2026-01-07": "5.00"
    }

    image = result.outputs["grafico"].read_bytes()
    assert image.startswith(b"\x89PNG\r\n\x1a\n")

    manifest = json.loads(result.manifest_path.read_bytes())
    assert manifest["salidas"]["grafico"]["sha256"] == (
        hashlib.sha256(image).hexdigest()
    )

    assert source.read_bytes() == original


def test_chart_has_fixed_dimensions_bars_and_stable_bytes():
    groups = {"2026-01-05": "27.50", "2026-01-06": "10.00",
              "2026-01-07": "5.00"}
    first = grouped_amounts_png(groups)
    assert first == grouped_amounts_png(groups)
    with Image.open(io.BytesIO(first)) as image:
        assert image.size == (900, 500)
        assert image.mode == "RGB"
        assert image.info == {}
        green = (35, 122, 87)
        assert sum(count for count, color in image.getcolors(900 * 500)
                   if color == green) > 1000


def test_chart_text_boxes_fit_canvas_without_overlap(monkeypatch):
    real_draw = charts.ImageDraw.Draw
    text_boxes = []

    class RecordingDraw:
        def __init__(self, image):
            self.draw = real_draw(image)

        def __getattr__(self, name):
            return getattr(self.draw, name)

        def text(self, xy, text, **kwargs):
            text_boxes.append((text, self.draw.textbbox(
                xy, text, font=kwargs["font"], anchor=kwargs.get("anchor"))))
            return self.draw.text(xy, text, **kwargs)

    monkeypatch.setattr(charts.ImageDraw, "Draw", RecordingDraw)
    charts.grouped_amounts_png({
        "2026-01-05": "1234567.89",
        "2026-01-06": "100000.00",
        "2026-01-07": "5.00",
    })

    assert {"Ventas por fecha", "Importe", "2026-01-05", "2026-01-06",
            "2026-01-07", "1234567.89", "100000.00", "5.00"} <= {
                text for text, _ in text_boxes}
    for text, box in text_boxes:
        assert 0 <= box[0] < box[2] <= 900, (text, box)
        assert 0 <= box[1] < box[3] <= 500, (text, box)
    for index, (text, a) in enumerate(text_boxes):
        for other, b in text_boxes[index + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (
                text, other, a, b)
