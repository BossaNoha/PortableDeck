"""Read-only overview of the rules actually stored in the current session."""
import os
import tkinter as tk
from ..core.interactions import INTERACTIONS


def session_rule_sections(game):
    g = game
    sections = [("Game", [f"Players: {len(g.players)}", f"Deck: {os.path.basename(g.deck.path)}",
                           f"Starting hand: {g.cards_per_player} cards per player"])]
    def add(title, enabled, lines):
        if enabled:
            sections.append((title, lines or ["Enabled"]))
    def flags(pairs):
        return [label for attribute, label in pairs if getattr(g, attribute, False)]
    add("Scoring", g.score_enabled, flags((("allow_reduce_score", "Reduce score"),
        ("require_point_confirmation", "Other players approve score changes"),
        ("share_team_score", "Shared score within team"), ("enable_team_score", "Separate team score"))) +
        ([f"Target score: {g.target_score}"] if g.enable_target_score else []) +
        ([f"Score warning: {g.score_warning}"] if g.enable_target_score and g.enable_score_warning else []))
    add("Chip accounts", g.enable_chip_accounts,
        [f"Starting balance: {g.starting_balance}", f"Minimum bet: {g.minimum_bet}",
         "Restart: reset balances and pot" if g.reset_chip_accounts_on_restart else "Restart: keep balances and pot"] +
        flags((("share_team_chips", "Shared chips within team"),
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
            table.append(f"Maximum rows: {g.max_table_rows}")
        if g.limit_table_columns:
            table.append(f"Maximum columns: {g.max_table_columns}")
    if g.allow_positioned_play:
        table.append(f"Occupied position: {g.occupied_slot_action}")
    add("Table", g.enable_table, table)
    add("Discard pile", g.enable_discard_pile, [f"Shared piles: {len(g.discard_piles)}"] +
        (["Draw from discard: " + ("any card" if g.draw_from_discard_mode == "any" else "top card")]
         if g.allow_draw_from_discard else []) +
        (["Recycle discard when draw deck is empty"] if g.allow_recycle_discard_to_deck else []))
    access_labels = {"owner":"Owner only", "team":"Team", "everyone":"Everyone",
                     "team_dealer":"Team + Dealer", "dealer_only":"Dealer only", "owner_dealer":"Owner + Dealer",
                     "everyone_but_owner":"Everyone but owner", "team_but_member":"Team but member"}
    personal = flags((("enable_team_pile_access", "Team access enabled"), ("enable_dealer_pile_access", "Dealer access enabled")))
    for owner, player in enumerate(g.players):
        for index, rule in enumerate(g.personal_pile_settings[owner]):
            order = ("Not ordered" if not rule["ordered"] else
                     f"By size: {rule['size_order']}" if rule["order_by"] == "size" else f"By time: new card at {rule['new_card']}")
            personal.append(f"{player.name} / Pile {index + 1}: {access_labels.get(rule['access'], rule['access'])}; {order}")
    add("Personal piles on table", g.enable_table and g.enable_personal_piles, personal)
    teams = []
    for team in g.teams:
        members = [p.name for i,p in enumerate(g.players) if
                   (g.player_is_dealer(i) if team["id"] == "dealer" else g.player_teams[i] == team["id"])]
        teams.append(f"{team['name']}: {', '.join(members) or 'No players assigned'}")
    add("Roles/teams", g.enable_roles_teams and (g.enable_teams or g.enable_dealer), teams)
    add("Player interactions", g.enable_interactions, [label for key,label in INTERACTIONS.items() if g.interaction_allowed(key)])
    add("Special actions", g.enable_special_actions,
        (["Place selected card in draw deck"] if g.allow_insert_draw_deck else []) +
        (["Place selected card in discard pile"] if g.allow_insert_discard_pile and g.enable_discard_pile else []))
    add("Flipping cards", g.enable_flipping,
        (["Flip hand cards (reveals them to others)"] if g.allow_flip_hand else []) +
        (["Flip cards in front of players" if g.allow_play_in_front_of_players else "Flip table cards"] if g.can_flip_table_cards() else []))
    visibility = []
    names = {team["id"]:team["name"] for team in g.teams}
    for owner, rule in enumerate(g.cards_visibility):
        viewers = [g.players[i].name for i in rule["players"]]
        viewers += [names[team] for team in rule["teams"] if g.enable_roles_teams and team in names]
        visibility.append(f"{g.players[owner].name}'s hand visible to: {', '.join(viewers) or 'Nobody'}")
    add("Cards visibility", g.enable_cards_visibility, visibility)
    leaving = []
    if g.enable_player_leaving:
        rule = g.leave_conditions
        if rule["own_score"] and g.score_enabled and g.enable_target_score:
            leaving.append(f"Player reaches {rule['own_score_at']} score")
        if rule["opponent_score"] and g.score_enabled and g.enable_target_score:
            leaving.append(f"Opponent reaches {rule['opponent_score_at']} score")
        if rule["no_chips"] and g.enable_chip_accounts:
            leaving.append("Player runs out of chips")
        if leaving:
            leaving.insert(0, "Leave after: " + ("all conditions" if rule["match"] == "all" else "at least one condition"))
        else:
            leaving.append("Leaving allowed at any time")
    if g.enable_player_return:
        leaving.append("Departed players may return")
    add("Leaving session", g.enable_player_leaving or g.enable_player_return, leaving)
    return sections


def show_rules_overview(gui):
    game = gui.game
    window = tk.Toplevel(gui.root)
    window.title("Overview rules")
    window.transient(gui.root)
    window.geometry(f"{min(700, window.winfo_screenwidth()-80)}x{min(620, window.winfo_screenheight()-100)}")
    info = game.configuration_info
    modified = {True:"Yes", False:"No"}.get(info.get("modified"), "Unknown")
    tk.Label(window, text=f"Configuration: {info.get('name', 'Unknown')}   |   Modified preset: {modified}",
             wraplength=620, justify="left", padx=12, pady=10).pack(anchor="w")
    frame = tk.Frame(window)
    frame.pack(fill="both", expand=True, padx=12)
    text = tk.Text(frame, wrap="word", padx=10, pady=8, width=60)
    bar = tk.Scrollbar(frame, command=text.yview)
    bar.pack(side="right", fill="y")
    text.pack(fill="both", expand=True)
    text.configure(yscrollcommand=bar.set)
    text.tag_configure("heading", font=("TkDefaultFont", 11, "bold"), spacing1=8, spacing3=4)
    for title, lines in session_rule_sections(game):
        text.insert("end", title + "\n", "heading")
        for line in lines:
            text.insert("end", "• " + line + "\n")
        text.insert("end", "\n")
    text.configure(state="disabled")
    tk.Button(window, text="Close", command=window.destroy).pack(anchor="e", padx=12, pady=10)
    return window
