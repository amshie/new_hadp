"""Deny-by-default authorization matrix.

Authorization is server-side only. Client-side hiding is never a control. Each action
is permitted to an explicit set of roles; anything not listed is denied.
"""

from __future__ import annotations

from enum import Enum

from hadp_api.modules.enums import Role


class Action(str, Enum):
    PATIENT_CREATE = "patient.create"
    PATIENT_READ = "patient.read"
    CONSENT_RECORD = "consent.record"
    DOCUMENT_UPLOAD = "document.upload"
    IMPORT_RUN = "import.run"
    OBSERVATION_READ = "observation.read"
    REPORT_DRAFT = "report.draft"
    REPORT_EDIT = "report.edit"
    REPORT_APPROVE = "report.approve"
    REPORT_RELEASE = "report.release"


_ALL_STAFF = frozenset({Role.OWNER, Role.CLINICIAN, Role.ASSISTANT})

# Only a qualified clinician may approve or release a patient-facing report
# (CLAUDE.md: "require a qualified clinician to approve patient-facing reports").
_PERMISSIONS: dict[Action, frozenset[Role]] = {
    Action.PATIENT_CREATE: _ALL_STAFF,
    Action.PATIENT_READ: _ALL_STAFF,
    Action.CONSENT_RECORD: _ALL_STAFF,
    Action.DOCUMENT_UPLOAD: _ALL_STAFF,
    Action.IMPORT_RUN: _ALL_STAFF,
    Action.OBSERVATION_READ: _ALL_STAFF,
    Action.REPORT_DRAFT: frozenset({Role.OWNER, Role.CLINICIAN, Role.ASSISTANT}),
    Action.REPORT_EDIT: frozenset({Role.OWNER, Role.CLINICIAN, Role.ASSISTANT}),
    Action.REPORT_APPROVE: frozenset({Role.CLINICIAN}),
    Action.REPORT_RELEASE: frozenset({Role.CLINICIAN}),
}


def can(role: Role, action: Action) -> bool:
    return role in _PERMISSIONS.get(action, frozenset())
