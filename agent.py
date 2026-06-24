"""The agent loop, built directly on the OpenAI SDK — no LangChain or similar framework.

This is the real mechanics of tool-calling + streaming that a framework would normally
hide: we manage the conversation history as a plain list of dicts, manually accumulate
streamed tool-call fragments, execute the tools ourselves, feed results back as "tool"
messages, and re-query the model until it's ready to give a final answer.
"""

import json
import os

from openai import OpenAI

from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a friendly poker assistant. Users will describe a poker situation \
in casual, conversational language — their hole cards, their position at the table, the \
community board if any, and sometimes a pot size or a bet they're facing. Your job is to \
figure out what's being described and help them understand it: what hand they have, their \
odds, and what to consider doing.

You have three tools:
- analyze_hand: current hand strength, outs, and odds to improve. Use whenever a board (or \
no board, for preflop) and hole cards are described and the user wants to know what they have.
- recommend_action: a Fold/Call/Raise recommendation with reasoning. Use postflop when the \
user is facing or considering a betting decision, especially if they mention pot size or a \
bet to call.
- get_preflop_range_advice: standard preflop fold/call/raise/3-bet advice. Use before any \
board cards exist.

Always use a tool for any actual poker math — outs, odds, equity, or range membership. Never \
compute or guess these numbers yourself from memory; you are not reliable at poker arithmetic \
and the tools contain the verified logic. If you're missing information a tool needs (for \
example the user didn't say their position), ask a short clarifying question instead of \
guessing.

After giving any poker advice, end your response with a brief, clear note that this is \
AI-generated advice based on simplified standard ranges (not a perfect solver), and that you \
can make mistakes — so it's a learning aid, not a guaranteed-correct decision. Keep this note \
short, and skip it if the user is just asking a clarifying or unrelated follow-up question \
rather than getting new advice."""


def run_agent_turn(messages: list[dict], _depth: int = 0):
    """Generator that yields text chunks for the model's reply to the latest message in
    `messages`. Mutates `messages` in place — appends whatever the assistant said (and any
    tool-call round trip along the way) so the caller can persist history across turns."""
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    print(f"[agent] depth={_depth} sending {len(full_messages)} messages; last={full_messages[-1]}")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        tools=TOOL_SCHEMAS,
        stream=True,
    )

    content = ""
    tool_call_chunks: dict[int, dict] = {}

    for chunk in stream:
        delta = chunk.choices[0].delta

        if delta.content:
            content += delta.content
            yield delta.content

        # Tool calls also arrive as streamed fragments — the id and the start of the
        # function name show up in the first chunk for that call, then the arguments
        # JSON trickles in piece by piece across subsequent chunks. We have to
        # accumulate them ourselves; nothing hands you the assembled call.
        if delta.tool_calls:
            for tc in delta.tool_calls:
                slot = tool_call_chunks.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    slot["arguments"] += tc.function.arguments

    if not tool_call_chunks:
        # No tool was needed — what already streamed to the user IS the final answer.
        print(f"[agent] depth={_depth} no tool calls, final content={content!r}")
        messages.append({"role": "assistant", "content": content})
        return

    print(f"[agent] depth={_depth} tool_call_chunks={tool_call_chunks}")

    # The model wants tool(s) called. Record exactly what it asked for as an assistant
    # message, in the exact shape the API expects for a tool-calling turn.
    tool_calls_payload = [
        {
            "id": slot["id"],
            "type": "function",
            "function": {"name": slot["name"], "arguments": slot["arguments"]},
        }
        for slot in tool_call_chunks.values()
    ]
    messages.append({
        "role": "assistant",
        "content": content or None,
        "tool_calls": tool_calls_payload,
    })

    yield "\n\n⏳ checking the numbers...\n\n"

    # Actually execute each tool ourselves — this is the one step no API call does for
    # you. The model can only ask; running real Python code is on us.
    for slot in tool_call_chunks.values():
        arguments = json.loads(slot["arguments"]) if slot["arguments"] else {}
        result = TOOL_FUNCTIONS[slot["name"]](**arguments)
        print(f"[agent] depth={_depth} called {slot['name']}({arguments}) -> {result}")
        messages.append({
            "role": "tool",
            "tool_call_id": slot["id"],
            "content": json.dumps(result),
        })

    # Ask again with the tool result(s) now in the conversation. This recursive call
    # streams the model's real answer — and if it decides it needs yet another tool,
    # the same logic handles that round trip too.
    yield from run_agent_turn(messages, _depth=_depth + 1)
