"""Derived-value computation (ADR-0004 Slice 4).

A versioned registry of DETERMINISTIC formulas + a controlled compute service that turns validated
source Observations into a new derived Observation with full, immutable provenance. Deterministic
arithmetic only — never AI, never a verdict/score, never presented as a measured value; nothing runs
automatically (§10), and computation fails closed on missing/unpublished/incomparable inputs (§9).
"""
