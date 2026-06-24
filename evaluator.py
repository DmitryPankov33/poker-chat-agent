"""5-card poker hand evaluation. Works on (rank_value, suit) tuples."""

from collections import Counter
from itertools import combinations

HAND_NAMES = {
    9: "Straight Flush",
    8: "Four of a Kind",
    7: "Full House",
    6: "Flush",
    5: "Straight",
    4: "Three of a Kind",
    3: "Two Pair",
    2: "One Pair",
    1: "High Card",
}


def _straight_high(ranks_sorted_desc_unique: list[int]) -> int | None:
    """Return the high card of a straight if present, else None. Handles wheel (A-2-3-4-5)."""
    ranks = ranks_sorted_desc_unique
    if 14 in ranks:
        ranks = ranks + [1]  # ace can play low
    for i in range(len(ranks) - 4):
        window = ranks[i:i + 5]
        if window[0] - window[4] == 4:
            return window[0]
    return None


def evaluate_5(cards: list[tuple[int, str]]) -> tuple[int, list[int]]:
    """Score a single 5-card hand. Returns (category, tiebreakers) — higher is better."""
    ranks = sorted((r for r, _ in cards), reverse=True)
    suits = [s for _, s in cards]
    is_flush = len(set(suits)) == 1
    unique_ranks = sorted(set(ranks), reverse=True)
    straight_high = _straight_high(unique_ranks) if len(unique_ranks) >= 5 else None

    counts = Counter(ranks)
    groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    group_sizes = [g[1] for g in groups]

    if is_flush and straight_high:
        return (9, [straight_high])
    if group_sizes[0] == 4:
        four_rank, kicker = groups[0][0], groups[1][0]
        return (8, [four_rank, kicker])
    if group_sizes[0] == 3 and group_sizes[1] == 2:
        return (7, [groups[0][0], groups[1][0]])
    if is_flush:
        return (6, ranks)
    if straight_high:
        return (5, [straight_high])
    if group_sizes[0] == 3:
        kickers = sorted((r for r in ranks if r != groups[0][0]), reverse=True)
        return (4, [groups[0][0]] + kickers)
    if group_sizes[0] == 2 and group_sizes[1] == 2:
        pair_ranks = sorted([groups[0][0], groups[1][0]], reverse=True)
        kicker = groups[2][0]
        return (3, pair_ranks + [kicker])
    if group_sizes[0] == 2:
        kickers = sorted((r for r in ranks if r != groups[0][0]), reverse=True)
        return (2, [groups[0][0]] + kickers)
    return (1, ranks)


def best_hand(cards: list[tuple[int, str]]) -> tuple[int, list[int]]:
    """Best 5-card score from 5+ cards."""
    if len(cards) < 5:
        raise ValueError("Need at least 5 cards to evaluate a hand")
    return max(evaluate_5(combo) for combo in combinations(cards, 5))


def hand_name(category: int) -> str:
    return HAND_NAMES[category]
