"""Privacy requests (GDPR data-subject workflows).

Currently holds the patient-erasure request lifecycle (`DeletionRequest`): a two-person
gate — owner requests, medical director decides — that authorizes the later gated,
irreversible erasure. The erasure engine itself is a separate slice (docs/notes/0012).
"""
