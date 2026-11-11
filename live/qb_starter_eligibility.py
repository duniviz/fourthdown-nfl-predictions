"""Eligibility checks for publishing QB prop forecasts."""
def verified_qb_starter(starters, game_id, team, player_name):
    """Return a sourced QB1 record, accepting official confirmation or depth rank 1."""
    key = (str(game_id), str(team or "").upper(), "QB")
    name = str(player_name or "").strip().casefold()
    if not name:
        return None
    for row in starters.get(key, []):
        if str(row.get("player") or "").strip().casefold() != name:
            continue
        status = str(row.get("status") or "").lower()
        if status == "confirmed":
            return row
        try:
            if int(row.get("depth_rank", 0)) == 1:
                return row
        except (TypeError, ValueError):
            continue
    return None
