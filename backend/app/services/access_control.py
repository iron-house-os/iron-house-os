from enum import StrEnum
from uuid import UUID

from app.services.document_audit_access import normalize_role


class ModulePermission(StrEnum):
    READ = "read"
    WRITE = "write"
    ADMINISTER = "administer"


BUSINESS_MODULES = (
    "iron-house-chat",
    "backups",
    "meeting-minutes",
    "google-calendar",
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
    "daily-timesheets",
    "employee-onboarding",
    "finance",
    "media",
    "workflow-drafts",
)
ALL_MODULES = (*BUSINESS_MODULES, "users", "operations")

ESTIMATOR_WRITE_MODULES = frozenset(
    {
        "projects",
        "backups",
        "media",
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
        "workflow-drafts",
    }
)


def module_permissions_for_role(role: str | None, module: str) -> frozenset[ModulePermission]:
    normalized_role = normalize_role(role)
    if module not in ALL_MODULES:
        return frozenset()
    if module in {
        "finance",
        "iron-house-chat",
        "meeting-minutes",
        "google-calendar",
        "employee-onboarding",
    } and normalized_role not in {
        "admin",
        "operations_manager",
    }:
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
        if module in {"field-operations", "daily-timesheets"}:
            permissions.add(ModulePermission.WRITE)
        if module in {"media", "backups", "workflow-drafts"}:
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


def can_access_employee_receipt_route(
    role: str | None,
    module: str,
    method: str,
    relative_path: list[str],
) -> bool:
    """Allow employee receipt intake without opening the rest of finance."""
    if normalize_role(role) != "viewer" or module != "finance" or not relative_path:
        return False

    normalized_method = method.upper()
    if relative_path == ["receipts"]:
        return normalized_method in {"GET", "POST"}
    if relative_path == ["receipts", "extract"]:
        return normalized_method == "POST"
    if len(relative_path) not in {2, 3} or relative_path[0] != "receipts":
        return False
    try:
        UUID(relative_path[1])
    except ValueError:
        return False
    if len(relative_path) == 2:
        return normalized_method in {"GET", "PUT"}
    return relative_path[2] == "submit" and normalized_method == "POST"


def describe_role_access(role: str | None) -> dict[str, list[str]]:
    return {
        module: sorted(permission.value for permission in module_permissions_for_role(role, module))
        for module in ALL_MODULES
    }
