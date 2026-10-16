"""Shadow mode of the lab intake agent: propose without exposing, compare afterwards.

    # 1. A shadow proposal for a stored PDF (no screen, no decision possible):
    cd apps/api && uv run python evals/intake_shadow.py propose \\
        --tenant-id … --actor-user-id … --patient-id … --document-id …

    # 2. The clinic keys the same report's values the way it does today (import / manual entry).

    # 3. The comparison, per laboratory and per field, appended to the results log:
    cd apps/api && uv run python evals/intake_shadow.py compare --tenant-id … --actor-user-id …

Runs against the configured database as the application role, inside the tenant named — the
same path as the API. It writes a shadow batch (step 1) and nothing else; the comparison reads.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from hadp_api.config import get_settings  # noqa: E402
from hadp_api.db.engine import get_sessionmaker, set_tenant_context  # noqa: E402
from hadp_api.modules.documents.blob import get_blob_store  # noqa: E402
from hadp_api.modules.documents.models import SourceDocument  # noqa: E402
from hadp_api.modules.intake import service, shadow  # noqa: E402
from hadp_api.modules.intake.pages import load_pages  # noqa: E402
from hadp_api.modules.intake.providers import get_provider  # noqa: E402

DEFAULT_RESULTS = HERE / "results" / "intake_shadow_results.jsonl"


def _session(tenant_id: uuid.UUID, actor: uuid.UUID):  # type: ignore[no-untyped-def]
    db = get_sessionmaker()()
    set_tenant_context(db, tenant_id, actor)
    return db


def propose(args: argparse.Namespace) -> int:
    settings = get_settings()
    db = _session(args.tenant_id, args.actor_user_id)
    try:
        document = db.get(SourceDocument, args.document_id)
        if document is None or document.patient_id != args.patient_id:
            print("document not found for this patient", file=sys.stderr)
            return 2
        data = get_blob_store(settings).get(document.storage_key)
        pages = load_pages(data, settings)
        provider = get_provider(args.provider or settings.intake_provider, settings)
        result = service.create_pending_batch(
            db,
            tenant_id=args.tenant_id,
            patient_id=args.patient_id,
            document_id=args.document_id,
            proposal=provider.extract(data, pages),
            created_by_user_id=args.actor_user_id,
            shadow=True,
        )
        db.commit()
        print(
            json.dumps(
                {
                    "batch_id": str(result.batch_id),
                    "green": result.green,
                    "yellow": result.yellow,
                    "red": result.red,
                    "shadow": True,
                }
            )
        )
        return 0
    finally:
        db.close()


def compare(args: argparse.Namespace) -> int:
    db = _session(args.tenant_id, args.actor_user_id)
    try:
        rows = shadow.compare(db, tenant_id=args.tenant_id)
    finally:
        db.close()
    entry = {
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tenant_id": str(args.tenant_id),
        "labs": [r.as_dict() for r in rows],
    }
    args.results.parent.mkdir(parents=True, exist_ok=True)
    with args.results.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(
        "| Laboratory | Batches | Proposed | Keyed | Matched | Value | Unit | Ref low | Ref high "
        "| Keying delay (median s) |"
    )
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in rows:
        d = r.as_dict()
        fd = d["field_divergence"]

        def pct(x: float | None) -> str:
            return "—" if x is None else f"{x:.2f}"

        print(
            f"| {d['source_lab']} | {d['batches']} | {d['proposed']} | {d['keyed']} | "
            f"{d['matched']} | "
            f"{pct(fd['value_text'])} | {pct(fd['unit_text'])} | {pct(fd['reference_low'])} | "
            f"{pct(fd['reference_high'])} | {pct(d['keying_delay_seconds_median'])} |"
        )
    print(f"appended 1 record to {args.results}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("propose")
    p.add_argument("--tenant-id", type=uuid.UUID, required=True)
    p.add_argument("--actor-user-id", type=uuid.UUID, required=True)
    p.add_argument("--patient-id", type=uuid.UUID, required=True)
    p.add_argument("--document-id", type=uuid.UUID, required=True)
    p.add_argument("--provider", default=None)
    p.set_defaults(run=propose)
    c = sub.add_parser("compare")
    c.add_argument("--tenant-id", type=uuid.UUID, required=True)
    c.add_argument("--actor-user-id", type=uuid.UUID, required=True)
    c.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    c.set_defaults(run=compare)
    args = parser.parse_args(argv)
    return int(args.run(args))


if __name__ == "__main__":
    raise SystemExit(main())
