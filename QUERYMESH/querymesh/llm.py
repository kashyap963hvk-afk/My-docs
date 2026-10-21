"""One place that creates the chat model client (vLLM speaks the OpenAI API)."""
from langchain_openai import ChatOpenAI

from querymesh import config
from querymesh.observability import langfuse_callbacks


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL,
        temperature=temperature,
        max_tokens=1024,
        timeout=120,
        callbacks=langfuse_callbacks(),
    )


if __name__ == "__main__":
    print(get_llm().invoke("In one sentence, what is arXiv?").content)
