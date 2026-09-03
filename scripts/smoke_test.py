import asyncio
import json

import httpx


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30) as client:
        payload = {
            "customer_id": "C1024",
            "conversation_id": "smoke-001",
            "message": "Quel est le statut de mon virement TR4587 ?",
        }
        response = await client.post("/api/v1/chat", json=payload)
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
