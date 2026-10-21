"""The five agent servers. Each one exposes the same skill twice:
  - as an MCP tool over SSE at /mcp/sse        (the supervisor calls it)
  - as an A2A agent at /a2a + an Agent Card     (other agents discover it and delegate to it)
Run one with:  python -m querymesh.agents retriever
"""
import asyncio
import json
import os
import sys

import uvicorn
from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from querymesh import config, observability, skills
from querymesh.discovery import delegate, find_peer

PEER_MIN_HITS = 3  # fewer hits than this -> the retriever asks the scout for help


# ---------- the tools (async wrappers so slow work does not block the server) ----------
async def retrieve(query: str, k: int = 8) -> list[dict]:
    """Hybrid search over indexed arXiv chunks."""
    hits = await asyncio.to_thread(skills.retrieve, query, k)
    if len(hits) < PEER_MIN_HITS:
        scout_url = await find_peer(config.AGENT_URLS, "scout")  # agent discovery
        if scout_url:
            await delegate(scout_url, {"topic": query, "max_papers": 5})  # A2A peer delegation
            hits = await asyncio.to_thread(skills.retrieve, query, k)
    return hits


async def grade(question: str, chunks: list[dict]) -> list[dict]:
    """Keep only the chunks that help answer the question."""
    return await asyncio.to_thread(skills.grade, question, chunks)


async def write(question: str, chunks: list[dict], feedback: str = "") -> dict:
    """Write a cited answer from the chunks."""
    return await asyncio.to_thread(skills.write, question, chunks, feedback)


async def critic(question: str, answer: str, chunks: list[dict]) -> dict:
    """Check that the answer is supported by the chunks."""
    return await asyncio.to_thread(skills.critic, question, answer, chunks)


async def scout(topic: str, max_papers: int = 5) -> dict:
    """Fetch fresh arXiv papers on a topic and index their abstracts."""
    return await asyncio.to_thread(skills.scout, topic, max_papers)


AGENTS = {
    "retriever": {"port": 8101, "tool": retrieve, "about": "Finds arXiv passages with hybrid search"},
    "grader": {"port": 8102, "tool": grade, "about": "Grades passages for relevance"},
    "writer": {"port": 8103, "tool": write, "about": "Writes cited answers"},
    "critic": {"port": 8104, "tool": critic, "about": "Checks answers for hallucinations"},
    "scout": {"port": 8105, "tool": scout, "about": "Fetches fresh papers from arXiv"},
}


# ---------- A2A: how a peer agent's request is executed ----------
class SkillExecutor(AgentExecutor):
    """Reads the A2A message as JSON arguments, runs the tool, returns the JSON result."""

    def __init__(self, tool):
        self.tool = tool

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        arguments = json.loads(get_message_text(context.message) or "{}")
        result = await self.tool(**arguments)
        await updater.add_artifact(parts=[new_text_part(text=json.dumps(result), media_type="application/json")])
        await updater.update_status(state=TaskState.TASK_STATE_COMPLETED, message=new_text_message("done"))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported")


# ---------- build one agent server ----------
def build_app(name: str) -> Starlette:
    spec = AGENTS[name]
    skill_id = spec["tool"].__name__
    public_url = os.getenv("PUBLIC_URL", f"http://localhost:{spec['port']}")

    mcp = FastMCP(f"querymesh-{name}")
    mcp.tool(spec["tool"])
    mcp_app = mcp.http_app(transport="sse", path="/sse")

    card = AgentCard(
        name=f"querymesh-{name}",
        description=spec["about"],
        version="1.0.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[AgentInterface(protocol_binding="JSONRPC", url=f"{public_url}/a2a", protocol_version="1.0")],
        skills=[AgentSkill(id=skill_id, name=skill_id, description=spec["about"], tags=["querymesh"])],
    )
    handler = DefaultRequestHandler(agent_executor=SkillExecutor(spec["tool"]),
                                    task_store=InMemoryTaskStore(), agent_card=card)

    async def healthz(request):
        return JSONResponse({"status": "ok", "agent": name})

    routes = [
        Route("/healthz", healthz),
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, "/a2a"),
        Mount("/mcp", app=mcp_app),
    ]
    return Starlette(routes=routes, lifespan=mcp_app.lifespan)


if __name__ == "__main__":
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "retriever"
    observability.setup(f"querymesh-{agent_name}")
    port = int(os.getenv("PORT", AGENTS[agent_name]["port"]))
    uvicorn.run(build_app(agent_name), host="0.0.0.0", port=port)
