"""af - the AnimationFactory control CLI for AI agents. stdout = ONE JSON document, diagnostics on stderr. One core (af_core.py), also behind the MCP adapter.
  af.py capabilities [--project P]            af.py project_get --project P [--what summary|storyboard|status|all]
  af.py project_put --project P --storyboard-file F --expect-hash H     af.py validate --project P [--storyboard-file F]
  af.py estimate --project P                  af.py preview --project P [--scenes s01,s02] [--background]
  af.py render --project P [--draft] [--background]     af.py jobs --project P [--job-id ID]      af.py artifacts --project P
  af.py call TOOL --json '{...}'              (same call as the MCP tools)
Exit code: 0 ok, 2 needs_changes / waiting_approval / running, 1 error. Approval is NOT a command."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import af_core as core  # noqa: E402


def _run_job(jobfile):
    import os
    rec = json.loads(Path(jobfile).read_text(encoding="utf-8"))
    hb = Path(jobfile).with_suffix(".hb")

    def beat():                                                   # liveness = a fresh heartbeat file (pids are unreliable behind the Windows Store python launcher)
        import threading
        import time
        while True:
            hb.write_text(str(time.time()), encoding="utf-8")
            time.sleep(2)
    import threading
    threading.Thread(target=beat, daemon=True).start()
    with open(rec["log"], "w", encoding="utf-8") as lg:
        code = subprocess.run(rec["argv"], stdout=lg, stderr=subprocess.STDOUT, cwd=str(core.P2)).returncode
    Path(jobfile).with_suffix(".exit").write_text(str(code), encoding="utf-8")


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(argv) >= 2 and argv[0] == "_run_job":
        return _run_job(argv[1]) or 0
    if len(argv) >= 2 and argv[0] == "_preview_worker":
        a = argparse.ArgumentParser()
        a.add_argument("project")
        a.add_argument("--scenes", default="")
        n = a.parse_args(argv[1:])
        r = core.preview(n.project, n.scenes.split(",") if n.scenes else None)
        print(json.dumps(r, ensure_ascii=False))
        return {"ok": 0, "needs_changes": 3}.get(r["status"], 1)
    ap = argparse.ArgumentParser(prog="af", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for t in core.TOOLS:
        sp = sub.add_parser(t["name"], help=t["description"][:80])
        for k, spec in t["inputSchema"]["properties"].items():
            flag = "--" + k.replace("_", "-")
            if spec.get("type") == "boolean":
                sp.add_argument(flag, action="store_true")
            elif spec.get("type") == "object":
                sp.add_argument(flag + "-file", help=f"JSON file for {k}")
            elif spec.get("type") == "array":
                sp.add_argument(flag, help="comma separated")
            else:
                sp.add_argument(flag)
    c = sub.add_parser("call", help="generic: call TOOL --json '{...}'")
    c.add_argument("tool")
    c.add_argument("--json", default="{}")
    a = ap.parse_args(argv)
    if a.cmd == "call":
        name = a.tool
        try:
            args = json.loads(a.json)
            if not isinstance(args, dict):
                raise ValueError("--json must be a JSON object")
        except ValueError as e:
            print(json.dumps({"status": "error", "contract": core.CONTRACT, "errors": [{"code": "INVALID_JSON", "scene_id": None, "shot_id": None, "field": "--json", "message": str(e),
                                                                                       "next_action": "Pass a valid JSON object, e.g. --json '{\"project\": \"name\"}'."}], "charged_calls": 0}, ensure_ascii=False))
            return 1
    else:
        name, args = a.cmd, {}
        t = next(x for x in core.TOOLS if x["name"] == name)
        for k, spec in t["inputSchema"]["properties"].items():
            attr = k
            if spec.get("type") == "object":
                v = getattr(a, attr + "_file", None)
                if v:
                    try:
                        args[k] = json.loads(Path(v).read_text(encoding="utf-8"))
                    except (OSError, ValueError) as e:
                        print(json.dumps({"status": "error", "contract": core.CONTRACT, "errors": [{"code": "BAD_FILE", "scene_id": None, "shot_id": None, "field": k, "message": f"{v}: {e}",
                                                                                                   "next_action": "Pass the path of a readable JSON file."}], "charged_calls": 0}, ensure_ascii=False))
                        return 1
            else:
                v = getattr(a, attr, None)
                if v not in (None, False):
                    args[k] = v.split(",") if spec.get("type") == "array" else v
    try:
        res = core.call(name, args)
    except KeyError:
        res = {"status": "error", "contract": core.CONTRACT, "errors": [{"code": "UNKNOWN_COMMAND", "message": f"unknown command {name!r}", "next_action": "Run af.py --help or capabilities."}]}
    print(json.dumps(res, ensure_ascii=False))
    return {"ok": 0, "error": 1}.get(res.get("status"), 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
