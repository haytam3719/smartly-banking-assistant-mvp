from app.domain.enums import RouteMode, ToolName
from app.domain.models import RoutingDecision, ToolPlan
from app.orchestration.policies import RoutingPolicy


def test_transfer_without_reference_becomes_clarification() -> None:
    decision = RoutingDecision(
        mode=RouteMode.TOOLS_ONLY,
        tools=[ToolPlan(name=ToolName.GET_TRANSFER_STATUS)],
    )
    validated = RoutingPolicy().validate(decision)
    assert validated.mode == RouteMode.CLARIFY
    assert validated.tools == []


def test_duplicate_tool_calls_are_deduplicated() -> None:
    plan = ToolPlan(name=ToolName.GET_ACCOUNT_BALANCE)
    decision = RoutingDecision(mode=RouteMode.TOOLS_ONLY, tools=[plan, plan])
    validated = RoutingPolicy().validate(decision)
    assert len(validated.tools) == 1


def test_valid_hybrid_transfer_plan() -> None:
    decision = RoutingDecision(
        mode=RouteMode.HYBRID,
        tools=[ToolPlan(name=ToolName.GET_TRANSFER_STATUS, transfer_id="TR4587")],
        rag_query="rejected transfer procedure",
    )
    validated = RoutingPolicy().validate(decision)
    assert validated.mode == RouteMode.HYBRID
