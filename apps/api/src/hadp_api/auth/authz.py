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
    INVITATION_CREATE = "invitation.create"
    # Staff administration: inviting a colleague who self-onboards into a role. Owner-only
    # (a strictly narrower privilege than patient invitation), and gates create/list/revoke.
    STAFF_INVITE_CREATE = "staff_invite.create"
    REVIEW_RESOLVE = "review.resolve"
    INTERPRETATION_AUTHOR = "interpretation.author"
    REPORT_DRAFT = "report.draft"
    REPORT_EDIT = "report.edit"
    REPORT_APPROVE = "report.approve"
    REPORT_REJECT = "report.reject"
    REPORT_RELEASE = "report.release"


# Operational care staff (create/upload/import/draft); the medical director is the
# governance gate, not an operator.
_CARE_STAFF = frozenset({Role.OWNER, Role.CLINICIAN, Role.ASSISTANT})
# Read access additionally includes the medical director, who must review content
# and evidence before releasing it.
_READ_STAFF = _CARE_STAFF | {Role.MEDICAL_DIRECTOR}

# Two-tier Physician Gate (INTENDED_USE/ADR-0003): a qualified CLINICIAN authors the
# interpretation and approves the report; only a MEDICAL DIRECTOR locks/releases
# patient-facing content. The two steps are deliberately held by different roles.
_PERMISSIONS: dict[Action, frozenset[Role]] = {
    Action.PATIENT_CREATE: _CARE_STAFF,
    Action.PATIENT_READ: _READ_STAFF,
    Action.CONSENT_RECORD: _CARE_STAFF,
    Action.DOCUMENT_UPLOAD: _CARE_STAFF,
    Action.IMPORT_RUN: _CARE_STAFF,
    Action.OBSERVATION_READ: _READ_STAFF,
    # Inviting a patient is operational provisioning (staff-wide), NOT the
    # clinician-only release gate (docs/notes/0010 §4).
    Action.INVITATION_CREATE: _CARE_STAFF,
    # Inviting staff is tenant administration: OWNER only. A colleague self-onboards into
    # the role the owner chose (the redeemer never selects their own role). This grants
    # broad, cross-patient clinic access, so it is the most restricted provisioning action.
    Action.STAFF_INVITE_CREATE: frozenset({Role.OWNER}),
    # Review-queue resolution is a clinical judgement (WORKFLOW §2.2/§2.4: the
    # assistant triages the queue but may not resolve clinically).
    Action.REVIEW_RESOLVE: frozenset({Role.CLINICIAN}),
    Action.INTERPRETATION_AUTHOR: frozenset({Role.CLINICIAN}),
    Action.REPORT_DRAFT: _CARE_STAFF,
    Action.REPORT_EDIT: _CARE_STAFF,
    Action.REPORT_APPROVE: frozenset({Role.CLINICIAN}),
    # Either gate tier may refuse: the clinician withdraws a draft/their approval;
    # the medical director refuses at the release gate.
    Action.REPORT_REJECT: frozenset({Role.CLINICIAN, Role.MEDICAL_DIRECTOR}),
    Action.REPORT_RELEASE: frozenset({Role.MEDICAL_DIRECTOR}),
}


def can(role: Role, action: Action) -> bool:
    return role in _PERMISSIONS.get(action, frozenset())
