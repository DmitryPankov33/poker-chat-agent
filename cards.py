"""Card parsing and deck utilities. Merged from poker_hand_analyzer and poker_position_trainer."""

RANKS = "23456789TJQKA"
SUITS = "shdc"  # spades, hearts, diamonds, clubs
RANK_VALUES = {r: i + 2 for i, r in enumerate(RANKS)}


def parse_card(card: str) -> tuple[int, str]:
    """Parse a card like 'Ah' into (rank_value, suit)."""
    card = card.strip()
    rank_char, suit_char = card[:-1].upper(), card[-1].lower()
    if rank_char not in RANK_VALUES or suit_char not in SUITS:
        raise ValueError(f"Invalid card: {card}")
    return RANK_VALUES[rank_char], suit_char


def full_deck() -> list[str]:
    return [r + s for r in RANKS for s in SUITS]


def remaining_deck(used_cards: list[str]) -> list[str]:
    used = {c.strip() for c in used_cards}
    return [c for c in full_deck() if c not in used]


def normalize_card(card: str) -> str:
    """Validate a card string and return its canonical form, e.g. 'ah' -> 'Ah'."""
    rank, suit = parse_card(card)
    rank_char = RANKS[rank - 2]
    return rank_char + suit


def validate_cards(cards: list[str]) -> list[str]:
    """Validate a list of card strings: checks format and rejects duplicates.
    Returns the cards in canonical form."""
    normalized = [normalize_card(c) for c in cards]
    seen = set()
    for c in normalized:
        if c in seen:
            raise ValueError(f"Duplicate card: {c}")
        seen.add(c)
    return normalized


def hand_notation(card1: str, card2: str) -> str:
    """Canonical starting-hand notation: pairs as 'AA', suited as 'AKs', offsuit as 'AKo'."""
    (r1, s1), (r2, s2) = parse_card(card1), parse_card(card2)
    if r1 == r2:
        rank_char = RANKS[r1 - 2]
        return rank_char + rank_char
    high, low = max(r1, r2), min(r1, r2)
    high_char, low_char = RANKS[high - 2], RANKS[low - 2]
    suited = "s" if s1 == s2 else "o"
    return f"{high_char}{low_char}{suited}"
