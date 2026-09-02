from __future__ import annotations

from datetime import date
from time import perf_counter

from app.core.request_context import RequestContext
from app.domain.enums import FailureKind, ToolName
from app.domain.models import ToolPlan, ToolResult

ACCOUNTS = {
    "C1024": {"available_balance": 12840.55, "currency": "MAD", "account_type": "CURRENT"},
    "C2048": {"available_balance": 950.00, "currency": "EUR", "account_type": "CURRENT"},
}

CARDS = {
    "C1024": {
        "card_type": "GOLD",
        "status": "ACTIVE",
        "expiry_date": "2028-09",
        "payment_limit": 20000.0,
        "amount_used": 6500.0,
        "currency": "MAD",
    }
}

TRANSFERS = {
    "TR4587": {
        "customer_id": "C1024",
        "amount": 1000.0,
        "currency": "EUR",
        "beneficiary": "Demo Beneficiary",
        "date": "2026-08-27",
        "status": "REJECTED",
        "rejection_reason": "PAYMENT_LIMIT_EXCEEDED",
    },
    "TR9001": {
        "customer_id": "C1024",
        "amount": 250.0,
        "currency": "MAD",
        "beneficiary": "Demo Merchant",
        "date": "2026-08-29",
        "status": "PENDING",
        "rejection_reason": None,
    },
}

TRANSACTIONS = {
    "C1024": [
        {"id": "TX1", "date": "2026-08-29", "amount": -180.0, "currency": "MAD", "label": "GROCERY"},
        {"id": "TX2", "date": "2026-08-28", "amount": -75.0, "currency": "MAD", "label": "TRANSPORT"},
        {"id": "TX3", "date": "2026-08-27", "amount": 4500.0, "currency": "MAD", "label": "TRANSFER_IN"},
    ]
}

CUSTOMERS = {
    "C1024": {"segment": "RETAIL", "country": "MA", "preferred_language": "fr"}
}


class MockBankingGateway:
    async def execute(self, context: RequestContext, plan: ToolPlan) -> ToolResult:
        started = perf_counter()
        try:
            data = self._execute(context, plan)
            return ToolResult(
                name=plan.name,
                ok=True,
                data=data,
                latency_ms=int((perf_counter() - started) * 1000),
            )
        except KeyError:
            return ToolResult(
                name=plan.name,
                ok=False,
                failure_kind=FailureKind.NOT_FOUND,
                safe_error="Requested banking information was not found.",
                latency_ms=int((perf_counter() - started) * 1000),
            )
        except PermissionError:
            return ToolResult(
                name=plan.name,
                ok=False,
                failure_kind=FailureKind.FORBIDDEN,
                safe_error="The requested resource is not available for this customer.",
                latency_ms=int((perf_counter() - started) * 1000),
            )

    def _execute(self, context: RequestContext, plan: ToolPlan) -> dict[str, object]:
        customer_id = context.customer_id
        if plan.name == ToolName.GET_ACCOUNT_BALANCE:
            return dict(ACCOUNTS[customer_id])
        if plan.name == ToolName.GET_CARD_INFO:
            return dict(CARDS[customer_id])
        if plan.name == ToolName.GET_CUSTOMER_INFO:
            return dict(CUSTOMERS[customer_id])
        if plan.name == ToolName.GET_TRANSFER_STATUS:
            transfer = TRANSFERS[plan.transfer_id or ""]
            if transfer["customer_id"] != customer_id:
                raise PermissionError
            return {k: v for k, v in transfer.items() if k != "customer_id"}
        if plan.name == ToolName.GET_TRANSACTIONS:
            txs = list(TRANSACTIONS[customer_id])
            if plan.start_date:
                txs = [t for t in txs if date.fromisoformat(str(t["date"])) >= plan.start_date]
            if plan.end_date:
                txs = [t for t in txs if date.fromisoformat(str(t["date"])) <= plan.end_date]
            if plan.limit:
                txs = txs[: plan.limit]
            return {"transactions": txs}
        raise KeyError(plan.name)
