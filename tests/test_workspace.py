from pathlib import Path

import pytest

from vyntrava_data_studio.workspace import WorkspaceError, resolve_input, resolve_output


@pytest.fixture
def spaces(tmp_path):
    root = tmp_path / "clientes"
    for client, job in (("cliente_a", "encargo_a"), ("cliente_b", "encargo_b")):
        base = root / client / job
        for folder in ("originales", "trabajo", "salidas", "evidencia"):
            (base / folder).mkdir(parents=True, exist_ok=True)
    original = root / "cliente_a" / "encargo_a" / "originales" / "datos.csv"
    original.write_bytes(b"id\n1\n")
    return root


def test_resolves_existing_original_and_unoccupied_output(spaces):
    original = resolve_input(spaces, "cliente_a", "encargo_a", "datos.csv")
    output = resolve_output(spaces, "cliente_a", "encargo_a", "reporte.json", "salidas")
    assert original == spaces / "cliente_a" / "encargo_a" / "originales" / "datos.csv"
    assert output == spaces / "cliente_a" / "encargo_a" / "salidas" / "reporte.json"
    assert not output.exists()
    assert original.read_bytes() == b"id\n1\n"


@pytest.mark.parametrize("name", ["..", ".", "../cliente_b", "x/y.csv", r"x\y.csv",
                                    "/tmp/datos.csv", r"C:\datos.csv", r"\\server\share\datos.csv",
                                    "x:stream", "bad\x00name", "bad\x85name"])
def test_rejects_invalid_basename_before_access(spaces, name):
    with pytest.raises(WorkspaceError) as exc:
        resolve_input(spaces, "cliente_a", "encargo_a", name)
    assert exc.value.code == "invalid_basename"
    with pytest.raises(WorkspaceError) as exc:
        resolve_output(spaces, "cliente_a", "encargo_a", name, "salidas")
    assert exc.value.code == "invalid_basename"


@pytest.mark.parametrize("client,job", [("../cliente_b", "encargo_a"),
                                           ("cliente_a", "../encargo_b"),
                                           ("cliente_b/encargo_b", "encargo_a"),
                                           ("Cliente_A", "encargo_a")])
def test_rejects_invalid_client_or_job(spaces, client, job):
    with pytest.raises(WorkspaceError) as exc:
        resolve_input(spaces, client, job, "datos.csv")
    assert exc.value.code == "invalid_identifier"


def test_cannot_use_another_clients_original(spaces):
    foreign = spaces / "cliente_b" / "encargo_b" / "originales" / "datos.csv"
    foreign.write_bytes(b"secret")
    with pytest.raises(WorkspaceError) as exc:
        resolve_input(spaces, "cliente_a", "encargo_a", "otro.csv")
    assert exc.value.code == "missing_input"
    assert foreign.read_bytes() == b"secret"


@pytest.mark.parametrize("kind", ["originales", "../originales", "otro", "salidas/trabajo"])
def test_rejects_output_outside_allowed_folders(spaces, kind):
    with pytest.raises(WorkspaceError) as exc:
        resolve_output(spaces, "cliente_a", "encargo_a", "datos.csv", kind)
    assert exc.value.code == "invalid_output_kind"


def test_rejects_non_string_output_kind(spaces):
    with pytest.raises(WorkspaceError) as exc:
        resolve_output(spaces, "cliente_a", "encargo_a", "datos.csv", [])
    assert exc.value.code == "invalid_output_kind"


@pytest.mark.parametrize("kind", ["salidas", "evidencia", "trabajo"])
def test_output_is_confined_to_requested_folder(spaces, kind):
    result = resolve_output(spaces, "cliente_a", "encargo_a", "nuevo.json", kind)
    assert result == spaces / "cliente_a" / "encargo_a" / kind / "nuevo.json"


def test_rejects_existing_output_including_original_name(spaces):
    output = spaces / "cliente_a" / "encargo_a" / "salidas" / "datos.csv"
    output.write_bytes(b"prior")
    with pytest.raises(WorkspaceError) as exc:
        resolve_output(spaces, "cliente_a", "encargo_a", "datos.csv", "salidas")
    assert exc.value.code == "output_exists"
    assert output.read_bytes() == b"prior"


def test_rejects_missing_input_and_missing_workspace(spaces):
    with pytest.raises(WorkspaceError) as exc:
        resolve_input(spaces, "cliente_a", "encargo_a", "missing.csv")
    assert exc.value.code == "missing_input"
    with pytest.raises(WorkspaceError) as exc:
        resolve_output(spaces, "cliente_a", "missing", "out.json", "salidas")
    assert exc.value.code == "missing_workspace"


def test_rejects_redirected_ancestor_of_root(tmp_path, spaces):
    import os
    import subprocess

    if os.name != "nt":
        pytest.skip("Windows junction only")
    link = tmp_path / "alias"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(tmp_path)],
                            capture_output=True)
    if result.returncode:
        pytest.skip("junction creation unavailable")
    with pytest.raises(WorkspaceError) as exc:
        resolve_input(link / "clientes", "cliente_a", "encargo_a", "datos.csv")
    assert exc.value.code == "redirected_path"


def test_rejects_directory_in_place_of_original(spaces):
    (spaces / "cliente_a" / "encargo_a" / "originales" / "folder.csv").mkdir()
    with pytest.raises(WorkspaceError) as exc:
        resolve_input(spaces, "cliente_a", "encargo_a", "folder.csv")
    assert exc.value.code == "not_regular_file"


def test_rejects_symlink_to_another_client_before_access(spaces):
    foreign = spaces / "cliente_b" / "encargo_b" / "originales" / "datos.csv"
    foreign.write_bytes(b"foreign")
    link = spaces / "cliente_a" / "encargo_a" / "originales" / "atajo.csv"
    try:
        link.symlink_to(foreign)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(WorkspaceError) as exc:
        resolve_input(spaces, "cliente_a", "encargo_a", "atajo.csv")
    assert exc.value.code == "redirected_path"
    assert foreign.read_bytes() == b"foreign"


def test_rejects_symlinked_workspace_component(spaces):
    link = spaces / "cliente_a" / "encargo_a" / "salidas" / "shortcut.json"
    target = spaces / "cliente_b" / "encargo_b" / "salidas" / "target.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(WorkspaceError) as exc:
        resolve_output(spaces, "cliente_a", "encargo_a", "shortcut.json", "salidas")
    assert exc.value.code == "redirected_path"


@pytest.mark.skipif(not hasattr(Path, "is_junction"), reason="junction inspection unavailable")
def test_rejects_junction_to_other_client(spaces):
    import subprocess

    if __import__("os").name != "nt":
        pytest.skip("Windows junction only")
    link = spaces / "cliente_a" / "encargo_a" / "salidas" / "linked"
    target = spaces / "cliente_b" / "encargo_b" / "salidas"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                            capture_output=True)
    if result.returncode:
        pytest.skip("junction creation unavailable")
    with pytest.raises(WorkspaceError) as exc:
        resolve_output(spaces, "cliente_a", "encargo_a", "linked", "salidas")
    assert exc.value.code == "redirected_path"
