from pathlib import Path

import pytest

from vyntrava_data_studio.importer import CsvError, read_csv


def load(tmp_path: Path, content: bytes, encoding: str = "utf-8", delimiter: str = ","):
    source = tmp_path / "sample.csv"
    source.write_bytes(content)
    return read_csv(source, encoding, delimiter)


def rejected(tmp_path: Path, content: bytes, code: str, encoding: str = "utf-8", delimiter: str = ","):
    with pytest.raises(CsvError) as raised:
        load(tmp_path, content, encoding, delimiter)
    assert raised.value.code == code
    assert isinstance(raised.value.record_number, int) or raised.value.record_number is None
    assert b"sensitive-cell-value" not in str(raised.value).encode()


@pytest.mark.parametrize("delimiter,content", [
    (",", b"first,second\na,b\nc,d\n"),
    (";", b"first;second\na;b\nc;d\n"),
])
def test_preserves_headers_rows_and_order(tmp_path, delimiter, content):
    table = load(tmp_path, content, delimiter=delimiter)
    assert table.headers == ("first", "second")
    assert table.rows == (("a", "b"), ("c", "d"))
    assert table.delimiter == delimiter
    assert table.had_bom is False


def test_accepts_matching_bom_and_zero_data_rows(tmp_path):
    table = load(tmp_path, b"\xef\xbb\xbf a ;b\r\n", "utf-8-sig", ";")
    assert table.headers == (" a ", "b")
    assert table.rows == ()
    assert table.had_bom is True


def test_bom_only_has_no_header(tmp_path):
    rejected(tmp_path, b"\xef\xbb\xbf", "missing_header", "utf-8-sig")


@pytest.mark.parametrize("content,encoding,code", [
    (b"\xef\xbb\xbfhead\n", "utf-8", "encoding_mismatch"),
    (b"head\n", "utf-8-sig", "encoding_mismatch"),
    (b"\xff\xfeh\x00\n\x00", "utf-8", "invalid_encoding"),
    (b"head\n\xff\n", "utf-8", "invalid_encoding"),
    (b"head\x00\n", "utf-8", "invalid_encoding"),
    (b"head\n\xef\xbb\xbfvalue\n", "utf-8", "invalid_encoding"),
])
def test_rejects_encoding_problems(tmp_path, content, encoding, code):
    rejected(tmp_path, content, code, encoding)


@pytest.mark.parametrize("encoding,delimiter", [
    ("latin-1", ","), ("UTF-8", ","), ("utf-8", None), ("utf-8", "|"),
])
def test_rejects_undeclared_or_unsupported_format(tmp_path, encoding, delimiter):
    with pytest.raises(CsvError):
        load(tmp_path, b"head\n", encoding, delimiter)


def test_size_limit_is_inclusive(tmp_path):
    content = b"head\n" + b"x" * (10_485_760 - 5)
    assert load(tmp_path, content).rows == (("x" * (10_485_760 - 5),),)
    rejected(tmp_path, content + b"x", "too_large")


@pytest.mark.parametrize("content,code", [
    (b"", "empty_file"),
    (b"\n", "missing_header"),
    (b",b\n", "invalid_header"),
    (b"a,\n", "invalid_header"),
    (b"a,a\n", "invalid_header"),
    (b"a,b\n1\n", "unequal_width"),
    (b"a,b\n1,2,3\n", "unequal_width"),
    (b"a\n\nb\n", "blank_record"),
    (b"a\n\"sensitive-cell-value", "invalid_quotes"),
    (b"a\n\"v\"x\n", "invalid_quotes"),
    (b"a\nv\"x\n", "invalid_quotes"),
    (b"a\rb\n", "invalid_line_ending"),
])
def test_rejects_malformed_csv(tmp_path, content, code):
    rejected(tmp_path, content, code)


def test_quoted_fields_and_line_endings(tmp_path):
    table = load(tmp_path, b'a,b\r\n"one,two","say ""hi"""\r\n"line\nnext",z\n"cr\r\nlf",q\n')
    assert table.rows == (("one,two", 'say "hi"'), ("line\nnext", "z"), ("cr\r\nlf", "q"))


def test_wrong_delimiter_is_not_silently_used(tmp_path):
    rejected(tmp_path, b"a;b\n1;2\n", "delimiter_mismatch", delimiter=",")


def test_rejects_non_csv_or_nonregular_input(tmp_path):
    other = tmp_path / "data.txt"
    other.write_bytes(b"a\n")
    with pytest.raises(CsvError) as raised:
        read_csv(other, "utf-8", ",")
    assert raised.value.code == "invalid_file"
    with pytest.raises(CsvError) as raised:
        read_csv(tmp_path / "missing.csv", "utf-8", ",")
    assert raised.value.code == "invalid_file"
