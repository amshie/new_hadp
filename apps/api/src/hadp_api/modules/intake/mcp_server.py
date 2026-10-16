"""The lab intake agent's MCP server — stdio, four tools, one document.

    HADP_INTAKE_TENANT_ID=… HADP_INTAKE_PATIENT_ID=… HADP_INTAKE_DOCUMENT_ID=… \\
    HADP_INTAKE_ACTOR_USER_ID=… HADP_INTAKE_MODEL_ID=… HADP_INTAKE_PROMPT_VERSION=… \\
    uv run python -m hadp_api.modules.intake.mcp_server

It exposes exactly `tools.TOOL_NAMES` and nothing else: no file system, no network, no tool that
writes an observation. The scope comes from the environment the harness sets, never from the
model. A missing variable stops the server before it serves anything.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from hadp_api.modules.intake.tools import TOOL_NAMES, IntakeScope, IntakeTools, ToolError

SERVER_NAME = "hadp-lab-intake"
_ENV = {
    "tenant_id": "HADP_INTAKE_TENANT_ID",
    "patient_id": "HADP_INTAKE_PATIENT_ID",
    "document_id": "HADP_INTAKE_DOCUMENT_ID",
    "actor_user_id": "HADP_INTAKE_ACTOR_USER_ID",
    "model_id": "HADP_INTAKE_MODEL_ID",
    "prompt_version": "HADP_INTAKE_PROMPT_VERSION",
}


def scope_from_env(env: Mapping[str, str] | None = None) -> IntakeScope:
    source: Mapping[str, str] = os.environ if env is None else env
    missing = [name for name in _ENV.values() if not source.get(name)]
    if missing:
        raise SystemExit(f"intake scope incomplete: set {', '.join(missing)}")
    return IntakeScope(
        tenant_id=uuid.UUID(source[_ENV["tenant_id"]]),
        patient_id=uuid.UUID(source[_ENV["patient_id"]]),
        document_id=uuid.UUID(source[_ENV["document_id"]]),
        actor_user_id=uuid.UUID(source[_ENV["actor_user_id"]]),
        extraction_provider=source.get("HADP_INTAKE_PROVIDER", "mcp-agent"),
        model_id=source[_ENV["model_id"]],
        prompt_version=source[_ENV["prompt_version"]],
    )


def _json(value: Any) -> str:
    def default(o: Any) -> Any:
        if isinstance(o, Decimal):
            return format(o, "f")
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, bytes):
            return None
        raise TypeError(type(o).__name__)

    return json.dumps(value, default=default, ensure_ascii=False)


def build_server(tools: IntakeTools) -> FastMCP:
    """Register the four tools on a FastMCP instance. Each wrapper only translates arguments and
    results; refusals come back as tool errors with a code, never as a stack trace."""
    server = FastMCP(SERVER_NAME)

    def guarded(fn: Any, **kwargs: Any) -> Any:
        try:
            return fn(**kwargs)
        except ToolError as exc:
            raise ValueError(f"{exc.code}: {exc.detail}") from None

    @server.tool(name="read_document", structured_output=False)
    def read_document(document_id: str, with_images: bool = True) -> list[Any]:
        """Page texts (text layer) and page images of the document this run is bound to."""
        view = guarded(tools.read_document, document_id=document_id, with_images=with_images)
        out: list[Any] = [
            _json(
                {
                    "document_id": view.document_id,
                    "page_count": view.page_count,
                    "pages": [
                        {"page": p.page, "source": p.source, "text": p.text} for p in view.pages
                    ],
                }
            )
        ]
        out.extend(Image(data=p.image_png, format="png") for p in view.pages if p.image_png)
        return out

    @server.tool(name="get_atlas_kpi")
    def get_atlas_kpi(query: str) -> str:
        """Catalog entries a name may mean: KPI code, canonical UCUM unit, aliases, LOINC."""
        return _json([asdict(e) for e in guarded(tools.get_atlas_kpi, query=query)])

    @server.tool(name="get_last_locked")
    def get_last_locked(patient_id: str, kpi_code: str) -> str:
        """The last published value of this patient for a KPI, or null."""
        last = guarded(tools.get_last_locked, patient_id=patient_id, kpi_code=kpi_code)
        return _json(asdict(last) if last is not None else None)

    @server.tool(name="create_pending_batch")
    def create_pending_batch(
        document_id: str,
        values: list[dict[str, Any]],
        patient_date_of_birth: str | None = None,
        issue_date: str | None = None,
        source_lab: str | None = None,
    ) -> str:
        """Propose the values read from the document. Code checks them and records each with a
        status; nothing is confirmed. Usable once per run. `source_lab` is the laboratory's
        name as printed on the letterhead (labels the batch; changes no value)."""
        outcome = guarded(
            tools.create_pending_batch,
            document_id=document_id,
            values=values,
            patient_date_of_birth=patient_date_of_birth,
            issue_date=issue_date,
            source_lab=source_lab,
        )
        return _json(asdict(outcome))

    registered = tuple(t.name for t in server._tool_manager.list_tools())
    assert sorted(registered) == sorted(TOOL_NAMES), registered
    return server


def main() -> int:
    server = build_server(IntakeTools(scope_from_env()))
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
