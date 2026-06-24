"""Standard, simplified preflop ranges per position tier.

These are reasonable approximations of commonly-published tight-aggressive charts, not a
solver-perfect GTO output. Opening is modeled as raise-or-fold (no limping). Facing a raise
is modeled as 3bet / call / fold, with the raiser's exact tier collapsed into an "Early"
(tight, respect it) or "Late" (wide, play back at it) bucket — see positions.raiser_bucket.
"""

# --- Opening ranges (raise-or-fold, action folded to you) ---

EARLY = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77",
    "AKs", "AQs", "AJs", "ATs",
    "AKo", "AQo",
    "KQs", "KJs", "QJs", "JTs",
}

MIDDLE = EARLY | {
    "66", "55",
    "A9s", "A8s",
    "ATo", "KJo",
    "KTs", "K9s",
    "QTs", "J9s",
    "T9s", "98s",
}

LATE = MIDDLE | {
    "44", "33", "22",
    "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "A9o", "A8o",
    "KQo", "KTo", "K8s",
    "QJo",
    "Q9s", "Q8s",
    "J8s", "T8s",
    "87s", "76s", "65s", "54s",
}

BTN = LATE | {
    "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
    "K9o", "K8o", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
    "QTo",
    "Q9o", "Q7s", "Q6s",
    "JTo",
    "J9o", "J7s",
    "T9o", "T7s",
    "98o", "97s",
    "87o", "86s",
    "76o", "75s",
    "65o", "64s",
    "54o", "53s",
    "43s", "32s",
}

# SB-open is between CO and BTN in width (wide vs. just the BB, but still OOP postflop).
SB = LATE | {
    "A8o", "A7o", "A6o",
    "K9o", "K7s", "K6s",
    "Q9o", "Q7s",
    "J9o", "J8o",
    "T9o", "T8o",
    "98o", "97s",
    "87o", "86s",
    "76o", "65o",
}

OPENING_RANGES = {
    "Early": EARLY,
    "Middle": MIDDLE,
    "Late": LATE,
    "BTN": BTN,
    "SB": SB,
}


def _vs(threebet: set, call: set) -> dict:
    return {"3bet": threebet, "call": call}


# --- Facing-a-raise ranges: (your tier, raiser bucket) -> {3bet, call} ---

FACING_RAISE = {
    ("Early", "Early"): _vs(
        {"AA", "KK", "QQ", "AKs", "AKo"},
        {"JJ", "TT", "AQs", "AQo", "KQs"},
    ),
    ("Middle", "Early"): _vs(
        {"AA", "KK", "QQ", "AKs", "AKo"},
        {"JJ", "TT", "99", "AQs", "AQo", "AJs", "KQs", "KJs"},
    ),
    ("Middle", "Late"): _vs(
        {"AA", "KK", "QQ", "JJ", "AKs", "AKo", "AQs"},
        {"TT", "99", "88", "AQo", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs"},
    ),
    ("Late", "Early"): _vs(
        {"AA", "KK", "QQ", "JJ", "AKs", "AKo", "AQs"},
        {"TT", "99", "88", "AQo", "AJs", "ATs", "KQs", "KJs", "QJs"},
    ),
    ("Late", "Late"): _vs(
        {"AA", "KK", "QQ", "JJ", "TT", "AKs", "AKo", "AQs", "AQo", "AJs", "KQs"},
        {"99", "88", "77", "66", "ATs", "A9s", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s"},
    ),
    ("BTN", "Early"): _vs(
        {"AA", "KK", "QQ", "JJ", "TT", "AKs", "AKo", "AQs", "AQo"},
        {"99", "88", "77", "AJs", "ATs", "KQs", "KJs", "KTs", "QJs", "JTs"},
    ),
    ("BTN", "Late"): _vs(
        {"AA", "KK", "QQ", "JJ", "TT", "99", "AKs", "AKo", "AQs", "AQo", "AJs", "AJo", "KQs", "KQo"},
        {"88", "77", "66", "55", "ATs", "A9s", "A8s", "KJs", "KTs", "K9s",
         "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "98s"},
    ),
    ("SB", "Early"): _vs(
        {"AA", "KK", "QQ", "AKs", "AKo", "AJs"},
        {"JJ", "TT", "99", "AQs", "AQo", "KQs"},
    ),
    ("SB", "Late"): _vs(
        {"AA", "KK", "QQ", "JJ", "AKs", "AKo", "AQs", "AJs", "KQs"},
        {"TT", "99", "88", "AQo", "ATs", "A9s", "KJs", "KTs", "QJs"},
    ),
    ("BB", "Early"): _vs(
        {"AA", "KK", "QQ", "AKs", "AKo", "AQs"},
        {"JJ", "TT", "99", "AQo", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs"},
    ),
    ("BB", "Late"): _vs(
        {"AA", "KK", "QQ", "JJ", "TT", "AKs", "AKo", "AQs", "AQo", "AJs", "KQs", "KQo"},
        {"99", "88", "77", "66", "55", "ATs", "A9s", "A8s", "A7s", "AJo", "ATo", "A9o", "A8o",
         "KJs", "KTs", "K9s", "QJs", "QTs", "JTs", "J9s", "T9s", "98s", "87s", "76s", "65s"},
    ),
}
