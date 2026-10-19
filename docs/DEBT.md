# Technical debt and cleanup log

Rule: when you leave a shortcut, add a line here. Cleanup (20/10/2026, tag `cleanup-1`): done items are struck through in the log below.

## Open debt (measured, not guessed)
| Item | Where | Why it is still there | When to fix |
|---|---|---|---|
| 69 `sys.path.insert` hacks in 54 files | tools, ops, ui, assets_mcp, tests | Scripts run as `python tools/x.py`; a proper `af` package needs every entry point to become a thin wrapper | with the package layout change (needs its own chapter: one commit per package, tests after each) |
| Very long functions | `build_video.main` (~260 lines), `ui/server._project_api` (~208), `validate_storyboard.validate` (~190), `build_storyboard.expand` (~157), `export_remotion.export` (~134) | split risks changing behaviour; covered by integration tests only | split next time one of them is edited for a feature |
| `prepare.py` 995 lines, `ui/server.py` 657 lines | | one file per concern is cheap to add but touches many imports | split by step (research, script, storyboard, assets) when next changed |
| No `logging` module: scripts print; each tool has its own `log()` | many | CLI output is part of several tests | introduce a shared `log` when the package layout lands |
| JSON read/write helpers repeated (`read_json`, `_load/_save`, 56 `json.loads(...read_text...)`) | tools | low value per site | one `jsonio.py` with the package layout |
| Path constants `P2 = Path(__file__).parent.parent` in ~38 files; the folder is still called `phase2` | all | renaming `phase2` touches ~60 files and `.mcp.json` | only after `toolpaths.py` is the single source of truth |
| `ui/static/index.html` 82 KB single file | ui | works, no build step | split when a second screen is added |
| Timeline logic ported by hand (`scene_anim.jsx` -> `remotion/src/timeline.ts`) | lib, remotion | no automated parity test | add a parity test when the Craft path is retired |
| `cost_model.json` is rewritten by `calibrate.py` inside the source tree | phase2/ | calibration baseline | move to runtime state when the config dir is introduced |

## Cleanup log
- B1 ~~project data, evidence logs, topic history tracked in git~~ -> untracked; `phase2/projects/.gitignore` allowlists only the fixtures tests read (`video1_luong`, `video2_quy_khan_cap`, `ui_demo`).
- B2 ~~documents scattered in phase2 and the root~~ -> `docs/` (guide, acceptance, plans, archive) + index.
- B3 ~~phase-1 tools/tests/acceptance at the repo root~~ -> `legacy/phase1/`; its voice client moved to `phase2/tools/voice.py`.
- B4 ~~`plan_actions` copied in two renderers~~ -> `tools/action_plan.py`; ~~three `sha_file`~~ -> `agy_image.sha_file`; ~~dead `_alive`~~; ~~hard-coded Windows font path~~ -> `toolpaths.font_bold()`.
- B5 anti-rubbish: `ops/clean.py`, repo hygiene test, `.editorconfig` (see below).
