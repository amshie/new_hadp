"""Lab intake agent: values a model PROPOSES from a stored document, checked by code, and
confirmed by a human before any of them becomes an observation (docs/product/INTAKE_AGENT.md).

Nothing in this module writes an observation. The only write is a batch of pending values,
and a pending value is not part of the patient record: the timeline, the interpretation and
the reports never read it.
"""
