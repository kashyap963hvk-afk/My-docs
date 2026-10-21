"""The supervisor-worker graph: one supervisor routes the question through five agents."""
import asyncio
import json
import operator
import sys
from typing import Annotated, TypedDict

import logfire
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from querymesh import config, skills


class QueryState(TypedDict, total=False):
    """The shared notebook every agent reads from and writes to."""
    question: str
    search_query: str
    chunks: list[dict]
    relevant: list[dict] | None
    answer: str | None
    citations: list[dict]
    grounded: bool | None
    feedback: str
    retrieval_attempts: int
    generation_attempts: int
    scouted: bool
    steps: Annotated[list[str], operator.add]  # every agent appends a line; nothing is lost


# ---------- how the supervisor reaches an agent ----------
LOCAL_SKILLS = {
    "retrieve": skills.retrieve,
    "grade": skills.grade,
    "write": skills.write,
    "critic": skills.critic,
    "scout": skills.scout,
}
_registry: dict[str, str] = {}  # skill name -> MCP URL, filled by agent discovery


async def call_skill(name: str, **kwargs):
    """local mode: run the Python function. remote mode: call the agent's MCP tool over SSE."""
    with logfire.span("agent call {name}", name=name, mode=config.WORKER_MODE):
        if config.WORKER_MODE == "local":
            return await asyncio.to_thread(LOCAL_SKILLS[name], **kwargs)
        from fastmcp import Client

        from querymesh.discovery import discover_agents

        if not _registry:
            _registry.update(await discover_agents(config.AGENT_URLS))
        async with Client(_registry[name], timeout=300) as mcp:
            result = await mcp.call_tool(name, kwargs)
        return result.data if result.data is not None else json.loads(result.content[0].text)


# ---------- the supervisor ----------
def supervisor(state: QueryState) -> Command:
    """Read the notebook and decide which agent works next (or finish)."""
    if state.get("retrieval_attempts", 0) == 0:
        return Command(goto="retriever", update={"search_query": state["question"]})

    if state.get("answer") is None:
        if state.get("relevant") is None:
            return Command(goto="grader")
        if len(state["relevant"]) >= config.MIN_RELEVANT:
            return Command(goto="writer")
        if state["retrieval_attempts"] < config.MAX_RETRIEVALS:
            better = skills.rewrite_query(state["question"], state["search_query"])
            return Command(goto="retriever", update={
                "search_query": better, "steps": [f"supervisor: search again with '{better}'"]})
        if not state.get("scouted"):
            return Command(goto="scout")
        return Command(goto="writer")  # write with what we have; the writer says what is missing

    if state.get("grounded") is None:
        return Command(goto="critic")
    if not state["grounded"] and state["generation_attempts"] < config.MAX_GENERATIONS:
        return Command(goto="writer")
    return Command(goto=END)


# ---------- the five workers ----------
async def retriever(state: QueryState) -> dict:
    chunks = await call_skill("retrieve", query=state["search_query"], k=config.TOP_K)
    attempts = state.get("retrieval_attempts", 0) + 1
    return {"chunks": chunks, "relevant": None, "retrieval_attempts": attempts,
            "steps": [f"retriever: {len(chunks)} chunks (attempt {attempts})"]}


async def grader(state: QueryState) -> dict:
    relevant = await call_skill("grade", question=state["question"], chunks=state["chunks"])
    return {"relevant": relevant,
            "steps": [f"grader: {len(relevant)} of {len(state['chunks'])} chunks are relevant"]}


async def writer(state: QueryState) -> dict:
    chunks = state.get("relevant") or state.get("chunks", [])
    result = await call_skill("write", question=state["question"], chunks=chunks,
                              feedback=state.get("feedback", ""))
    attempts = state.get("generation_attempts", 0) + 1
    return {"answer": result["answer"], "citations": result["citations"], "grounded": None,
            "generation_attempts": attempts, "steps": [f"writer: answer drafted (attempt {attempts})"]}


async def critic(state: QueryState) -> dict:
    chunks = state.get("relevant") or state.get("chunks", [])
    verdict = await call_skill("critic", question=state["question"], answer=state["answer"],
                               chunks=chunks)
    return {"grounded": verdict["grounded"], "feedback": verdict["feedback"],
            "steps": [f"critic: grounded={verdict['grounded']}"]}


async def scout(state: QueryState) -> dict:
    result = await call_skill("scout", topic=state["question"], max_papers=5)
    return {"scouted": True, "retrieval_attempts": 0, "chunks": [], "relevant": None,
            "steps": [f"scout: added {len(result['added'])} new papers from arXiv"]}


# ---------- wire it together ----------
def build_graph():
    builder = StateGraph(QueryState)
    builder.add_node("supervisor", supervisor, destinations=("retriever", "grader", "writer", "critic", "scout", END))
    for name, node in [("retriever", retriever), ("grader", grader), ("writer", writer),
                       ("critic", critic), ("scout", scout)]:
        builder.add_node(name, node)
        builder.add_edge(name, "supervisor")  # every worker reports back to the supervisor
    builder.add_edge(START, "supervisor")
    return builder.compile()


graph = build_graph()


async def stream_answer(question: str):
    """Yield ('step', text) while the agents work, then ('final', result_dict)."""
    state: dict = {"question": question}
    async for update in graph.astream(state, stream_mode="updates", config={"recursion_limit": 40}):
        for node, change in update.items():
            if not change:
                continue
            state.update({k: v for k, v in change.items() if k != "steps"})
            for line in change.get("steps", []):
                yield "step", line
    yield "final", {"answer": state.get("answer", ""), "citations": state.get("citations", []),
                    "grounded": state.get("grounded")}


async def ask(question: str) -> dict:
    final = {}
    async for kind, value in stream_answer(question):
        if kind == "step":
            print("  ..", value)
        else:
            final = value
    return final


if __name__ == "__main__":
    result = asyncio.run(ask(" ".join(sys.argv[1:]) or "How does reciprocal rank fusion work?"))
    print("\n" + result["answer"] + "\n")
    for c in result["citations"]:
        print(f"[{c['n']}] {c['title']}  {c['url']}")
