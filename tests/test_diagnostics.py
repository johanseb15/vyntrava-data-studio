from vyntrava_data_studio.diagnostics import diagnose
from vyntrava_data_studio.importer import CsvTable, read_csv


def test_pilot_a_counts_and_preserves_source(tmp_path):
    source = tmp_path / "clients.csv"
    source.write_text(
        "id,nombre,email,ciudad\n"
        "C001,Ana Ruiz,ana@example.test,Buenos Aires\n"
        "C002,Luis Paz,,Córdoba\n"
        "C002,Luis Paz,,Córdoba\n"
        "C003,  Mara Sol  ,mara@example.test,   \n"
        "C004,Jo Vale,no-es-email,Rosario\n"
        "C005,,eve@example.test,Mendoza\n",
        encoding="utf-8",
    )
    table = read_csv(source, "utf-8", ",")
    original = table.rows

    first = diagnose(table)
    assert first.row_count == 6
    assert first.column_count == 4
    assert first.exact_duplicate_count == 1
    assert first.empty_cell_count == 3
    assert first.whitespace_only_cell_count == 1
    assert first.columns[1].empty_count == 1
    assert first.columns[2].empty_count == 2
    assert first.columns[3].whitespace_only_count == 1
    assert diagnose(table) == first
    assert table.rows == original
    assert "Mara Sol" not in repr(first)
    assert "ana@example.test" not in repr(first)


def test_inference_uses_all_present_values_and_keeps_whitespace_as_missing():
    table = CsvTable(
        headers=("integer", "decimal", "text", "empty", "spaces"),
        rows=(("1", "1", "a", "", "   "),
              ("-2", "2.50", "3", "", " ")),
        had_bom=False, delimiter=",", encoding="utf-8",
    )

    result = diagnose(table)
    assert tuple(column.inferred_type for column in result.columns) == (
        "entero", "decimal", "texto", "sin_datos", "sin_datos"
    )
    assert result.empty_cell_count == 2
    assert result.whitespace_only_cell_count == 2


def test_empty_table_has_no_rows_or_inferred_data():
    table = CsvTable(("a", "b"), (), False, ",", "utf-8")
    result = diagnose(table)
    assert (result.row_count, result.column_count, result.exact_duplicate_count) == (0, 2, 0)
    assert tuple(column.inferred_type for column in result.columns) == ("sin_datos", "sin_datos")


def test_exact_duplicates_compare_all_raw_cells():
    table = CsvTable(("a", "b"), (("x", ""), ("x", ""), ("x", " "), ("x", "")), False, ",", "utf-8")
    result = diagnose(table)
    assert result.exact_duplicate_count == 2
    assert result.empty_cell_count == 3
    assert result.whitespace_only_cell_count == 1
