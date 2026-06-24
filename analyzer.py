"""Core analysis: combine evaluator + outs + odds into one JSON-friendly result."""

from collections import Counter

from cards import parse_card, remaining_deck, validate_cards
from evaluator import best_hand, hand_name


MEANINGFUL_IMPROVEMENT = 3  # two pair or better — a single pair alone isn't counted as an "out"


def board_danger_signals(board: list[str]) -> list[tuple[str, str]]:
    """Surface-level board texture warnings (no opponent modeling): paired boards can mean
    full houses/quads, 3+ of a suit can mean a flush is out there, 3 ranks within a tight
    span can mean a straight is out there. Returns (type, message) pairs so callers can
    decide which warnings are actually still relevant given their own hand."""
    if len(board) < 3:
        return []

    parsed = [parse_card(c) for c in board]
    ranks = [r for r, _ in parsed]
    suits = [s for _, s in parsed]
    signals = []

    if max(Counter(ranks).values()) >= 2:
        signals.append(("paired", "the board is paired - a full house or quads is possible"))
    if max(Counter(suits).values()) >= 3:
        signals.append(("flush_suit", "3+ cards of one suit are on the board - a flush is possible"))

    unique_ranks = sorted(set(ranks))
    for i in range(len(unique_ranks) - 2):
        if unique_ranks[i + 2] - unique_ranks[i] <= 4:
            signals.append(("connected", "the board is connected - a straight is possible"))
            break

    return signals


def relevant_warnings(category: int, signals: list[tuple[str, str]]) -> list[str]:
    """Filter out warnings that are no longer meaningful given the hand you already have.

    Two of these signals are tautological once you've already made the hand they describe,
    because you only hold 2 hole cards: a made flush always implies 3+ board cards of that
    suit (you supply at most 2 of the 5), and a made straight always implies the board has
    3+ ranks crammed into a tight span (same reasoning — you supply at most 2 of the 5
    consecutive ranks). So flush_suit is dropped for a flush, connected is dropped for a
    straight. A flush also beats a straight, so connected isn't a real threat to a flush
    holder either. A full house or better is rarely beaten by anything these simple board
    signals can flag, so no warnings carry through at that point — real exceptions (a bigger
    full house, quads, a straight flush) aren't modeled here.
    """
    if category >= 7:
        return []
    if category == 6:  # flush
        exclude = {"flush_suit", "connected"}
    elif category == 5:  # straight
        exclude = {"connected"}
    else:
        exclude = set()
    return [msg for kind, msg in signals if kind not in exclude]


def find_outs(hole_cards: list[str], board: list[str]) -> tuple[list[str], int]:
    """Cards that meaningfully improve the hand if drawn (two pair or better).
    Returns (out_cards, current_category)."""
    known = hole_cards + board
    known_parsed = [parse_card(c) for c in known]
    current_category, _ = best_hand(known_parsed)

    outs = []
    for candidate in remaining_deck(known):
        trial = known_parsed + [parse_card(candidate)]
        new_category, _ = best_hand(trial)
        if new_category > current_category and new_category >= MEANINGFUL_IMPROVEMENT:
            outs.append(candidate)
    return outs, current_category


def improve_chance(num_outs: int, cards_to_come: int) -> dict:
    """Rule of 4 and 2 approximation."""
    if cards_to_come == 2:
        return {
            "next_card": f"{num_outs * 2:.1f}%",
            "by_river": f"{min(num_outs * 4, 100):.1f}%",
        }
    if cards_to_come == 1:
        return {"next_card": f"{min(num_outs * 2, 100):.1f}%"}
    return {}


def preflop_label(hole_cards: list[str]) -> str:
    (r1, _), (r2, _) = (parse_card(c) for c in hole_cards)
    if r1 == r2:
        return "Premium starting hand" if r1 >= 10 else "Decent starting hand"
    if min(r1, r2) >= 10:
        return "Strong starting hand"
    return "Speculative starting hand"


def strength_label(category: int, num_outs: int) -> str:
    if category >= 6:
        return "Strong made hand"
    if category >= 4:
        return "Decent made hand"
    if num_outs >= 12:
        return "Strong draw"
    if num_outs >= 8:
        return "Decent draw"
    if num_outs > 0:
        return "Weak draw"
    return "Weak hand"


STRENGTH_FALLBACK_ACTION = {
    "Premium starting hand": "Raise",
    "Strong starting hand": "Raise",
    "Decent starting hand": "Call",
    "Speculative starting hand": "Fold",
    "Strong made hand": "Raise",
    "Decent made hand": "Call",
    "Strong draw": "Call",
    "Decent draw": "Call",
    "Weak draw": "Fold",
    "Weak hand": "Fold",
}


def pot_odds_recommendation(category: int, num_outs: int, board_len: int,
                             pot_size: float, bet_to_call: float, strength: str,
                             num_opponents: int, board_warnings: list[str]) -> dict:
    """Compare draw equity (from outs) against the equity required by pot odds.

    num_opponents discounts equity: completing a draw only wins the pot if you also
    beat everyone else, so more opponents means your raw outs-based equity overstates
    your real chance to win. This is a simple heuristic (equity / num_opponents), not
    an exact multiway calculation — accurate multiway equity needs opponent range modeling.
    """
    if bet_to_call <= 0:
        return {
            "action": "Check",
            "reasoning": "There's no bet to call, so pot odds don't apply - you can see the next card for free.",
        }

    required = bet_to_call / (pot_size + bet_to_call) * 100
    opponent_note = "" if num_opponents == 1 else f" (discounted for {num_opponents} opponents)"

    if category >= 6:
        if board_warnings:
            return {
                "action": "Call",
                "reasoning": (
                    f"You have a {hand_name(category)}, but be cautious: {'; '.join(board_warnings)}. "
                    f"Call rather than raise into a board that could already have you beat."
                ),
                "pot_odds_required": f"{required:.1f}%",
                "board_warnings": board_warnings,
            }
        # Already a flush or better, and the board doesn't show obvious danger signs — bet for value.
        return {
            "action": "Raise",
            "reasoning": (
                f"You already have a {hand_name(category)}, well ahead of the "
                f"{required:.1f}% equity needed to call - bet for value, even against {num_opponents} opponent(s)."
            ),
            "pot_odds_required": f"{required:.1f}%",
        }

    cards_to_come = 2 if board_len == 3 else 1
    raw_equity = min(num_outs * (4 if cards_to_come == 2 else 2), 100)
    equity = raw_equity / num_opponents
    warning_suffix = f" Also, {'; '.join(board_warnings)}." if board_warnings else ""

    if equity < required:
        result = {
            "action": "Fold",
            "reasoning": (
                f"You need about {required:.1f}% equity to call profitably, "
                f"but your draw gives you roughly {equity:.1f}%{opponent_note} "
                f"({num_outs} outs). Folding is correct here.{warning_suffix}"
            ),
            "pot_odds_required": f"{required:.1f}%",
            "your_equity": f"{equity:.1f}%",
        }
    else:
        result = {
            "action": "Call",
            "reasoning": (
                f"Your equity ({equity:.1f}%{opponent_note}) beats the {required:.1f}% needed to call "
                f"profitably with {num_outs} outs.{warning_suffix}"
            ),
            "pot_odds_required": f"{required:.1f}%",
            "your_equity": f"{equity:.1f}%",
        }
    if board_warnings:
        result["board_warnings"] = board_warnings
    return result


def strength_fallback_recommendation(strength: str, board_warnings: list[str]) -> dict:
    action = STRENGTH_FALLBACK_ACTION.get(strength, "Fold")
    if action == "Raise" and board_warnings:
        action = "Call"
        reasoning = (
            f"Hand strength ('{strength}') would normally suggest raising, but be cautious: "
            f"{'; '.join(board_warnings)}. No pot odds given, so this is a rough estimate."
        )
    else:
        reasoning = (
            f"No pot size / bet to call given, so this is based on hand strength alone "
            f"('{strength}'), not pot odds."
        )
    result = {"action": action, "reasoning": reasoning}
    if board_warnings:
        result["board_warnings"] = board_warnings
    return result


def analyze(hole_cards: list[str], board: list[str],
            pot_size: float | None = None, bet_to_call: float | None = None,
            num_opponents: int = 1) -> dict:
    if len(hole_cards) != 2:
        raise ValueError("hole_cards must contain exactly 2 cards")
    if len(board) not in (0, 3, 4, 5):
        raise ValueError("board must have 0 (preflop), 3 (flop), 4 (turn), or 5 (river) cards")
    if (pot_size is None) != (bet_to_call is None):
        raise ValueError("pot_size and bet_to_call must be given together")
    if pot_size is not None and (pot_size < 0 or bet_to_call < 0):
        raise ValueError("pot_size and bet_to_call must not be negative")
    if num_opponents < 1:
        raise ValueError("num_opponents must be at least 1")

    hole_cards = validate_cards(hole_cards)
    board = validate_cards(board)
    validate_cards(hole_cards + board)  # cross-check for duplicates between hole cards and board

    known_parsed = [parse_card(c) for c in hole_cards + board]
    category, _ = best_hand(known_parsed) if len(known_parsed) >= 5 else (0, [])

    outs, current_category = ([], category)
    chances = {}
    if len(board) in (3, 4):
        outs, current_category = find_outs(hole_cards, board)
        cards_to_come = 2 if len(board) == 3 else 1
        chances = improve_chance(len(outs), cards_to_come)

    current_hand_name = hand_name(current_category) if current_category else "Preflop"
    if not board:
        strength = preflop_label(hole_cards)
    elif len(board) == 5:
        strength = strength_label(current_category, 0)
    else:
        strength = strength_label(current_category, len(outs))

    warnings = relevant_warnings(current_category, board_danger_signals(board))

    if pot_size is not None and len(board) in (3, 4):
        recommendation = pot_odds_recommendation(
            current_category, len(outs), len(board), pot_size, bet_to_call, strength,
            num_opponents, warnings
        )
    else:
        recommendation = strength_fallback_recommendation(strength, warnings)

    return {
        "current_hand": current_hand_name,
        "outs": len(outs),
        "out_cards": outs,
        "improve_chance": chances,
        "hand_strength": strength,
        "recommendation": recommendation,
    }
