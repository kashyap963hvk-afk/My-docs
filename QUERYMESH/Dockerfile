# Two images from one recipe:
#   docker build --target app    -t querymesh:v1 .          (API, 5 agents, Gradio, Telegram)
#   docker build --target ingest -t querymesh-ingest:v1 .   (adds Docling for PDF parsing)
FROM public.ecr.aws/docker/library/python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY pyproject.toml ./
COPY querymesh ./querymesh
RUN uv pip install --system --no-cache .
RUN useradd --create-home appuser
USER appuser
EXPOSE 8090 8101 8102 8103 8104 8105 7860
CMD ["uvicorn", "querymesh.api:app", "--host", "0.0.0.0", "--port", "8090"]

FROM app AS ingest
USER root
RUN uv pip install --system --no-cache torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && uv pip install --system --no-cache ".[ingest]"
USER appuser
CMD ["python", "-m", "querymesh.ingest", "--max-papers", "5"]
