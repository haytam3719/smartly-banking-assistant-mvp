import pytest

from app.core.request_context import RequestContext
from app.domain.enums import FailureKind, ToolName
from app.domain.models import ToolPlan
from app.infrastructure.banking.mock_gateway import MockBankingGateway


@pytest.mark.asyncio
async def test_transfer_is_customer_scoped() -> None:
    gateway = MockBankingGateway()
    context = RequestContext(request_id="r1", customer_id="C2048", conversation_id="c1")
    result = await gateway.execute(
        context,
        ToolPlan(name=ToolName.GET_TRANSFER_STATUS, transfer_id="TR4587"),
    )
    assert result.ok is False
    assert result.failure_kind == FailureKind.FORBIDDEN


@pytest.mark.asyncio
async def test_account_balance_success() -> None:
    gateway = MockBankingGateway()
    context = RequestContext(request_id="r1", customer_id="C1024", conversation_id="c1")
    result = await gateway.execute(context, ToolPlan(name=ToolName.GET_ACCOUNT_BALANCE))
    assert result.ok is True
    assert result.data is not None
    assert result.data["currency"] == "MAD"
