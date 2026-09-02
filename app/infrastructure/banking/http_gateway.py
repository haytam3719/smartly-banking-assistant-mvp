from __future__ import annotations

from time import perf_counter

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.core.request_context import RequestContext
from app.domain.enums import FailureKind, ToolName
from app.domain.models import ToolPlan, ToolResult


class TransientBankingError(Exception):
    pass


class HttpBankingGateway:
    PATHS = {
        ToolName.GET_ACCOUNT_BALANCE: "/v1/customers/{customer_id}/accounts/balance",
        ToolName.GET_TRANSACTIONS: "/v1/customers/{customer_id}/transactions",
        ToolName.GET_CARD_INFO: "/v1/customers/{customer_id}/cards/info",
        ToolName.GET_TRANSFER_STATUS: "/v1/customers/{customer_id}/transfers/{transfer_id}",
        ToolName.GET_CUSTOMER_INFO: "/v1/customers/{customer_id}/profile",
    }

    def __init__(self, *, base_url: str, token: str, timeout_seconds: float) -> None:
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Authorization": f"Bearer {token}"},
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def execute(self, context: RequestContext, plan: ToolPlan) -> ToolResult:
        started = perf_counter()
        try:
            data = await self._request(context, plan)
            return ToolResult(name=plan.name, ok=True, data=data, latency_ms=self._ms(started))
        except httpx.TimeoutException:
            return ToolResult(
                name=plan.name,
                ok=False,
                failure_kind=FailureKind.TIMEOUT,
                safe_error="The banking service did not respond in time.",
                latency_ms=self._ms(started),
            )
        except PermissionError:
            return ToolResult(
                name=plan.name,
                ok=False,
                failure_kind=FailureKind.FORBIDDEN,
                safe_error="The requested resource is not available for this customer.",
                latency_ms=self._ms(started),
            )
        except KeyError:
            return ToolResult(
                name=plan.name,
                ok=False,
                failure_kind=FailureKind.NOT_FOUND,
                safe_error="Requested banking information was not found.",
                latency_ms=self._ms(started),
            )
        except (TransientBankingError, httpx.HTTPError):
            return ToolResult(
                name=plan.name,
                ok=False,
                failure_kind=FailureKind.UPSTREAM,
                safe_error="The banking service is temporarily unavailable.",
                latency_ms=self._ms(started),
            )

    @retry(
        retry=retry_if_exception_type((TransientBankingError, httpx.ConnectError)),
        stop=stop_after_attempt(2),
        wait=wait_exponential_jitter(initial=0.1, max=0.5),
        reraise=True,
    )
    async def _request(self, context: RequestContext, plan: ToolPlan) -> dict[str, object]:
        path = self.PATHS[plan.name].format(
            customer_id=context.customer_id,
            transfer_id=plan.transfer_id or "",
        )
        params: dict[str, str | int] = {}
        if plan.start_date:
            params["start_date"] = plan.start_date.isoformat()
        if plan.end_date:
            params["end_date"] = plan.end_date.isoformat()
        if plan.limit:
            params["limit"] = plan.limit

        response = await self.client.get(
            path,
            params=params,
            headers={"X-Request-ID": context.request_id},
        )
        if response.status_code == 404:
            raise KeyError(path)
        if response.status_code in {401, 403}:
            raise PermissionError(path)
        if 500 <= response.status_code < 600:
            raise TransientBankingError(f"upstream status={response.status_code}")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise httpx.DecodingError("Expected JSON object", request=response.request)
        return payload

    @staticmethod
    def _ms(started: float) -> int:
        return int((perf_counter() - started) * 1000)
