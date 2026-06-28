# Poker Chat Agent

A conversational agent for poker hand analysis. Describe your cards, position, and the board
in plain language; the agent figures out what's being asked, calls the right tool to get the
real poker math, and explains it back to you conversationally.

Built directly on the OpenAI SDK — **no LangChain or other agent framework**. The conversation
loop, tool-call handling, and streaming are all plain Python, so the actual mechanics are
visible rather than hidden behind a framework's abstractions.

## How it works

1. **Tools, not memorized math.** The model never computes outs, odds, or pot odds itself —
   it only decides *which* tool to call and *what arguments* to pass, based on what the user
   described. Three tools, each wrapping already-tested logic from the hand-analyzer and
   position-trainer projects:
   - `analyze_hand` — current hand strength, outs, chance to improve
   - `recommend_action` — Fold/Call/Raise recommendation with reasoning
   - `get_preflop_range_advice` — preflop Fold/Call/Raise/3-bet advice
2. **Manual tool-calling loop.** When the model requests a tool, we accumulate the streamed
   tool-call fragments ourselves, run the actual Python function, feed the result back as a
   `tool` message, and ask the model again for a natural-language answer. See `agent.py`.
3. **System prompt enforces a standing disclaimer.** The system prompt instructs the model to
   end any advice with a note that it's AI-generated and can be wrong — and because the system
   prompt is resent with every API call, this isn't a one-time reminder, it's enforced for the
   whole conversation.
4. **Real token streaming.** Both the OpenAI call (`stream=True`) and the FastAPI response are
   streamed end-to-end, so the browser shows text appearing incrementally rather than the full
   reply popping in at once.
5. **Photo input, two models.** You can attach one or more photos (e.g. a separate hand photo
   and table photo) instead of typing it out. Any turn with an image attached automatically
   switches from `gpt-4o-mini` to the full `gpt-4o` for that turn — vision needs more care than
   plain text, since misreading even one card's rank or suit from a photo would throw off the
   entire analysis. Each image is downscaled client-side before upload to keep payloads and
   cost down, processed one at a time rather than in parallel (concurrent canvas decoding
   turned out to have a real race condition that occasionally produced a broken, empty image).
   See `agent.py`'s `_has_image()` / `VISION_MODEL` and `static/index.html`'s
   `downscaleImage()` / `handleImageSelect()`.
6. **Asks instead of guessing.** If a tool needs something the user hasn't said yet (pot size,
   bet to call, table position, or even a card that isn't clearly visible in a photo), the
   system prompt requires asking a specific clarifying question rather than calling the tool
   with a guessed argument or giving a vague, numberless answer.

## Project layout

| File | Purpose |
|---|---|
| `cards.py`, `evaluator.py`, `analyzer.py` | Hand evaluation, outs, pot odds (from poker_hand_analyzer) |
| `positions.py`, `ranges.py`, `explanations.py` | Position tiers, preflop ranges (from poker_position_trainer) |
| `tools.py` | The 3 tool functions + their OpenAI function-calling schemas |
| `agent.py` | The manual conversation + tool-calling + streaming loop |
| `api.py` | FastAPI HTTP wrapper, serves the chat UI |
| `static/index.html` | Chat UI, with a dropdown "quick picker" to build messages |

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file (never committed — see `.gitignore`):

```
OPENAI_API_KEY=sk-your-key-here
```

## Usage

```bash
python -m uvicorn api:app --reload
```

Open `http://127.0.0.1:8000`.

### Docker

```bash
docker build -t poker-chat-agent .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-your-key-here poker-chat-agent
```

## Cost note

This calls the OpenAI API (`gpt-4o-mini`) using a real API key, so every message costs a small
amount of real money. If deployed publicly, anyone with the link can use your key's credit —
consider a hard spending limit under platform.openai.com → Settings → Billing → Limits.
