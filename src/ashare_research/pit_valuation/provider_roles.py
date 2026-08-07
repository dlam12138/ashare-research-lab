"""M2 Stage 2K.1R4E.4 — provider-role contract for the market snapshot registries.

Resolves the two market providers by **role** (``primary`` / ``secondary``)
instead of by provider name, so the formal release path never hard-codes a
second-source business contract such as ``load(..., "akshare")``.

- Registry v4 entries carry ``provider_id``, ``provider_role``,
  ``transport_library`` and ``underlying_provider``.
- Legacy registries (v2/v3) carry a ``provider`` name; a compatibility adapter
  maps ``baostock -> primary`` and ``akshare -> secondary``.  Old registries are
  never modified and historical artifact digests never change.
- Fail-closed: exactly one primary and exactly one secondary are required.
  0 or >1 of either role raises :class:`ProviderRoleError`.

This module never opens a database and never touches the network.
"""

from __future__ import annotations

from typing import Any

ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"
ROLES = (ROLE_PRIMARY, ROLE_SECONDARY)

#: Legacy registry provider-name -> role adapter (v2/v3 compatibility only).
LEGACY_ROLE_MAP = {
    "baostock": ROLE_PRIMARY,
    "akshare": ROLE_SECONDARY,
}

#: Registry contracts that carry the new role schema.
ROLE_SCHEMA_CONTRACTS = ("market_data_snapshot_registry_v4",)


class ProviderRoleError(ValueError):
    """The registry does not satisfy the exactly-one-primary/one-secondary contract."""


def is_role_schema(registry: dict[str, Any]) -> bool:
    """Whether the registry uses the v4 role schema (provider_id/provider_role)."""
    return registry.get("contract") in ROLE_SCHEMA_CONTRACTS


def entry_role(entry: dict[str, Any], *, registry: dict[str, Any] | None = None) -> str:
    """Return the role of one provider entry (v4 role field or legacy adapter)."""
    if is_role_schema(registry or {}):
        role = entry.get("provider_role", "")
        if role not in ROLES:
            raise ProviderRoleError(f"invalid provider_role {role!r} in registry entry")
        return role
    name = entry.get("provider", "")
    role = LEGACY_ROLE_MAP.get(name)
    if role is None:
        raise ProviderRoleError(f"legacy provider name {name!r} has no role mapping")
    return role


def entry_provider_id(entry: dict[str, Any], *, registry: dict[str, Any]) -> str:
    """Return the provider_id of an entry (v4) or the legacy provider name."""
    if is_role_schema(registry):
        provider_id = entry.get("provider_id", "")
        if not provider_id:
            raise ProviderRoleError("registry v4 entry missing provider_id")
        return provider_id
    return entry.get("provider", "")


def resolve_registry_providers(registry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (primary_entry, secondary_entry) with fail-closed role validation.

    Exactly one primary and exactly one secondary are required.  0 or >1 of
    either role is a :class:`ProviderRoleError` (NOT_TRUSTED), never a silent
    fallback.
    """
    providers = registry.get("providers")
    if not isinstance(providers, list) or not providers:
        raise ProviderRoleError("registry has no providers list")

    primary: dict[str, Any] | None = None
    secondary: dict[str, Any] | None = None
    for entry in providers:
        role = entry_role(entry, registry=registry)
        if role == ROLE_PRIMARY:
            if primary is not None:
                raise ProviderRoleError("more than one primary provider in registry")
            primary = entry
        elif role == ROLE_SECONDARY:
            if secondary is not None:
                raise ProviderRoleError("more than one secondary provider in registry")
            secondary = entry

    if primary is None:
        raise ProviderRoleError("no primary provider in registry")
    if secondary is None:
        raise ProviderRoleError("no secondary provider in registry")
    return primary, secondary


def provider_identity(entry: dict[str, Any], *, registry: dict[str, Any]) -> dict[str, Any]:
    """The canonical role-identity block bound into v2 reconciliation digests."""
    return {
        "provider_id": entry_provider_id(entry, registry=registry),
        "provider_role": entry_role(entry, registry=registry),
        "transport_library": entry.get("transport_library", ""),
        "underlying_provider": entry.get("underlying_provider", ""),
        "endpoint_identity": entry.get("endpoint_identity", ""),
        "object_sha256": entry.get("sha256", ""),
        "table_digest": entry.get("table_digest", ""),
        "row_count": entry.get("row_count"),
    }


def validate_provider_roles(registry: dict[str, Any]) -> dict[str, Any]:
    """Validate the role contract and return a summary (raises on failure)."""
    primary, secondary = resolve_registry_providers(registry)
    return {
        "primary_provider_id": entry_provider_id(primary, registry=registry),
        "primary_role": entry_role(primary, registry=registry),
        "primary_underlying_provider": primary.get("underlying_provider", ""),
        "primary_object_sha256": primary.get("sha256", ""),
        "secondary_provider_id": entry_provider_id(secondary, registry=registry),
        "secondary_role": entry_role(secondary, registry=registry),
        "secondary_transport_library": secondary.get("transport_library", ""),
        "secondary_underlying_provider": secondary.get("underlying_provider", ""),
        "secondary_endpoint_identity": secondary.get("endpoint_identity", ""),
        "secondary_object_sha256": secondary.get("sha256", ""),
        "secondary_table_digest": secondary.get("table_digest", ""),
    }
