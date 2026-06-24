"""HTTP API for the poker chat agent.

Run locally:
    python -m uvicorn api:app --reload

Open http://127.0.0.1:8000 for the chat UI.
"""

from dotenv import load_dotenv
load_dotenv()  # must run before agent.py is imported, since it reads OPENAI_API_KEY at import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import run_agent_turn

app = FastAPI(title="Poker Chat Agent")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]  # full visible conversation so far, including the new user message


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest):
    # The server is stateless: it takes the conversation as given, runs one turn, and
    # streams the reply. It's the client's job to append that reply and resend the whole
    # history next time — the server never stores anything between requests.
    messages = [m.model_dump() for m in request.messages]

    def event_stream():
        for chunk in run_agent_turn(messages):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/plain")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
