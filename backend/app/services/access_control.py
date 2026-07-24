from enum import StrEnum

from app.services.document_audit_access import normalize_role


class ModulePermission(StrEnum):
    READ = "read"
    WRITE = "write"
    ADMINISTER = "administer"


BUSINESS_MODULES = (
    "iron-house-chat",
    "legal",
    "projects",
    "suppliers",
    "rfqs",
    "rfq-automation",
    "bid-package",
    "bid-readiness",
    "bids",
    "estimates",
    "cost-codes",
    "quotes",
    "documents",
    "drawing-intelligence",
    "takeoff",
    "municipality",
    "tenders",
    "equipment",
    "field-operations",
    "finance",
)
ALL_MODULES = (*BUSINESS_MODULES, "users", "operations")

ESTIMATOR_WRITE_MODULES = frozenset(
    {
        "projects",
        "suppliers",
        "rfqs",
        "rfq-automation",
        "bid-package",
        "bid-readiness",
        "bids",
        "estimates",
        "cost-codes",
        "quotes",
        "documents",
        "drawing-intelligence",
        "takeoff",
        "municipality",
        "tenders",
    }
)


def module_permissions_for_role(role: str | None, module: str) -> frozenset[ModulePermission]:
    normalized_role = normalize_role(role)
    if module not in ALL_MODULES:
        return frozenset()
    if module == "legal" and normalized_role != "admin":
        return frozenset()
    if module in {"finance", "iron-house-chat"} and normalized_role not in {"admin", "operations_manager"}:
        return frozenset()
    if normalized_role == "admin":
        permissions = {ModulePermission.READ, ModulePermission.WRITE}
        if module in {"users", "operations"}:
            permissions.add(ModulePermission.ADMINISTER)
        return frozenset(permissions)
    if module in {"users", "operations"}:
        return frozenset()
    if normalized_role == "operations_manager":
        return frozenset({ModulePermission.READ, ModulePermission.WRITE})
    if normalized_role == "estimator":
        permissions = {ModulePermission.READ}
        if module in ESTIMATOR_WRITE_MODULES:
            permissions.add(ModulePermission.WRITE)
        return frozenset(permissions)
    if normalized_role == "viewer":
        permissions = {ModulePermission.READ}
        if module == "field-operations":
            permissions.add(ModulePermission.WRITE)
        return frozenset(permissions)
    return frozenset()


def required_permission(module: str, method: str) -> ModulePermission:
    if module in {"users", "operations"}:
        return ModulePermission.ADMINISTER
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return ModulePermission.READ
    return ModulePermission.WRITE


def can_access_module(role: str | None, module: str, permission: ModulePermission) -> bool:
    return permission in module_permissions_for_role(role, module)


def describe_role_access(role: str | None) -> dict[str, list[str]]:
    return {
        module: sorted(permission.value for permission in module_permissions_for_role(role, module))
        for module in ALL_MODULES
    }
