import pytest

from app.core.config import get_settings
from app.domain.enums import RouteMode, ToolName
from app.infrastructure.llm.openai_adapters import OpenAILLMRouter

pytestmark = [pytest.mark.integration, pytest.mark.live_llm]


@pytest.fixture
def router() -> OpenAILLMRouter:
    settings = get_settings()
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY not configured")
    return OpenAILLMRouter(
        model=settings.openai_router_model,
        api_key=settings.openai_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )


@pytest.mark.parametrize(
    ("message", "mode", "tool"),
    [
        ("Quel est mon solde ?", RouteMode.TOOLS_ONLY, ToolName.GET_ACCOUNT_BALANCE),
        ("Affiche mes dernières transactions.", RouteMode.TOOLS_ONLY, ToolName.GET_TRANSACTIONS),
        ("Quels sont les frais d'un virement vers l'étranger ?", RouteMode.RAG_ONLY, None),
        ("Quel est mon plafond de carte ?", RouteMode.TOOLS_ONLY, ToolName.GET_CARD_INFO),
        ("Mon virement TR4587 a été refusé. Pourquoi et que dois-je faire ?", RouteMode.HYBRID, ToolName.GET_TRANSFER_STATUS),
    ],
)
async def test_challenge_routing(router: OpenAILLMRouter, message: str, mode: RouteMode, tool: ToolName | None) -> None:
    decision = await router.route(message)
    assert decision.mode == mode
    if tool is not None:
        assert tool in [plan.name for plan in decision.tools]
