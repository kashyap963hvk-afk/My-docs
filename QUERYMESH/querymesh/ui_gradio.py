"""Gradio web chat. Shows each agent step live, then the cited answer."""
import gradio as gr

from querymesh import observability
from querymesh.api_client import format_final, get_token, stream_question

observability.setup("querymesh-gradio")


async def respond(message: str, history: list):
    token = get_token()
    progress = ""
    async for kind, value in stream_question(message, token):
        if kind == "step":
            progress += f"- {value}\n"
            yield f"Working...\n{progress}"
        else:
            yield f"{format_final(value)}\n\nAgent steps:\n{progress}"


demo = gr.ChatInterface(
    fn=respond,
    title="QueryMesh",
    description="Ask a question about recent arXiv papers. Five agents search, grade, write and check.",
    examples=["How does reciprocal rank fusion combine BM25 and vector search?",
              "What are recent methods to reduce hallucination in RAG?"],
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
