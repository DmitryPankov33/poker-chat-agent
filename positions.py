"""Maps table size (4-9 players) to a sequence of position tiers, in preflop action order
(first to act after the blinds ... up to the button, then SB, then BB last).

Real position names (UTG, MP, CO...) shift around depending on table size, so instead of
naming every seat, seats are bucketed into tiers: Early, Middle, Late, BTN, SB, BB. This
scales to any table size without needing a separate named-position chart for each one.
"""

# Tiers for the non-blind, non-button seats, indexed by how many such seats exist
# (table_size - 3, since BTN/SB/BB are always their own tiers).
_NON_BUTTON_TIERS = {
    1: ["Late"],
    2: ["Early", "Late"],
    3: ["Early", "Middle", "Late"],
    4: ["Early", "Early", "Middle", "Late"],
    5: ["Early", "Early", "Middle", "Middle", "Late"],
    6: ["Early", "Early", "Early", "Middle", "Middle", "Late"],
}

# Conventional position names for the non-blind, non-button seats, same indexing as above.
# Separate from the tiers above: this is purely for display/learning, the range logic only
# ever looks at tiers. Standard naming counts back from the button: CO, then HJ, then MP,
# then UTG (+1, +2...) for the earliest seats.
_NON_BUTTON_NAMES = {
    1: ["CO"],
    2: ["UTG", "CO"],
    3: ["UTG", "HJ", "CO"],
    4: ["UTG", "UTG+1", "HJ", "CO"],
    5: ["UTG", "UTG+1", "MP", "HJ", "CO"],
    6: ["UTG", "UTG+1", "UTG+2", "MP", "HJ", "CO"],
}

MIN_TABLE_SIZE = 4
MAX_TABLE_SIZE = 9


def seat_tiers(table_size: int) -> list[str]:
    """Position tier for each seat, in action order (index 0 acts first preflop)."""
    if table_size < MIN_TABLE_SIZE or table_size > MAX_TABLE_SIZE:
        raise ValueError(f"table_size must be between {MIN_TABLE_SIZE} and {MAX_TABLE_SIZE}")
    k = table_size - 3
    return _NON_BUTTON_TIERS[k] + ["BTN", "SB", "BB"]


def seat_names(table_size: int) -> list[str]:
    """Conventional position name for each seat, in the same action order as seat_tiers."""
    if table_size < MIN_TABLE_SIZE or table_size > MAX_TABLE_SIZE:
        raise ValueError(f"table_size must be between {MIN_TABLE_SIZE} and {MAX_TABLE_SIZE}")
    k = table_size - 3
    return _NON_BUTTON_NAMES[k] + ["BTN", "SB", "BB"]


def raiser_bucket(raiser_tier: str) -> str:
    """Collapses a raiser's exact tier into 'Early' (tight, respect it) or 'Late' (wide,
    can be played back at more loosely) to keep the facing-a-raise chart a manageable size."""
    return "Early" if raiser_tier in ("Early", "Middle") else "Late"
