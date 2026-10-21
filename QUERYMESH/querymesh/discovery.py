"""A2A helpers: discover agents from their Agent Cards, and delegate work to a peer agent."""
import json

import httpx
from a2a.client import A2ACardResolver, AgentCardResolutionError, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest


async def fetch_card(base_url: str):
    """Download http://agent/.well-known/agent-card.json (the agent's business card)."""
    async with httpx.AsyncClient(timeout=10) as http:
        return await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()


async def discover_agents(base_urls: list[str]) -> dict[str, str]:
    """Return {skill id: MCP SSE URL} for every agent that answers."""
    registry = {}
    for base_url in base_urls:
        card = await fetch_card(base_url)
        for skill in card.skills:
            registry[skill.id] = base_url.rstrip("/") + "/mcp/sse"
    return registry


async def find_peer(base_urls: list[str], skill_id: str) -> str | None:
    """Find the base URL of the agent that offers skill_id (e.g. 'scout')."""
    for base_url in base_urls:
        try:
            card = await fetch_card(base_url)
        except AgentCardResolutionError:  # that agent is down or not an A2A agent: skip it
            continue
        if any(skill.id == skill_id for skill in card.skills):
            return base_url
    return None


async def delegate(base_url: str, payload: dict) -> dict:
    """Send a task to a peer agent over A2A and return its JSON result."""
    card = await fetch_card(base_url)
    client = await create_client(agent=card, client_config=ClientConfig(streaming=False))
    request = SendMessageRequest(message=new_text_message(json.dumps(payload), role=Role.ROLE_USER))
    result: dict = {}
    try:
        async for response in client.send_message(request):
            if response.HasField("task") and response.task.artifacts:
                result = json.loads(response.task.artifacts[0].parts[0].text)
    finally:
        await client.close()
    return result
