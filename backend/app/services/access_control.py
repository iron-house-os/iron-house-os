from enum import StrEnum

from app.services.document_audit_access import normalize_role


class ModulePermission(StrEnum):
    READ = "read"
    WRITE = "write"
    ADMINISTER = "administer"


BUSINESS_MODULES = (
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
)
ALL_MODULES = (*BUSINESS_MODULES, "users")

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
    if normalized_role == "admin":
        permissions = {ModulePermission.READ, ModulePermission.WRITE}
        if module == "users":
            permissions.add(ModulePermission.ADMINISTER)
        return frozenset(permissions)
    if module == "users":
        return frozenset()
    if normalized_role == "operations_manager":
        return frozenset({ModulePermission.READ, ModulePermission.WRITE})
    if normalized_role == "estimator":
        permissions = {ModulePermission.READ}
        if module in ESTIMATOR_WRITE_MODULES:
            permissions.add(ModulePermission.WRITE)
        return frozenset(permissions)
    if normalized_role == "viewer":
        return frozenset({ModulePermission.READ})
    return frozenset()


def required_permission(module: str, method: str) -> ModulePermission:
    if module == "users":
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
