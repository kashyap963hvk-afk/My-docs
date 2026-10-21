"""Small client for the QueryMesh API, shared by the Gradio and Telegram interfaces."""
import json

import httpx

from querymesh import config


def get_token() -> str:
    response = httpx.post(f"{config.API_URL}/token", timeout=30,
                          data={"username": config.API_USERNAME, "password": config.API_PASSWORD})
    response.raise_for_status()
    return response.json()["access_token"]


async def stream_question(question: str, token: str):
    """Yield ('step', text) and finally ('final', dict) from the API's Server-Sent Events."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=600) as http:
        async with http.stream("POST", f"{config.API_URL}/ask/stream",
                               json={"question": question}, headers=headers) as response:
            response.raise_for_status()
            event = "message"
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    event = line[len("event: "):]
                elif line.startswith("data: "):
                    yield event, json.loads(line[len("data: "):])


def format_final(final: dict) -> str:
    sources = "\n".join(f"[{c['n']}] {c['title']} - {c['url']}" for c in final.get("citations", []))
    flag = " (from cache)" if final.get("cached") else ""
    return f"{final.get('answer', '')}\n\nSources{flag}:\n{sources or 'none'}"
