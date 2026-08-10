from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_ROOT = REPO_ROOT / "src/repo_familiar/templates"


class PackagingTests(unittest.TestCase):
    def test_wheel_contains_every_canonical_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["uv", "build", "--wheel", "--out-dir", tmpdir],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            wheel_path = next(Path(tmpdir).glob("*.whl"))
            with ZipFile(wheel_path) as wheel:
                members = set(wheel.namelist())

        expected = {
            "repo_familiar/templates/" + path.relative_to(TEMPLATES_ROOT).as_posix()
            for path in TEMPLATES_ROOT.rglob("*.tmpl")
        }
        self.assertEqual(expected - members, set())


if __name__ == "__main__":
    unittest.main()
