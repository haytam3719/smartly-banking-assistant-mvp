from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core.config import get_settings
from app.infrastructure.llm.openai_adapters import OpenAILLMRouter
from app.orchestration.policies import RoutingPolicy


async def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    router = OpenAILLMRouter(
        model=settings.openai_router_model,
        api_key=settings.openai_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    policy = RoutingPolicy(settings.max_tools_per_request)
    scenarios = json.loads(Path("tests/evals/scenarios.json").read_text(encoding="utf-8"))

    passed = 0
    rows = []
    for item in scenarios:
        decision = policy.validate(await router.route(item["message"]))
        tools = [p.name.value for p in decision.tools]
        ok = decision.mode.value == item["expected_route"] and tools == item["expected_tools"]
        passed += int(ok)
        rows.append({"ok": ok, "message": item["message"], "route": decision.mode.value, "tools": tools})

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\nRouting accuracy: {passed}/{len(scenarios)} = {passed / len(scenarios):.1%}")
    if passed != len(scenarios):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
