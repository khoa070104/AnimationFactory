"""Test double for `agy --print ... --output-format stream-json` (used through AGY_CMD). Modes via FAKE_AGY_MODE:
 ok (default) | notool | hang | nofile | decoy_response (response points at a file OUTSIDE this job's conversation) | decoy_newer (a newer image exists elsewhere)
FAKE_AGY_COUNT = file that gets one line appended per invocation. AGY_HOME = fake home whose brain/ holds conversations."""
import json
import os
import sys
import time
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

args = sys.argv[1:]
prompt = args[args.index("--print") + 1]
logf = Path(args[args.index("--log-file") + 1])
mode = os.environ.get("FAKE_AGY_MODE", "ok")
brain = Path(os.environ["AGY_HOME"]) / "brain"
if "--json-schema" in args:                       # LLM mode: structured answer produced by fake_llm_responder from the real prompt
    sys.path.insert(0, str(Path(__file__).parent))
    import fake_llm_responder as FL
    task = FL.task_of(prompt)
    model = args[args.index("--model") + 1] if "--model" in args else "?"
    if os.environ.get("FAKE_AGY_COUNT"):
        with open(os.environ["FAKE_AGY_COUNT"], "a", encoding="utf-8") as f:
            f.write(f"llm {task} {model}\n")
    logf.write_text(f'I0000 model_config_manager.go:340] Propagating selected model override to backend: label="Fake LLM ({model})"\n', encoding="utf-8")
    print(json.dumps({"event": "init", "init": {}}), flush=True)
    if os.environ.get("FAKE_LLM_MODE") == "hang":
        time.sleep(120)
    if task == "research_facts":
        print(json.dumps({"event": "step_update", "step_update": {"step_type": "tool", "tool_name": "search_web", "state": "DONE"}}), flush=True)
    data = FL.respond(task, prompt, None, os.environ.get("FAKE_LLM_MODE", "ok"))
    print(json.dumps({"event": "result", "result": {"conversation_id": "llm-conv", "status": "SUCCESS", "response": json.dumps(data, ensure_ascii=False), "structured_output": data,
                                                   "usage": {"input_tokens": 100, "output_tokens": 50, "thinking_tokens": 0, "total_tokens": 150}, "denied_actions": []}}), flush=True)
    sys.exit(0)
if os.environ.get("FAKE_AGY_COUNT"):
    with open(os.environ["FAKE_AGY_COUNT"], "a", encoding="utf-8") as f:
        f.write("call\n")
logf.write_text('I0000 model_config_manager.go:340] Propagating selected model override to backend: label="Fake Model (High)"\n', encoding="utf-8")


def art(path):
    im = Image.new("RGB", (512, 512), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((96, 96, 416, 416), fill=(250, 200, 61), outline=(29, 29, 31), width=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=95)


def emit(o):
    print(json.dumps(o), flush=True)


emit({"event": "init", "init": {"cwd": os.getcwd(), "tools": ["generate_image"], "permission_mode": "request-review"}})
if mode == "hang":
    time.sleep(120)
conv, sub = str(uuid.uuid4()), str(uuid.uuid4())
img = brain / conv / "result_123.jpg"
if mode == "notool":
    emit({"event": "result", "result": {"conversation_id": conv, "status": "SUCCESS", "response": "I drew it with code.", "usage": {"total_tokens": 10}, "denied_actions": []}})
    sys.exit(0)
if mode != "nofile":
    art(img)
if mode == "decoy_newer":
    art(brain / "other-conversation" / "newer_decoy.jpg")
decoy = brain / "other-conversation" / "decoy.jpg"
if mode == "decoy_response":
    art(decoy)
tr = brain / sub / ".system_generated" / "logs" / "transcript.jsonl"
tr.parent.mkdir(parents=True, exist_ok=True)
if mode not in ("nofile", "decoy_response"):
    tr.write_text(json.dumps({"step_index": 2, "content": f"Generated image is saved at {img}.", "media": [{"mime_type": "image/jpeg", "uri": "file:///" + str(img).replace("\\", "/")}]}) + "\n", encoding="utf-8")
else:
    tr.write_text(json.dumps({"step_index": 1, "content": "nothing"}) + "\n", encoding="utf-8")
emit({"event": "step_update", "step_update": {"step_type": "subagent", "tool_name": "invoke_subagent", "state": "DONE", "subagent_info": {"subagents": [
    {"type_name": "image-generator", "conversation_id": sub, "log_uri": "file:///" + str(tr).replace("\\", "/")}]}}})
shown = decoy if mode == "decoy_response" else img
emit({"event": "result", "result": {"conversation_id": conv, "status": "SUCCESS", "response": f"[{shown}](file:///{shown}), tool: generate_image",
                                     "usage": {"total_tokens": 1234}, "denied_actions": []}})
