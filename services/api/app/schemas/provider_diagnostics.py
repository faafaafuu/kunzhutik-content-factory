from pydantic import BaseModel


class ProviderDiagnostic(BaseModel):
    area: str
    selected_provider: str
    effective_provider: str
    configured: bool
    fallback_enabled: bool
    missing_env: list[str]
    notes: list[str]


class ProviderDiagnosticsResponse(BaseModel):
    providers: list[ProviderDiagnostic]
