"""Tracing: Logfire records spans (who called what, how long); Langfuse records LLM tokens."""
import os

import logfire

_configured = False


def setup(service_name: str, app=None) -> None:
    """Call once at the start of every process (API, each agent, UI)."""
    global _configured
    if not _configured:
        logfire.configure(
            service_name=service_name,
            send_to_logfire="if-token-present",  # no LOGFIRE_TOKEN = tracing stays off, no error
            console=False,
        )
        logfire.instrument_httpx()  # every outgoing HTTP call becomes a span
        # MCP tool calls need nothing extra: the MCP SDK (mcp 2) emits OpenTelemetry spans itself
        _configured = True
    if app is not None:
        logfire.instrument_fastapi(app)  # every incoming request becomes a span


def langfuse_callbacks() -> list:
    """LangChain callback that sends prompts, answers and token counts to Langfuse Cloud."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return []
    from langfuse.langchain import CallbackHandler

    return [CallbackHandler()]
