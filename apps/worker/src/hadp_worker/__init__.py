"""Background worker (Redis-backed).

Milestone 0.5 scope: import normalization runs inline in the API for the spike. This
worker is the labeled seam where that work moves to an asynchronous, retried,
idempotent job in later milestones. It is intentionally minimal and does NOT yet
process clinical jobs.
"""
