"""Export the FastAPI OpenAPI document to packages/api-client/openapi.json.

The exported document is the contract from which the TypeScript client is generated
(`make gen-client`). It is never edited by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

from hadp_api.main import app

_REPO_ROOT = Path(__file__).resolve().parents[5]
_OUT = _REPO_ROOT / "packages" / "api-client" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {_OUT.relative_to(_REPO_ROOT)} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
