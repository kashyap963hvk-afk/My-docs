"""The QueryMesh API: login, ask a question, or ask and stream the agents' progress."""
import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from querymesh import cache, observability
from querymesh.auth import check_password, create_token, current_user
from querymesh.graph import stream_answer

app = FastAPI(title="QueryMesh API", version="1.0.0")
observability.setup("querymesh-api", app)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends()) -> dict:
    if not check_password(form.username, form.password):
        raise HTTPException(401, "wrong username or password")
    return {"access_token": create_token(form.username), "token_type": "bearer"}


@app.post("/ask")
async def ask(body: Question, user: str = Depends(current_user)) -> dict:
    cached = cache.get(body.question)
    if cached:
        return {**cached, "cached": True}
    final: dict = {}
    async for kind, value in stream_answer(body.question):
        if kind == "final":
            final = value
    cache.put(body.question, final)
    return {**final, "cached": False}


@app.post("/ask/stream")
async def ask_stream(body: Question, user: str = Depends(current_user)) -> StreamingResponse:
    """Server-Sent Events: one 'step' event per agent action, then one 'final' event."""

    async def events():
        cached = cache.get(body.question)
        if cached:
            yield f"event: final\ndata: {json.dumps({**cached, 'cached': True})}\n\n"
            return
        async for kind, value in stream_answer(body.question):
            if kind == "final":
                cache.put(body.question, value)
                value = {**value, "cached": False}
            yield f"event: {kind}\ndata: {json.dumps(value)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

