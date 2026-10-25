"""Writes web/files.json: the files browser Python loads (a static site can't list folders).
Run it after changing store/, tests/ or tutor/. The Pages workflow runs it too."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKIP = {"__pycache__", ".pytest_cache"}

files = sorted(str(f.relative_to(ROOT)) for folder in ("store", "tests", "tutor") for f in (ROOT / folder).rglob("*")
               if f.is_file() and not SKIP & set(f.parts) and f.suffix not in {".db", ".pyc"})
(ROOT / "web" / "files.json").write_text(json.dumps(files, indent=1) + "\n")
print(len(files), "files")
