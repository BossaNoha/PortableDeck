"""Score notifications prepared independently of any interface."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreNotification:
    key: str
    kind: str
    recipient: int
    title: str
    message: str
    requires_confirmation: bool = True
    subject: str = ""
    score: int | None = None
    threshold: int | None = None
    requester: int | None = None
    delta: int | None = None


def active_score_notifications(game):
    """Return active threshold events and their excluded warning recipients."""
    g = game
    if not g.score_enabled or not g.enable_target_score or not g.active_player_indices():
        return {}, {}
    active, owners = {}, {}
    viewer = g.current_player_index

    def add(identity, label, score, members, *, team_counter=False):
        if score >= g.target_score:
            kind, threshold = "target", g.target_score
            message = f"{label} reached the target score ({score}/{threshold})."
        elif g.enable_score_warning and score >= g.score_warning:
            kind, threshold = "warning", g.score_warning
            message = (f"{label} reached the warning threshold: {score} points." if team_counter else
                       f"{label} reached the warning threshold: {score} points (threshold {threshold}).")
        else:
            return
        key = f"{kind}:{identity}"
        active[key] = ScoreNotification(key, kind, viewer, "Score notice", message,
                                       subject=label, score=score, threshold=threshold)
        if kind == "warning":
            owners.setdefault(key, set()).update(members)

    for i, score in enumerate(g.scores):
        identity, label = f"player_{i}", g.players[i].name
        if g.share_team_score and g.player_teams[i]:
            identity, label = g.player_teams[i], g.player_team_name(i)
        add(identity, label, score, {i})
    if g.enable_team_score:
        for team in g.teams:
            if team["id"] != "dealer":
                members = {i for i, team_id in enumerate(g.player_teams) if team_id == team["id"]}
                add(f"team_counter:{team['id']}", f"Team {team['name']}",
                    g.team_scores[team["id"]], members, team_counter=True)
    return active, owners


def pending_score_notifications(game):
    """Read-only query; displaying a notification does not acknowledge it."""
    active, owners = active_score_notifications(game)
    viewer = game.current_player_index
    seen = game.score_alerts_seen.get(str(viewer), [])
    return tuple(notice for key, notice in active.items()
                 if key not in seen and viewer not in owners.get(key, set()))


def acknowledge_score_notifications(game, notifications):
    """Acknowledge only current, actually delivered events for this player.

    Also prune events no longer active, allowing a new threshold crossing to
    notify again. Call with an empty sequence when there is nothing to display.
    """
    active, owners = active_score_notifications(game)
    for viewer in list(game.score_alerts_seen):
        game.score_alerts_seen[viewer] = [key for key in game.score_alerts_seen[viewer] if key in active]
    viewer = game.current_player_index
    seen = game.score_alerts_seen.setdefault(str(viewer), [])
    for notice in notifications:
        if (notice.recipient == viewer and active.get(notice.key) == notice
                and viewer not in owners.get(notice.key, set()) and notice.key not in seen):
            seen.append(notice.key)


def score_confirmation_notification(game):
    """Prepare a pending score approval prompt; the client submits the decision."""
    if not game.current_player_must_confirm_point():
        return None
    request = game.pending_point_request
    requester = request["requester"]
    delta = request.get("delta", 1)
    name = game.players[requester].name
    viewer = game.current_player_index
    message = (f"{name} requested a score change of {delta:+d}.\n\n"
               f"As {game.players[viewer].name}, do you approve this score change?")
    return ScoreNotification(f"confirm_point:{requester}:{delta}", "score_approval", viewer,
        "Confirm point request", message, subject=name, requester=requester, delta=delta)
