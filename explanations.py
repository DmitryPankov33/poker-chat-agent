"""Plain-English reasoning for why a given action is correct, built from templates rather
than hand-by-hand text. Combines: how wide this position/raiser situation should play, plus
why this specific hand's category does or doesn't have enough value to continue."""

from cards import RANKS

OPEN_POSITION_TEXT = {
    "Early": "Early position is the tightest spot at the table — most players are still left to act, so only strong hands are profitable to open.",
    "Middle": "Middle position can open a bit wider than Early, but there are still several players left to act behind you.",
    "Late": "Late position (CO) can open much wider — fewer players are left who could wake up with a big hand.",
    "BTN": "The Button can open the widest of any position — only the blinds are left, and you'll have position after the flop.",
    "SB": "Small Blind only has to get through the Big Blind, so it can open almost as wide as the Button.",
}

RAISER_RESPECT_TEXT = {
    "Early": "This raise came from a tighter position, which usually means a stronger range — defend tighter against it.",
    "Late": "This raise came from a wider, later position, which is often weaker — you can defend more loosely against it.",
}

HERO_DEFENSE_TEXT = {
    "Early": "From Early position, even facing another early raise, you still have many players left to act behind you, so this stays very tight.",
    "BB": "As the Big Blind you're also getting the best price on a call, since you've already got chips invested — that lets you defend wider than position alone would suggest.",
    "SB": "The Small Blind doesn't get BB's pot-odds discount and is out of position for the whole hand if called, so it has to defend tighter.",
    "Middle": "From Middle position you still have players left to act behind you, so the calling/3-betting range stays fairly tight.",
    "Late": "From Late position (CO) you're closer to the button but still don't have post-flop position on a button raiser, so this stays moderately tight.",
    "BTN": "The Button gets to act last on every post-flop street, which is enough of an edge to defend a bit wider than other seats.",
}

HAND_CATEGORY_CONTINUE_TEXT = {
    "pair": "Pocket pairs play well in almost any spot — set value and raw equity make this worth continuing.",
    "ace_suited": "A suited ace has both kicker value and flush backup — enough to continue here.",
    "ace_offsuit": "A strong offsuit ace has enough raw value on its own to continue here.",
    "broadway_suited": "Suited broadway hands combine strong kicker value with flush potential — enough to continue here.",
    "broadway_offsuit": "Strong enough on raw card value to continue here, even without a suit to back it up.",
    "suited_connector": "Straight and flush potential plus decent implied odds make this worth continuing here.",
    "other": "Strong enough relative to the rest of this range to continue here.",
}

HAND_CATEGORY_FOLD_TEXT = {
    "pair": "Even a small pair isn't automatically strong enough here — set value alone doesn't justify it in this spot.",
    "ace_suited": "A suited ace usually has enough backup to continue, but not quite enough in this particular spot.",
    "ace_offsuit": "An offsuit ace without more strength behind it isn't enough to continue against this range.",
    "broadway_suited": "Even with a flush draw behind it, this isn't strong enough on its own to continue here.",
    "broadway_offsuit": "Offsuit broadway hands look strong but get dominated easily, and without a suit to back them up they don't have enough equity here.",
    "suited_connector": "Suited connectors need either great pot odds or a wide, weak opponent range to be profitable — neither lines up enough here.",
    "other": "This hand doesn't have enough raw strength or backup potential to continue here.",
}


def classify_hand(notation: str) -> str:
    """Buckets a hand notation (e.g. 'AKs', 'QJo', 'TT') into a broad category used to
    explain why it does or doesn't have enough value to continue."""
    if len(notation) == 2:
        return "pair"

    high, low, suited_char = notation[0], notation[1], notation[2]
    suited = suited_char == "s"

    if high == "A":
        return "ace_suited" if suited else "ace_offsuit"
    if high in "KQJT" and low in "KQJT":
        return "broadway_suited" if suited else "broadway_offsuit"

    gap = abs(RANKS.index(high) - RANKS.index(low))
    if suited and gap <= 2:
        return "suited_connector"
    return "other"


def explain(question: dict, hand_notation: str, correct_action: str) -> str:
    category = classify_hand(hand_notation)
    is_fold = correct_action == "Fold"
    hand_text = HAND_CATEGORY_FOLD_TEXT[category] if is_fold else HAND_CATEGORY_CONTINUE_TEXT[category]

    if question["scenario"] == "open":
        position_text = OPEN_POSITION_TEXT[question["hero_tier"]]
        return f"{position_text} {hand_text}"

    raiser_bucket_text = RAISER_RESPECT_TEXT[
        "Early" if question["raiser_tier"] in ("Early", "Middle") else "Late"
    ]
    defense_text = HERO_DEFENSE_TEXT.get(question["hero_tier"], "")
    return f"{raiser_bucket_text} {defense_text} {hand_text}".strip()
