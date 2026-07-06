"""Per-tenant KPI configuration.

Owners choose which global, read-only KPI catalog entries (ADR-0004) are active and visible
for THEIR clinic. The global catalog is never mutated; this module records only a tenant-scoped,
RLS-protected override on top of it. The effective value is COALESCE(tenant override, catalog).
"""
