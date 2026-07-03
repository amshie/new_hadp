"""Staff invitations: a clinic owner invites a colleague who self-onboards into a role.

Mirrors the patient-invitation credential (single-use, TTL'd, revocable, hash-only), but
redemption creates a User + Membership rather than a consent event. The role is fixed by the
owner at invite time — the redeemer never selects it. Owner-only, tenant-scoped, audited.
"""
