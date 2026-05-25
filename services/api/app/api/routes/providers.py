from fastapi import APIRouter, Depends

from app.api.deps import require_operator
from app.models.operator_user import OperatorUser
from app.schemas.provider_diagnostics import ProviderDiagnosticsResponse
from app.services.provider_diagnostics import get_provider_diagnostics

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/diagnostics", response_model=ProviderDiagnosticsResponse)
def diagnostics(user: OperatorUser = Depends(require_operator)) -> ProviderDiagnosticsResponse:
    return ProviderDiagnosticsResponse(providers=get_provider_diagnostics())
