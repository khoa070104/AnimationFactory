"""AnimationFactory asset MCP server (stdio). Antigravity's image generator behind two tools:

  submit_asset_job  -> queue an asset request, returns job_id at once
  check_asset_job   -> state of a job by job_id (queued/running/succeeded/failed/timeout/interrupted) with the stored result

All logic lives in tools/agy_jobs.py and tools/agy_image.py (shared with the CLI): evidence that the image tool was used, file taken only from the
job's own conversation, project-scoped output, PNG + background removal, manifest, reuse of unchanged requests, bounded time and attempts.
Approval is NOT a tool: only the owner approves an asset (agy_image.py approve ...); scenes refuse unapproved assets.
MCP over stdio: newline-delimited JSON-RPC 2.0. stdout carries protocol messages only; diagnostics go to stderr.

Register (example, do it yourself in your MCP settings):
  {"mcpServers": {"animation-factory-assets": {"command": "python", "args": ["D:/AnimationFactory/phase2/assets_mcp/af_assets_server.py"]}}}"""
import json
import sys
import threading
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import agy_jobs as J  # noqa: E402
import af_core as AF  # noqa: E402     # the control layer shared with the af.py CLI: one core, two doors

SERVER = {"name": "animation-factory-assets", "version": "1.0.0"}
SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"]
INSTRUCTIONS = ("Generate project art with Antigravity. 1) submit_asset_job (project, asset_id, kind, prompt, optional reference_images / "
                "transparent_background / display_width) returns job_id immediately. 2) Poll check_asset_job until state is succeeded, failed or timeout "
                "(a job takes about 1-2 minutes). A repeated identical request reuses the stored result. New assets are drafts: the owner approves them, "
                "then scenes can use them as {\"type\":\"prop\",\"img\":\"ai:<asset_id>\"}. Control loop: capabilities -> project_get -> edit -> validate/project_put (expect_hash) -> "
                "preview (free: stills per shot, contact sheet, low-res clip) -> fix errors by scene/shot/field -> render (stops at approval gates; approving is the owner's job, there is no approve tool). "
                "Long runs: pass background=true and poll jobs.")
TOOLS = [
    {"name": "submit_asset_job",
     "description": "Queue an image-asset request for a project (Antigravity image generator). Returns a job_id immediately. Same request => same job (no duplicate run, stored result reused). Reports bad input clearly.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["project", "asset_id", "kind", "prompt"], "properties": {
         "project": {"type": "string", "description": "Project folder name under phase2/projects (a folder created by new_project.py)."},
         "asset_id": {"type": "string", "pattern": "^[a-z0-9_]{1,40}$", "description": "Stable id; used in scenes as ai:<asset_id>."},
         "kind": {"type": "string", "enum": ["prop", "character", "background"], "description": "prop/character: single subject, transparent PNG by default; background: 16:9, opaque."},
         "prompt": {"type": "string", "minLength": 3, "maxLength": 2000, "description": "What to draw (the house style rules are added automatically)."},
         "reference_images": {"type": "array", "maxItems": 4, "items": {"type": "string"}, "description": "Absolute paths of reference images for style/shape."},
         "transparent_background": {"type": "boolean", "description": "Remove the white background (default true for prop/character, always false for background)."},
         "display_width": {"type": "integer", "minimum": 64, "maximum": 4096, "description": "Width in canvas px at scale 1.0 (default 300; backgrounds 1920). The PNG is stored at 2x."},
         "regenerate": {"type": "boolean", "description": "Create this asset again even if a result is stored or the request failed twice."},
         "timeout_seconds": {"type": "integer", "minimum": 30, "maximum": 900, "description": "Per-attempt limit (default 330). A timed-out run is not retried automatically."}}}},
    {"name": "check_asset_job",
     "description": "Get a job's state by job_id: queued, running, succeeded, failed, timeout or interrupted. On success: project-relative file, sha256, tool-use evidence, conversation id, agent model label, approval status and a scene snippet. On failure: the reason.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["project", "job_id"], "properties": {
         "project": {"type": "string"}, "job_id": {"type": "string", "description": "As returned by submit_asset_job."}}}},
]
TOOLS += [{k: t[k] for k in ("name", "description", "inputSchema")} for t in AF.TOOLS]       # capabilities, project_*, validate, estimate, preview, render, jobs, artifacts
CONTROL = {t["name"] for t in AF.TOOLS}
_out_lock = threading.Lock()


def send(obj):
    with _out_lock:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def result(rid, res):
    send({"jsonrpc": "2.0", "id": rid, "result": res})


def error(rid, code, msg):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}})


def call_tool(name, args):
    if name in CONTROL:                                                # control layer: results (also errors) are structured JSON, never an exception
        return AF.call(name, args)
    if name == "submit_asset_job":
        a = dict(args)
        project = a.pop("project", None)
        if not project:
            raise J.JobError("project is required")
        return J.submit(project, a)
    if name == "check_asset_job":
        if not args.get("project") or not args.get("job_id"):
            raise J.JobError("project and job_id are required")
        return J.check(args["project"], args["job_id"])
    raise KeyError(name)


def handle(msg):
    method, rid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if method == "initialize":
        want = params.get("protocolVersion")
        result(rid, {"protocolVersion": want if want in SUPPORTED else SUPPORTED[-1], "capabilities": {"tools": {"listChanged": False}},
                     "serverInfo": SERVER, "instructions": INSTRUCTIONS})
    elif method in ("notifications/initialized", "notifications/cancelled"):
        return
    elif method == "ping":
        result(rid, {})
    elif method == "tools/list":
        result(rid, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        try:
            out = call_tool(name, params.get("arguments") or {})
            result(rid, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=2)}], "isError": False})
        except KeyError:
            error(rid, -32602, f"unknown tool {name!r}")
        except (J.JobError, ValueError, TypeError) as e:
            result(rid, {"content": [{"type": "text", "text": f"invalid request: {e}"}], "isError": True})
        except Exception as e:                                          # never crash the server; report
            print(traceback.format_exc(), file=sys.stderr)
            result(rid, {"content": [{"type": "text", "text": f"internal error: {e}"}], "isError": True})
    elif rid is not None:
        error(rid, -32601, f"method not found: {method}")


def main():
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    J.start_worker()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            error(None, -32700, "parse error")
            continue
        try:
            handle(msg)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            if isinstance(msg, dict) and msg.get("id") is not None:
                error(msg["id"], -32603, f"internal error: {e}")


if __name__ == "__main__":
    main()
