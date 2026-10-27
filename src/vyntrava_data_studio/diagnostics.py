"""Deterministic, non-mutating quality summary for imported CSV text."""

from dataclasses import dataclass
import re

from .importer import CsvTable


_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+\.[0-9]+|\.[0-9]+)\Z")


@dataclass(frozen=True)
class ColumnDiagnostic:
    name: str
    empty_count: int
    whitespace_only_count: int
    inferred_type: str


@dataclass(frozen=True)
class DiagnosticSummary:
    row_count: int
    column_count: int
    exact_duplicate_count: int
    empty_cell_count: int
    whitespace_only_cell_count: int
    columns: tuple[ColumnDiagnostic, ...]


def _inferred_type(values: tuple[str, ...]) -> str:
    present = tuple(value for value in values if value and not _only_spaces(value))
    if not present:
        return "sin_datos"
    if all(_INTEGER.fullmatch(value) for value in present):
        return "entero"
    if all(_INTEGER.fullmatch(value) or _DECIMAL.fullmatch(value) for value in present):
        return "decimal"
    return "texto"


def _only_spaces(value: str) -> bool:
    return bool(value) and all(char == " " for char in value)


def diagnose(table: CsvTable) -> DiagnosticSummary:
    """Count quality indicators without modifying or exposing cell values."""
    seen: set[tuple[str, ...]] = set()
    duplicate_count = 0
    for row in table.rows:
        if row in seen:
            duplicate_count += 1
        else:
            seen.add(row)

    columns = tuple(
        ColumnDiagnostic(
            name=header,
            empty_count=sum(value == "" for value in values),
            whitespace_only_count=sum(_only_spaces(value) for value in values),
            inferred_type=_inferred_type(values),
        )
        for header, values in (
            (header, tuple(row[index] for row in table.rows))
            for index, header in enumerate(table.headers)
        )
    )
    return DiagnosticSummary(
        row_count=len(table.rows),
        column_count=len(table.headers),
        exact_duplicate_count=duplicate_count,
        empty_cell_count=sum(column.empty_count for column in columns),
        whitespace_only_cell_count=sum(column.whitespace_only_count for column in columns),
        columns=columns,
    )
