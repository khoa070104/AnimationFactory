# AnimationFactory

A tool that AI CLIs (Claude CLI, Gemini CLI, Antigravity...) drive to produce 2D animated videos: storyboard data -> shots/camera -> Remotion render, with Antigravity-made assets, paid voice behind approvals and a budget.

## Review per chapter (one tag each)
| Chapter | Tag | Start here |
|---|---|---|
| Baseline before chapter 1 | `chang0-baseline` | - |
| 1. Control contract, shots, camera, layout | `chang1-done` | `docs/acceptance/ACCEPTANCE_CHANG1.md`, `docs/guide/HUONG_DAN_AF.md`, `docs/plans/PLAN_CHANG1.md`, evidence in `phase2/evidence/chang1/` |

## Layout
- `phase2/tools/` Python core (`af.py` / `af_core.py` control layer, `shots.py`, `layout.py`, `build_remotion.py`, `export_remotion.py`, ...)
- `phase2/remotion/` Remotion renderer (camera, layers, rig drawing, incremental render)
- `phase2/assets_mcp/` MCP server (asset jobs + the same control layer)
- `phase2/examples/` two storyboards (a story, an explanation)
- `phase2/tests/`, `phase2/remotion/tests/` tests
- Not in the repo: `.env`/keys, generated pictures, audio, video output, caches.

## Repo layout and hygiene
- `phase2/` source (tools, remotion, lib, tests, ops); `docs/` all guides/plans/acceptance (index: `docs/README.md`); `legacy/phase1/` frozen old pipeline; `docs/DEBT.md` open debt.
- Generated data (projects other than 3 fixtures, audio, renders, caches, zips) is git-ignored. `python phase2/ops/clean.py` lists rubbish (dry run), `--apply` removes it.
- `phase2/tests/test_repo_hygiene.py` fails if a stray top-level entry, media/zip, secret, oversize file, loose markdown or hard-coded machine path is tracked.
