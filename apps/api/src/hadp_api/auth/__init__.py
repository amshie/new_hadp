"""Authentication and authorization.

Production authentication is OIDC (a gated vendor decision). Development/tests use a
clearly labeled dev provider that never runs in production. Authorization is
server-side and deny-by-default.
"""
