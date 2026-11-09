"""Optional live check: load the schema into PostgreSQL inside a transaction, then roll back.

Nothing is left behind in the target database. Needs the `psql` client on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from cvtwin.checks import SCHEMA_SQL, CheckResult


def check_schema_live(root: Path, host: str, port: int, user: str, dbname: str) -> CheckResult:
    if shutil.which("psql") is None:
        return CheckResult("schema_loads_in_postgres", SCHEMA_SQL, "warn", False, "psql not found; skipped")
    schema = (root / SCHEMA_SQL).resolve()
    script = f"BEGIN;\n\\i '{schema}'\nROLLBACK;\n"
    proc = subprocess.run(
        ["psql", "-h", host, "-p", str(port), "-U", user, "-d", dbname,
         "-v", "ON_ERROR_STOP=1", "-q", "-X"],
        input=script, capture_output=True, text=True, timeout=120,
    )
    ok = proc.returncode == 0
    detail = "schema created and rolled back cleanly" if ok else (proc.stderr.strip() or proc.stdout.strip())[:500]
    return CheckResult("schema_loads_in_postgres", SCHEMA_SQL, "error", ok, detail)
