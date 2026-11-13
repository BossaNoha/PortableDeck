"""Read-only session rule data and text formatting for any interface."""
from dataclasses import dataclass
from pathlib import Path
from .interactions import INTERACTIONS


@dataclass(frozen=True)
class RuleEntry:
    key: str
    label: str
    value: str | int | bool | tuple[str, ...] = True
    suffix: str = ""


@dataclass(frozen=True)
class RuleSection:
    key: str
    title: str
    entries: tuple[RuleEntry, ...]


@dataclass(frozen=True)
class RulesOverview:
    configuration_name: str
    modified: bool | None
    sections: tuple[RuleSection, ...]


def build_rules_overview(game):
    """Build an independent snapshot of enabled rules from the live session."""
    g = game
    sections = [RuleSection("game", "Game", (
        RuleEntry("players", "Players", len(g.players)),
        RuleEntry("deck", "Deck", Path(g.deck.path).name),
        RuleEntry("starting_hand", "Starting hand", g.cards_per_player, " cards per player"),
    ))]

    def add(key, title, enabled, entries):
        if enabled:
            sections.append(RuleSection(key, title, tuple(entries) or (RuleEntry("enabled", "Enabled"),)))

    def flags(pairs):
        return [RuleEntry(attribute, label) for attribute, label in pairs if getattr(g, attribute, False)]

    scoring = flags((("allow_reduce_score", "Reduce score"),
        ("require_point_confirmation", "Other players approve score changes"),
        ("share_team_score", "Shared score within team"), ("enable_team_score", "Separate team score")))
    if g.enable_target_score:
        scoring.append(RuleEntry("target_score", "Target score", g.target_score))
        if g.enable_score_warning:
            scoring.append(RuleEntry("score_warning", "Score warning", g.score_warning))
    add("scoring", "Scoring", g.score_enabled, scoring)
    add("chips", "Chip accounts", g.enable_chip_accounts, [
        RuleEntry("starting_balance", "Starting balance", g.starting_balance),
        RuleEntry("minimum_bet", "Minimum bet", g.minimum_bet),
        RuleEntry("restart", "Restart", "reset balances and pot" if g.reset_chip_accounts_on_restart else "keep balances and pot")
    ] + flags((("share_team_chips", "Shared chips within team"),
               ("require_pot_withdrawal_confirmation", "Other players approve pot withdrawal"))))
    table = flags((("allow_take_from_table", "Take table cards into hand"),
        ("allow_move_table_card_to_discard", "Discard table cards"),
        ("allow_manual_table_cleanup", "Manual table cleanup"),
        ("clear_table_on_round_end", "Clear table at round end"),
        ("allow_positioned_play", "Play at selected positions"),
        ("allow_move_cards_on_table", "Move cards between positions"),
        ("allow_play_in_front_of_players", "Cards in front of players"),
        ("allow_face_down_table_cards", "Play cards face down"),
        ("allow_move_table_sequences", "Move face-up sequences")))
    if g.enable_table_limits:
        if g.limit_table_rows:
            table.append(RuleEntry("max_table_rows", "Maximum rows", g.max_table_rows))
        if g.limit_table_columns:
            table.append(RuleEntry("max_table_columns", "Maximum columns", g.max_table_columns))
    if g.allow_positioned_play:
        table.append(RuleEntry("occupied_slot_action", "Occupied position", g.occupied_slot_action))
    add("table", "Table", g.enable_table, table)
    discard = [RuleEntry("shared_piles", "Shared piles", len(g.discard_piles))]
    if g.allow_draw_from_discard:
        discard.append(RuleEntry("draw_from_discard", "Draw from discard", "any card" if g.draw_from_discard_mode == "any" else "top card"))
    if g.allow_recycle_discard_to_deck:
        discard.append(RuleEntry("recycle", "Recycle discard when draw deck is empty"))
    add("discard", "Discard pile", g.enable_discard_pile, discard)
    access_labels = {"owner": "Owner only", "team": "Team", "everyone": "Everyone",
        "team_dealer": "Team + Dealer", "dealer_only": "Dealer only", "owner_dealer": "Owner + Dealer",
        "everyone_but_owner": "Everyone but owner", "team_but_member": "Team but member"}
    personal = flags((("enable_team_pile_access", "Team access enabled"), ("enable_dealer_pile_access", "Dealer access enabled")))
    for owner, player in enumerate(g.players):
        for index, rule in enumerate(g.personal_pile_settings[owner]):
            order = ("Not ordered" if not rule["ordered"] else
                f"By size: {rule['size_order']}" if rule["order_by"] == "size" else f"By time: new card at {rule['new_card']}")
            personal.append(RuleEntry(f"pile_{owner}_{index}", f"{player.name} / Pile {index + 1}",
                access_labels.get(rule["access"], rule["access"]) + "; " + order))
    add("personal_piles", "Personal piles on table", g.enable_table and g.enable_personal_piles, personal)
    teams = []
    for team in g.teams:
        members = tuple(p.name for i, p in enumerate(g.players) if
            (g.player_is_dealer(i) if team["id"] == "dealer" else g.player_teams[i] == team["id"]))
        teams.append(RuleEntry(team["id"], team["name"], members or "No players assigned"))
    add("roles_teams", "Roles/teams", g.enable_roles_teams and (g.enable_teams or g.enable_dealer), teams)
    add("interactions", "Player interactions", g.enable_interactions,
        [RuleEntry(key, label) for key, label in INTERACTIONS.items() if g.interaction_allowed(key)])
    special = []
    if g.allow_insert_draw_deck:
        special.append(RuleEntry("insert_draw", "Place selected card in draw deck"))
    if g.allow_insert_discard_pile and g.enable_discard_pile:
        special.append(RuleEntry("insert_discard", "Place selected card in discard pile"))
    add("special_actions", "Special actions", g.enable_special_actions, special)
    flipping = []
    if g.allow_flip_hand:
        flipping.append(RuleEntry("flip_hand", "Flip hand cards (reveals them to others)"))
    if g.can_flip_table_cards():
        flipping.append(RuleEntry("flip_table", "Flip cards in front of players" if g.allow_play_in_front_of_players else "Flip table cards"))
    add("flipping", "Flipping cards", g.enable_flipping, flipping)
    visibility = []
    names = {team["id"]: team["name"] for team in g.teams}
    for owner, rule in enumerate(g.cards_visibility):
        viewers = tuple(g.players[i].name for i in rule["players"]) + tuple(
            names[team] for team in rule["teams"] if g.enable_roles_teams and team in names)
        visibility.append(RuleEntry(f"hand_{owner}", f"{g.players[owner].name}'s hand visible to", viewers or "Nobody"))
    add("visibility", "Cards visibility", g.enable_cards_visibility, visibility)
    leaving = []
    if g.enable_player_leaving:
        rule = g.leave_conditions
        if rule["own_score"] and g.score_enabled and g.enable_target_score:
            leaving.append(RuleEntry("own_score", f"Player reaches {rule['own_score_at']} score"))
        if rule["opponent_score"] and g.score_enabled and g.enable_target_score:
            leaving.append(RuleEntry("opponent_score", f"Opponent reaches {rule['opponent_score_at']} score"))
        if rule["no_chips"] and g.enable_chip_accounts:
            leaving.append(RuleEntry("no_chips", "Player runs out of chips"))
        if leaving:
            leaving.insert(0, RuleEntry("match", "Leave after", "all conditions" if rule["match"] == "all" else "at least one condition"))
        else:
            leaving.append(RuleEntry("any_time", "Leaving allowed at any time"))
    if g.enable_player_return:
        leaving.append(RuleEntry("return", "Departed players may return"))
    add("leaving", "Leaving session", g.enable_player_leaving or g.enable_player_return, leaving)
    info = g.configuration_info
    return RulesOverview(info.get("name", "Unknown"), info.get("modified"), tuple(sections))


def format_rule_entry(entry):
    if entry.value is True:
        return entry.label
    value = ", ".join(entry.value) if isinstance(entry.value, tuple) else str(entry.value)
    return f"{entry.label}: {value}{entry.suffix}"


def configuration_summary(overview):
    modified = {True: "Yes", False: "No"}.get(overview.modified, "Unknown")
    return f"Configuration: {overview.configuration_name}   |   Modified preset: {modified}"


def format_rules_overview(overview):
    """Plain text output suitable for a CLI, copying or an export."""
    blocks = [configuration_summary(overview)]
    for section in overview.sections:
        blocks.append(section.title + "\n" + "\n".join("- " + format_rule_entry(entry) for entry in section.entries))
    return "\n\n".join(blocks)


def session_rule_sections(game):
    """Compatibility adapter for clients expecting title/lines pairs."""
    return [(section.title, [format_rule_entry(entry) for entry in section.entries])
            for section in build_rules_overview(game).sections]
