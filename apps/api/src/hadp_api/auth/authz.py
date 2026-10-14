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
    # Member administration: list the clinic team, change a member's role, remove a member.
    MEMBER_LIST = "member.list"
    MEMBER_ROLE_CHANGE = "member.role_change"
    MEMBER_REMOVE = "member.remove"
    # Patient erasure (GDPR Art. 17) — a two-person gate. Requesting is tenant administration
    # (owner); deciding is the governance tier (medical director, like report release); executing
    # the approved, irreversible erasure is permitted to either administrative principal.
    PRIVACY_REQUEST_CREATE = "privacy_request.create"
    PRIVACY_REQUEST_LIST = "privacy_request.list"
    PRIVACY_REQUEST_DECIDE = "privacy_request.decide"
    PRIVACY_REQUEST_EXECUTE = "privacy_request.execute"
    # Data export (GDPR Art. 15/20): the whole record of one patient leaves in one file —
    # tenant administration, like requesting an erasure.
    PRIVACY_EXPORT = "privacy.export"
    # The clinic's own audit trail: who did what, and when. The clinic is the controller and
    # answers for its staff's access — tenant administration.
    AUDIT_READ = "audit.read"
    # One's own recorded actions in the clinic, and nobody else's: what the overview shows a
    # colleague who may not read the whole trail.
    AUDIT_READ_OWN = "audit.read_own"
    # The preparation-time metric (go-live plan A6): what the clinic states about its own
    # preparation time, and what the platform measures from the report lifecycle. It shows
    # how quickly the clinic's clinicians work through their reports — tenant administration.
    # The clinic's own profile: its name and address. Every staff role reads it (it is in the
    # shell anyway); the owner changes it — tenant administration.
    TENANT_PROFILE_READ = "tenant_profile.read"
    TENANT_PROFILE_EDIT = "tenant_profile.edit"
    METRIC_READ = "metric.read"
    METRIC_RECORD = "metric.record"
    REVIEW_RESOLVE = "review.resolve"
    INTERPRETATION_AUTHOR = "interpretation.author"
    REPORT_DRAFT = "report.draft"
    REPORT_EDIT = "report.edit"
    REPORT_REDRAFT = "report.redraft"
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
    # Member administration is tenant administration: OWNER only, like staff invites.
    # Role assignment is orthogonal to the two-tier Physician Gate — the gate is enforced
    # at action time by the assigned role; nothing here touches report approve/release.
    Action.MEMBER_LIST: frozenset({Role.OWNER}),
    Action.MEMBER_ROLE_CHANGE: frozenset({Role.OWNER}),
    Action.MEMBER_REMOVE: frozenset({Role.OWNER}),
    # Erasure two-person gate. Requesting (and cancelling one's own request) is owner-only,
    # like the other tenant-administration actions. Deciding is medical-director-only — the
    # governance tier, deliberately a DIFFERENT role than the requester so no single person can
    # both request and approve an irreversible erasure. Executing an approved request is allowed
    # to either administrative principal (owner or medical director).
    Action.PRIVACY_REQUEST_CREATE: frozenset({Role.OWNER}),
    # Both gate tiers see the queue: the owner tracks their requests, the medical director
    # decides them.
    Action.PRIVACY_REQUEST_LIST: frozenset({Role.OWNER, Role.MEDICAL_DIRECTOR}),
    Action.PRIVACY_REQUEST_DECIDE: frozenset({Role.MEDICAL_DIRECTOR}),
    Action.PRIVACY_REQUEST_EXECUTE: frozenset({Role.OWNER, Role.MEDICAL_DIRECTOR}),
    Action.PRIVACY_EXPORT: frozenset({Role.OWNER}),
    # Reading the audit trail shows every colleague's access to every record: OWNER only.
    Action.AUDIT_READ: frozenset({Role.OWNER}),
    # One's own actions: every staff role. It shows a colleague nothing they did not do.
    Action.AUDIT_READ_OWN: _READ_STAFF,
    # The clinic's own preparation-time statements and the measured turnaround: OWNER only.
    Action.TENANT_PROFILE_READ: _READ_STAFF,
    Action.TENANT_PROFILE_EDIT: frozenset({Role.OWNER}),
    Action.METRIC_READ: frozenset({Role.OWNER}),
    Action.METRIC_RECORD: frozenset({Role.OWNER}),
    # Review-queue resolution is a clinical judgement (WORKFLOW §2.2/§2.4: the
    # assistant triages the queue but may not resolve clinically).
    Action.REVIEW_RESOLVE: frozenset({Role.CLINICIAN}),
    Action.INTERPRETATION_AUTHOR: frozenset({Role.CLINICIAN}),
    Action.REPORT_DRAFT: _CARE_STAFF,
    Action.REPORT_EDIT: _CARE_STAFF,
    # A new draft version after a laboratory correction discards the current wording and
    # withdraws a released version from the patient: the clinician's step.
    Action.REPORT_REDRAFT: frozenset({Role.CLINICIAN}),
    Action.REPORT_APPROVE: frozenset({Role.CLINICIAN}),
    # Either gate tier may refuse: the clinician withdraws a draft/their approval;
    # the medical director refuses at the release gate.
    Action.REPORT_REJECT: frozenset({Role.CLINICIAN, Role.MEDICAL_DIRECTOR}),
    Action.REPORT_RELEASE: frozenset({Role.MEDICAL_DIRECTOR}),
}


def can(role: Role, action: Action) -> bool:
    return role in _PERMISSIONS.get(action, frozenset())


def permissions_by_role() -> dict[Role, list[str]]:
    """Every role and the actions the matrix grants it, in the order the actions are declared.

    What a clinic page shows as "what a role may do" — read from this matrix, never restated.
    """
    return {
        role: [action.value for action in Action if role in _PERMISSIONS.get(action, frozenset())]
        for role in Role
    }
