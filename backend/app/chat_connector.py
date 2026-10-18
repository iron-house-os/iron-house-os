"""Private OAuth resource server; never substitutes browser/admin credentials."""

from time import time
from uuid import UUID
from urllib.parse import urlsplit

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import get_settings, validate_production_settings
from app.db.session import SessionLocal
from app.models.user import UserAccount
from app.services.chat_projects import (
    TenderIntake, apply_intake, preview_intake, project_inventory, require_manager,
)


class ConnectorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IHOS_MCP_", extra="ignore")
    enabled: bool = False
    writes_enabled: bool = False
    resource_url: AnyHttpUrl
    issuer_url: AnyHttpUrl
    introspection_url: AnyHttpUrl
    introspection_client_id: str = Field(min_length=1)
    introspection_client_secret: SecretStr
    allowed_client_ids: list[str] = Field(min_length=1)
    subject_accounts: dict[str, UUID] = Field(min_length=1)
    port: int = Field(default=8091, ge=1024, le=65535)

    @model_validator(mode="after")
    def validate_transport(self):
        for url in (self.resource_url, self.issuer_url, self.introspection_url):
            parts = urlsplit(str(url))
            if parts.scheme != "https" or parts.username or parts.password or parts.query or parts.fragment:
                raise ValueError("Connector URLs require clean HTTPS origins/paths")
        if urlsplit(str(self.resource_url)).path != "/mcp":
            raise ValueError("Resource URL must end in /mcp")
        if not self.introspection_client_secret.get_secret_value():
            raise ValueError("Protected introspection credentials are required")
        return self


class IntrospectionVerifier:
    def __init__(self, settings: ConnectorSettings, transport=None):
        self.settings = settings
        self.transport = transport

    async def verify_token(self, token: str) -> AccessToken | None:
        if not self.settings.enabled or not 1 <= len(token) <= 8192:
            return None
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=False, transport=self.transport) as client:
                response = await client.post(str(self.settings.introspection_url),
                    auth=(self.settings.introspection_client_id,
                          self.settings.introspection_client_secret.get_secret_value()),
                    data={"token": token, "token_type_hint": "access_token"})
                response.raise_for_status()
                if len(response.content) > 65536:
                    return None
                claims = response.json()
            if not isinstance(claims, dict) or claims.get("active") is not True:
                return None
            audience = claims.get("aud")
            audiences = audience if isinstance(audience, list) else [audience]
            expires = claims.get("exp")
            if (claims.get("iss") != str(self.settings.issuer_url)
                    or str(self.settings.resource_url) not in audiences
                    or type(expires) is not int or not time() < expires <= time() + 3600
                    or claims.get("client_id") not in self.settings.allowed_client_ids
                    or not isinstance(claims.get("scope"), str)):
                return None
            subject = claims.get("sub")
            if not isinstance(subject, str) or subject not in self.settings.subject_accounts:
                return None
            scopes = claims["scope"].split()
            if "ihos:projects:read" not in scopes:
                return None
            return AccessToken(token=token, client_id=claims["client_id"], subject=subject,
                scopes=scopes, expires_at=expires, resource=str(self.settings.resource_url),
                claims={"account_id": str(self.settings.subject_accounts[subject])})
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return None


def create_connector(settings: ConnectorSettings) -> FastMCP:
    if not settings.enabled:
        raise RuntimeError("IHOS chat connector is disabled")
    validate_production_settings(get_settings())
    origin = urlsplit(str(settings.resource_url))
    server = FastMCP("Iron House OS", host="127.0.0.1", port=settings.port,
        stateless_http=True, json_response=True, max_request_body_size=65536,
        token_verifier=IntrospectionVerifier(settings),
        auth=AuthSettings(issuer_url=settings.issuer_url, resource_server_url=settings.resource_url,
                          required_scopes=["ihos:projects:read"], validate_token_resource=True),
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=[origin.netloc, f"127.0.0.1:{settings.port}"],
            allowed_origins=[f"{origin.scheme}://{origin.netloc}"]))

    def principal(db, *, write=False):
        token = get_access_token()
        if token is None or not token.claims or token.expires_at is None or token.expires_at <= time():
            raise PermissionError("Connect an authorised IHOS account")
        if write and (not settings.writes_enabled or "ihos:projects:write" not in token.scopes):
            raise PermissionError("IHOS project writes are not enabled for this connection")
        account = db.get(UserAccount, UUID(token.claims["account_id"]))
        return require_manager(account)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def connection_status() -> dict:
        """Verify the connected IHOS identity and granted project capabilities."""
        with SessionLocal() as db:
            account = principal(db)
            return {"connected": True, "account_id": str(account.id), "display_name": account.display_name,
                    "role": account.role, "environment": get_settings().environment,
                    "release_id": get_settings().release_id, "writes_enabled": settings.writes_enabled}

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def list_projects(offset: int = 0, limit: int = 50) -> dict:
        """List bounded live IHOS projects including Trash for duplicate reconciliation."""
        with SessionLocal() as db:
            return project_inventory(db, principal(db), offset, limit)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def preview_tender_intake(item: TenderIntake) -> dict:
        """Preview one source-linked tender opportunity. Existing unlinked matches fail for review."""
        with SessionLocal() as db:
            return preview_intake(db, principal(db), item)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                           idempotentHint=True, openWorldHint=False))
    def apply_tender_intake(preview_token: str) -> dict:
        """Apply an authorised, exact 10-minute preview. Creates opportunity only, never award/job number."""
        with SessionLocal() as db:
            return apply_intake(db, principal(db, write=True), preview_token)

    return server


if __name__ == "__main__":
    create_connector(ConnectorSettings()).run(transport="streamable-http")
