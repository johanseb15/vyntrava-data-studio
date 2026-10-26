"""Strict, text-preserving CSV import for synthetic and local inputs."""

from dataclasses import dataclass
from pathlib import Path
import stat


MAX_CSV_BYTES = 10_485_760
_BOM = b"\xef\xbb\xbf"

_MESSAGES = {
    "invalid_file": "CSV file is missing or is not a regular .csv file",
    "too_large": "CSV file exceeds 10 MiB",
    "empty_file": "CSV file is empty",
    "invalid_encoding": "CSV contains invalid or unsupported text",
    "encoding_mismatch": "CSV BOM does not match declared encoding",
    "invalid_encoding_name": "CSV encoding must be utf-8 or utf-8-sig",
    "invalid_delimiter": "CSV delimiter must be comma or semicolon",
    "delimiter_mismatch": "CSV appears to use a different delimiter",
    "missing_header": "CSV header is missing",
    "invalid_header": "CSV header contains an empty or repeated column",
    "unequal_width": "CSV record has a different number of fields",
    "blank_record": "CSV contains an empty record",
    "invalid_quotes": "CSV quotes are malformed",
    "invalid_line_ending": "CSV contains an isolated carriage return",
}


class CsvError(Exception):
    def __init__(self, code: str, record_number: int | None = None):
        self.code = code
        self.record_number = record_number
        message = _MESSAGES[code]
        if record_number is not None:
            message += f" (record {record_number})"
        super().__init__(message)


@dataclass(frozen=True)
class CsvTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    had_bom: bool
    delimiter: str
    encoding: str


def _read_text(path: Path, encoding: str) -> tuple[str, bool]:
    try:
        info = path.lstat()
        if path.suffix.lower() != ".csv" or not stat.S_ISREG(info.st_mode):
            raise CsvError("invalid_file")
        with path.open("rb") as source:
            data = source.read(MAX_CSV_BYTES + 1)
    except (OSError, ValueError, TypeError):
        raise CsvError("invalid_file") from None

    if len(data) > MAX_CSV_BYTES:
        raise CsvError("too_large")
    if not data:
        raise CsvError("empty_file")

    has_bom = data.startswith(_BOM)
    if has_bom != (encoding == "utf-8-sig"):
        raise CsvError("encoding_mismatch")
    if has_bom:
        data = data[len(_BOM):]
    if not data:
        raise CsvError("missing_header", 1)
    try:
        result = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise CsvError("invalid_encoding") from None
    if "\x00" in result or "\ufeff" in result:
        raise CsvError("invalid_encoding")
    return result, has_bom


def _parse_records(text: str, delimiter: str) -> tuple[tuple[str, ...], ...]:
    records: list[tuple[str, ...]] = []
    fields: list[str] = []
    value: list[str] = []
    state = "start"
    position = 0
    ended_with_newline = False

    def finish_record() -> None:
        nonlocal state
        number = len(records) + 1
        if not fields and not value and state == "start":
            raise CsvError("missing_header" if number == 1 else "blank_record", number)
        fields.append("".join(value))
        records.append(tuple(fields))
        fields.clear()
        value.clear()
        state = "start"

    while position < len(text):
        char = text[position]
        ended_with_newline = False
        number = len(records) + 1
        if state == "quoted":
            if char == '"':
                if position + 1 < len(text) and text[position + 1] == '"':
                    value.append('"')
                    position += 2
                    continue
                state = "closed"
            else:
                value.append(char)
        elif char == delimiter:
            fields.append("".join(value))
            value.clear()
            state = "start"
        elif char == "\n" or char == "\r":
            if char == "\r":
                if position + 1 >= len(text) or text[position + 1] != "\n":
                    raise CsvError("invalid_line_ending", number)
                position += 1
            finish_record()
            ended_with_newline = True
        elif char == '"':
            if state == "start":
                state = "quoted"
            else:
                raise CsvError("invalid_quotes", number)
        else:
            if state == "closed":
                raise CsvError("invalid_quotes", number)
            value.append(char)
            state = "plain"
        position += 1

    if state == "quoted":
        raise CsvError("invalid_quotes", len(records) + 1)
    if not ended_with_newline:
        finish_record()
    return tuple(records)


def read_csv(path: Path, encoding: str, delimiter: str) -> CsvTable:
    """Read a strict CSV without changing any cell or column text."""
    if encoding not in ("utf-8", "utf-8-sig"):
        raise CsvError("invalid_encoding_name")
    if delimiter not in (",", ";"):
        raise CsvError("invalid_delimiter")
    try:
        source = Path(path)
    except (TypeError, ValueError):
        raise CsvError("invalid_file") from None
    text, has_bom = _read_text(source, encoding)
    records = _parse_records(text, delimiter)
    headers = records[0]
    if len(headers) == 1:
        other = ";" if delimiter == "," else ","
        try:
            alternative = _parse_records(text, other)
        except CsvError:
            alternative = ()
        if alternative and len(alternative[0]) > 1 and all(len(row) == len(alternative[0]) for row in alternative):
            raise CsvError("delimiter_mismatch", 1)
    if any(not header for header in headers) or len(set(headers)) != len(headers):
        raise CsvError("invalid_header", 1)
    for number, row in enumerate(records[1:], 2):
        if len(row) != len(headers):
            raise CsvError("unequal_width", number)
    return CsvTable(headers, records[1:], has_bom, delimiter, encoding)
