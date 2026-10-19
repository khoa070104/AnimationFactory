# AnimationFactory

A tool that AI CLIs (Claude CLI, Gemini CLI, Antigravity...) drive to produce 2D animated videos: storyboard data -> shots/camera -> Remotion render, with Antigravity-made assets, paid voice behind approvals and a budget.

## Review per chapter (one tag each)
| Chapter | Tag | Start here |
|---|---|---|
| Baseline before chapter 1 | `chang0-baseline` | - |
| 1. Control contract, shots, camera, layout | `chang1-done` | `phase2/ACCEPTANCE_CHANG1.md`, `phase2/HUONG_DAN_AF.md`, `phase2/PLAN_CHANG1.md`, evidence in `phase2/evidence/chang1/` |

## Layout
- `phase2/tools/` Python core (`af.py` / `af_core.py` control layer, `shots.py`, `layout.py`, `build_remotion.py`, `export_remotion.py`, ...)
- `phase2/remotion/` Remotion renderer (camera, layers, rig drawing, incremental render)
- `phase2/assets_mcp/` MCP server (asset jobs + the same control layer)
- `phase2/examples/` two storyboards (a story, an explanation)
- `phase2/tests/`, `phase2/remotion/tests/` tests
- Not in the repo: `.env`/keys, generated pictures, audio, video output, caches.
