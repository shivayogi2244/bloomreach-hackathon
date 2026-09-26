"""Pinpoints TABLE_OR_VIEW_NOT_FOUND: shows what the app resolves vs what exists.

Run from the folder you serve the app from:  python -m tests.where_are_tables
"""

import os
import sys

from dotenv import dotenv_values


def main() -> None:
    print("=" * 64)
    print("1) Resolution chain for DATABRICKS_TABLE")
    print("=" * 64)
    os_val = os.environ.get("DATABRICKS_TABLE")
    file_val = dotenv_values(".env").get("DATABRICKS_TABLE")
    print(f"  OS environment var      : {os_val!r}" + ("   <-- OVERRIDES .env!" if os_val else ""))
    print(f"  .env file in CWD        : {file_val!r}")
    print(f"  CWD                     : {os.getcwd()}")
    sys.path.insert(0, os.getcwd())
    from app.config import DATABRICKS_TABLE as resolved

    print(f"  app.config resolves to  : {resolved!r}")

    print()
    print("=" * 64)
    print("2) What tables actually exist (live warehouse queries)")
    print("=" * 64)
    from app.databricks_tool import _run_statement

    candidates = [
        "workspace.default",
        "main.default",
        "databricks-hackathon.shivayogimath_dc",
        "databricks-admin.default",
    ]
    found: dict[str, list[str]] = {}
    for schema in candidates:
        try:
            rows = _run_statement(f"SHOW TABLES IN {schema}")
            names = [r["tableName"] for r in rows]
            found[schema] = names
            print(f"  {schema:42} -> {names if names else '(empty)'}")
        except Exception as exc:
            msg = str(exc)[:80].replace("\n", " ")
            print(f"  {schema:42} -> inaccessible ({msg})")

    print()
    print("=" * 64)
    print("3) Reproducing the app's exact query on the resolved table")
    print("=" * 64)
    print(f"  SELECT * FROM {resolved} LIMIT 3")
    try:
        rows = _run_statement(f"SELECT * FROM {resolved} LIMIT 3")
        print(f"  [OK] returned {len(rows)} row(s) -- the app should work; restart the server?")
        for r in rows:
            print("   ", r)
    except Exception as exc:
        print(f"  [XX] FAILED: {str(exc)[:200]}")

    print()
    print("=" * 64)
    print("4) Verdict")
    print("=" * 64)
    home = next((s for s, n in found.items() if "loop_segments" in n), None)
    if home is None:
        print("  loop_segments does not exist in ANY candidate schema.")
        print("  -> Re-run sql/setup.sql in the SQL Editor of THIS workspace,")
        print("     and make sure the CREATE TABLE prefix matches a real schema.")
    elif home == resolved:
        print(f"  Table is in {home} and app resolves the same. If chat still fails,")
        print("  the server process was started before the .env change -> restart it.")
    else:
        print(f"  MISMATCH: table lives in {home}, app queries {resolved}.")
        print(f"  -> Fix .env:  DATABRICKS_TABLE={home}.loop_segments")
    if os_val and os_val != file_val:
        print("  NOTE: an OS-level DATABRICKS_TABLE is overriding your .env file.")
        print("  -> `set DATABRICKS_TABLE=` (cmd) / Remove-Item Env:DATABRICKS_TABLE (PS),")
        print("     or fix the setx value, then open a NEW terminal.")


if __name__ == "__main__":
    main()
