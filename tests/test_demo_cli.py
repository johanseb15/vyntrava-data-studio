"""The local demo can be generated with one documented command."""

import json
from pathlib import Path
import subprocess
import sys


def test_demo_command_creates_a_reviewable_package(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    package = tmp_path / "paquete-sintetico"
    command = [sys.executable, str(repo / "examples" / "adel_data_demo_001.py"),
               str(package)]

    completed = subprocess.run(command, cwd=repo, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["datos"] == "SINTETICOS"
    assert result["estado"] == "revision_requerida"
    assert result["filas"] == 4
    assert result["incidencias"] == 1
    assert result["verificacion_independiente"] is True
    assert (package / "receta.json").is_file()
    assert (package / "clientes" / "cliente_demo" / "encargo_demo"
            / "evidencia" / "manifiesto.json").is_file()
