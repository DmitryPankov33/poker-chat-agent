"""The three tools the chat agent can call. Each wraps existing, already-tested poker logic
from the hand-analyzer and position-trainer projects — the agent's job is to figure out
which tool applies and turn natural language into the right arguments, never to do the
poker math itself.

Each tool function returns a plain JSON-serializable dict, and never raises — errors come
back as {"error": "..."} so the model can explain the problem to the user instead of the
whole request crashing.
"""

from analyzer import analyze
from cards import hand_notation, parse_card
from positions import raiser_bucket
from ranges import OPENING_RANGES, FACING_RAISE

POSITION_TIERS = ["Early", "Middle", "Late", "BTN", "SB", "BB"]
_ORDER = {tier: i for i, tier in enumerate(POSITION_TIERS)}

CARD_DESCRIPTION = (
    "Each card as rank+suit, e.g. 'Ah' for Ace of hearts, 'Td' for Ten of diamonds. "
    "Ranks: 2-9, T, J, Q, K, A. Suits: s (spades), h (hearts), d (diamonds), c (clubs)."
)
POSITION_DESCRIPTION = (
    "Bucket the player's seat into one of six tiers: 'Early' (UTG/UTG+1/UTG+2), "
    "'Middle' (MP/HJ), 'Late' (CO), 'BTN' (Button), 'SB' (Small Blind), 'BB' (Big Blind)."
)


def analyze_hand_tool(hole_cards: list[str], board: list[str] | None = None) -> dict:
    """Current hand strength, outs, and chance to improve. No betting context needed."""
    try:
        result = analyze(hole_cards, board or [])
    except ValueError as e:
        return {"error": str(e)}
    return {
        "current_hand": result["current_hand"],
        "hand_strength": result["hand_strength"],
        "outs": result["outs"],
        "out_cards": result["out_cards"],
        "improve_chance": result["improve_chance"],
    }


def recommend_action_tool(hole_cards: list[str], board: list[str] | None = None,
                           pot_size: float | None = None, bet_to_call: float | None = None,
                           num_opponents: int = 1) -> dict:
    """Fold/Call/Raise/Check recommendation with reasoning. Use when there's a board and the
    user is facing (or considering making) a betting decision."""
    try:
        result = analyze(hole_cards, board or [], pot_size, bet_to_call, num_opponents)
    except ValueError as e:
        return {"error": str(e)}
    return result["recommendation"]


def get_preflop_range_advice_tool(hole_cards: list[str], hero_position: str,
                                   raiser_position: str | None = None) -> dict:
    """Standard preflop opening or facing-a-raise advice, before any board cards exist."""
    if hero_position not in POSITION_TIERS:
        return {"error": f"hero_position must be one of {POSITION_TIERS}"}
    try:
        notation = hand_notation(*hole_cards)
    except ValueError as e:
        return {"error": str(e)}

    if raiser_position is None:
        if hero_position == "BB":
            return {"error": "BB never has an 'opening' decision — there's always a raiser to consider, or everyone folded and you win the blinds automatically."}
        in_range = notation in OPENING_RANGES[hero_position]
        return {
            "hand": notation,
            "recommended_action": "Raise" if in_range else "Fold",
            "context": f"opening from {hero_position} (everyone before you folded)",
        }

    if raiser_position not in POSITION_TIERS:
        return {"error": f"raiser_position must be one of {POSITION_TIERS}"}
    if _ORDER[raiser_position] >= _ORDER[hero_position]:
        return {"error": f"{raiser_position} acts after {hero_position} preflop, so they can't have raised before you — check the positions."}

    bucket = raiser_bucket(raiser_position)
    chart = FACING_RAISE[(hero_position, bucket)]
    if notation in chart["3bet"]:
        action = "3bet"
    elif notation in chart["call"]:
        action = "Call"
    else:
        action = "Fold"
    return {
        "hand": notation,
        "recommended_action": action,
        "context": f"facing a raise from {raiser_position} position",
    }


TOOL_FUNCTIONS = {
    "analyze_hand": analyze_hand_tool,
    "recommend_action": recommend_action_tool,
    "get_preflop_range_advice": get_preflop_range_advice_tool,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_hand",
            "description": (
                "Get the current best hand, outs, and chance to improve, given hole cards "
                "and the community board. Use this whenever the user describes their cards "
                "and a board (or no board, for preflop) and wants to know what they have."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hole_cards": {
                        "type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2,
                        "description": f"The player's two hole cards. {CARD_DESCRIPTION}",
                    },
                    "board": {
                        "type": "array", "items": {"type": "string"},
                        "description": f"Community cards, 0/3/4/5 of them. {CARD_DESCRIPTION}",
                    },
                },
                "required": ["hole_cards"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_action",
            "description": (
                "Get a Fold/Call/Raise/Check recommendation with reasoning, given hole cards, "
                "the board, and optionally the pot size and bet to call. Use this when the "
                "user is facing a betting decision postflop, especially if they mention a bet "
                "or pot size."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hole_cards": {
                        "type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2,
                        "description": f"The player's two hole cards. {CARD_DESCRIPTION}",
                    },
                    "board": {
                        "type": "array", "items": {"type": "string"},
                        "description": f"Community cards, 3/4/5 of them. {CARD_DESCRIPTION}",
                    },
                    "pot_size": {"type": "number", "description": "Current pot size, if known."},
                    "bet_to_call": {"type": "number", "description": "Amount the player needs to call, if known."},
                    "num_opponents": {"type": "integer", "description": "How many opponents are still in the hand. Defaults to 1 (heads-up)."},
                },
                "required": ["hole_cards"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_preflop_range_advice",
            "description": (
                "Get standard preflop Fold/Call/Raise/3-bet advice, before any board cards "
                "exist. Use this when the action is still preflop."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hole_cards": {
                        "type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2,
                        "description": f"The player's two hole cards. {CARD_DESCRIPTION}",
                    },
                    "hero_position": {
                        "type": "string", "enum": POSITION_TIERS,
                        "description": f"The player's own seat. {POSITION_DESCRIPTION}",
                    },
                    "raiser_position": {
                        "type": "string", "enum": POSITION_TIERS,
                        "description": (
                            "The seat of the player who raised before the hero, if anyone did. "
                            f"Omit entirely if no one has raised yet. {POSITION_DESCRIPTION}"
                        ),
                    },
                },
                "required": ["hole_cards", "hero_position"],
            },
        },
    },
]
