# 0012 — Patient erasure: DeletionRequest gate + gated tombstone

Date: 2026-07-05 · Status: **PR A shipped (request lifecycle); PR B planned (execution).**

Answers the question "who can delete a patient?" — which, before this work, was _nobody_,
because the DB actively blocks it. This note records why erasure must be a **tombstone**, not
a hard delete, and how the two-person workflow is built.

## The constraint that forces the design

Two independent DB facts make a naive `DELETE FROM patients` impossible:

1. `consent_events.patient_id` and `patient_invitations.patient_id` are `ON DELETE RESTRICT`
   — Postgres refuses to delete a patient with any consent event or invitation.
2. `interpretation_runs.patient_id` is `ON DELETE CASCADE`, but `interpretation_runs` and
   `tri_state_cells` carry **unconditional append-only triggers** (migration 0003:
   `hadp_block_interpretation_mutation` RAISEs on any UPDATE/DELETE). A patient delete would
   cascade into those tables, the trigger would fire, and the whole delete would abort.

So erasure **anonymizes the patient row (a tombstone)** and **hard-deletes the PII-bearing
child artifacts**, while **leaving the append-only ledgers (consent, audit, interpretation)
structurally intact** — after the tombstone their rows carry no identity, only IDs + closed
enums. This satisfies GDPR data-minimization without violating the immutability doctrine.

## PR A — request lifecycle (this slice, no data touched)

- **Migration 0015** (additive, non-destructive; touches no immutability machinery):
  `deletion_requests` table (tenant-scoped, RLS ENABLE+FORCE, FKs `ON DELETE RESTRICT`,
  closed-enum `status`/`reason_category` with CHECK constraints, partial unique index = at
  most one non-terminal request per patient) + a nullable `patients.erased_at` marker.
- **Two-person gate** (`auth/authz.py`): `PRIVACY_REQUEST_CREATE` = owner,
  `PRIVACY_REQUEST_LIST` = owner + medical director, `PRIVACY_REQUEST_DECIDE` = medical
  director, `PRIVACY_REQUEST_EXECUTE` = owner + medical director (defined now, wired in PR B).
  The requester and decider are always different people (one role per tenant); the service
  additionally enforces decider ≠ requester as defense-in-depth.
- **Service + routes**: create (owner) → approve/reject (medical director) → cancel (requester,
  pending only). Every transition audited with status/reason **codes only** — never identity.
  The request row itself carries no free text (reason is a closed enum), so it cannot leak PII.
- **Web**: an owner-only "Löschung beantragen" action on the patient detail (files a request,
  deletes nothing) and an owner + medical-director queue at
  `/einstellungen/loeschantraege` (approve / reject / withdraw).

## PR B — the erasure engine (planned)

`POST /deletion-requests/{id}/execute` (owner or medical director) consumes an **approved**
request in one request transaction:

1. Append a `WITHDRAWN` consent event for each currently-active purpose (reuses
   `consents.withdraw_consent`, which also revokes live report links for `report_release`).
2. Revoke open invitations; revoke any remaining patient access links.
3. Hard-delete PII-bearing child artifacts (observations, imports/review-items, documents
   rows, reports + versions/statements/evidence). These tables carry app DML (no trigger).
4. **Redact** free-text rationale on the append-only interpretation tables to NULL. Because
   those tables have `REVOKE UPDATE` + an unconditional trigger, this needs a **GUC-gated
   redaction path** added in a **separate migration 0016** (a `SECURITY DEFINER` scrub
   function + a trigger change that permits _only_ a rationale→NULL redaction when an
   `app.erasure` GUC is set — never a general update/delete). This is the one immutability-
   adjacent change; it is isolated to PR B and reviewed alongside the engine. **consent_events
   and audit_events triggers are never touched.**
5. Tombstone the patient row: blank `display_name` (placeholder), NULL `date_of_birth` /
   `external_ref`, set `erased_at`. Directory/worklist/duplicate-probe filter out `erased_at`;
   the detail page shows a tombstone banner instead of 404 (audit links stay resolvable).
6. Record a **count-only** `erasure_manifest` (per-artifact-type counts, never identifiers)
   and audit `privacy.erasure_executed`.
7. After commit, purge the source-document objects from storage (S3-delete is not
   transactional — keys are collected pre-commit and purged idempotently after; a partial
   failure is its own audit event).

## Open gates (Counsel / DPO — not engineering defaults)

- Erasure vs. physician retention duty (§ 630f BGB / GDPR Art. 17(3)(b) exemption): does
  anonymization satisfy "erasure", and which data must be retained regardless?
- The real `reason_category` taxonomy (the three values here are synthetic-Alpha placeholders,
  like `ConsentPurpose`).
- Whether interpretation rationale must be redacted, fully removed, or may remain post-tombstone.

Engineering provides the mechanism for the synthetic Alpha; the policy determination belongs to
the named Regulatory Lead / counsel. Real patient data remains gated regardless.
