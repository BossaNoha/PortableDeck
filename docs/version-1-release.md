# Version 1 release scope and blockers

Status: preparation, not release-ready. Reviewed 2026-11-21.

Version 1 ships the current Tkinter desktop interface for local hotseat play.
The replacement interface belongs to version 2. Further architectural work for
version 1 must support a concrete defect or release requirement.

## Scope

- Configure a local game with existing rules, player/team options and decks;
  manage deck definitions and named configuration presets.
- Use existing hand/table/discard/personal-pile actions, drag-and-drop, visibility,
  scores, chips, confirmations, departure/return and Undo.
- Save/load/resume, retain autosaves, restart and exit with existing save/cancel
  choices. Embedded definitions preserve the session after library edits.
- Keep the development CLI and standalone core/services tested. CLI remains a
  development client, not a second end-user interface promised for this release.

Online hosting, replacement UI and new game-specific rules are outside this
release. Fixes should stay small and committed separately.

The verified development environment is Windows with Python 3.11/Tkinter.
The current deliverable runs from source with `python main.py`, without
third-party Python packages. Executable/installer delivery and support claims
for other environments require separate validation and are not assumed complete.

## Confirmed blockers

Reproduced using temporary files and injected IO failures; user settings were
not touched. Neither finding is fixed by this documentation commit.

| ID | Problem and evidence | Required outcome before closing |
| --- | --- | --- |
| V1-01 | `app/settings.py:save_settings` opens the existing file in write mode. An injected failure after writing a JSON prefix replaced valid settings with unreadable partial JSON. Current-settings apply and Restore Defaults share this writer. | Prepare data before replacement; use an atomic temporary-file write. Failure preserves the prior file and active settings, with temporary output cleaned up where possible. Test failure after partial output and verify apply/default flows. |
| V1-02 | `load_settings` always calls `save_settings`, including after reading valid settings. An injected write denial propagated out of loading; `MainMenu.__init__` has no handler. A readable configuration alone does not permit startup. | Give startup write failures an intentional, visible recovery path. Preserve readable settings in memory and the existing file, report the problem, and avoid an unhandled startup exception or repeated write attempt. Test startup as well as an isolated service call. |

Fix V1-01 first, then V1-02. These are recovery/data-preservation defects;
normal writable-path operation is not reported as broken. Supporting every
read-only installation directory is not implied by these acceptance criteria.

## User journeys and remaining verification

Existing tests and native probes are a baseline, not completed release
acceptance. Re-run these journeys against the candidate release from a fresh,
writable checkout with isolated settings/saves and a temporary welcome marker.
Do not delete or replace a user's configuration to simulate first launch.

| Journey | Existing evidence | Candidate-release checks still needed |
| --- | --- | --- |
| First launch, welcome, menu | Entry point/welcome/settings code reviewed; services tested. | Start without local settings/saves, dismiss welcome, reopen; verify errors for unavailable storage. |
| Settings, defaults, presets | Settings/preset tests and earlier native preset lifecycle probe. | Close V1-01/V1-02; check cancellation, write errors, defaults and legacy preset warnings. |
| Deck create/edit/duplicate/import/export | Service/lifecycle tests and native editor/library probe. | Review shipped examples; check dialogs, overwrite choices and invalid files in the candidate folder. |
| Hotseat play | Action-result, selection, availability and drop tests; native action/control probes. | Actual short play session, including dropping a second card onto an occupied table, hidden cards and representative configured actions. |
| Scores/chips/approvals, departure/return, Undo | Cross-feature/control lifecycle tests and native probes. | Check visible prompts/control states, return after all players leave, and no duplicate saves or Undo entries. |
| Save, autosave, resume, restart | Legacy/embedded-deck persistence tests and native persistence probe. | Restart the process; resume pending decisions; Undo after load; rename/delete an independent save; restart without the original deck file. |
| Exit to menu/desktop | Save/discard cancellation/failure tests; exit code reviewed. | Check save Yes/No/Cancel, declined overwrite, failed save and discard-export error behavior without unexpected loss of the running game. |

An unexpected journey failure becomes a new numbered blocker with reproduction
and regression coverage before its fix. Untested journeys are pending checks,
not asserted defects. No further normal-path bug was confirmed in this review.

## Release gates

1. Close confirmed blockers in separate commits; update this document with evidence.
2. Pass `python -m unittest discover -s tests` and `git diff --check`.
3. Complete the candidate-build journeys and record the tested Python/Tk/OS
   environment and intentional limitations.
4. Review shipped defaults/deck/preset examples and instructions. Exclude local
   settings, sessions, welcome markers and temporary probes. Version identifier,
   tag and release notes remain release tasks; this review publishes nothing.

Baseline: all 384 tests passed. Earlier architecture/native verification is
recorded in [the UI/core audit](ui-core-boundary.md); it does not replace release
user acceptance testing.
