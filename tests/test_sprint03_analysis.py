from vyntrava_data_studio.importer import CsvTable
from vyntrava_data_studio.sprint02 import _analysis


def test_analysis_excludes_only_affected_rows_and_keeps_decimal_precision():
    table = CsvTable(
        ("producto", "cantidad", "precio"),
        (("Libro", "2", "0.125"),
         ("Libro", "0", "4.00"),
         ("Lápiz", "3", "0.125")),
        False, ";", "utf-8",
    )
    validations = [{"id": "cantidad_valida", "op": "entero_positivo",
                    "entrada": "ventas", "params": {"columna": "cantidad"}}]
    sum_result = _analysis(table, {
        "op": "suma_producto", "entrada": "ventas",
        "params": {"cantidad": "cantidad", "precio": "precio", "grupo": "producto"},
    }, validations)
    count_result = _analysis(table, {
        "op": "conteo", "entrada": "ventas", "params": {"grupo": "producto"},
    }, validations)

    assert sum_result["filas_incluidas"] == 2
    assert sum_result["filas_excluidas"] == 1
    assert sum_result["exclusiones"] == {"cantidad_valida": 1, "numero_invalido": 1}
    assert sum_result["unidades"] == 5
    assert sum_result["total"] == "0.625"
    assert sum_result["grupos"] == {"Libro": "0.250", "Lápiz": "0.375"}
    assert count_result["total"] == 3
    assert count_result["grupos"] == {"Libro": 2, "Lápiz": 1}
