"""Planning of a character's actions from the storyboard: cue phrase -> start time (seconds from the scene start), per-action parameters.
Shared by BOTH renderers (build_video.py for Craft, export_remotion.py for Remotion) so they can never disagree about WHEN something happens."""
import sbload

# seconds between the START of an action and its peak: the action starts early so that the peak lands on the cue
PEAK = {"point": 0.45, "cheer": 0.5, "cheek": 0.5, "shrug": 0.3, "hold_phone": 0.5, "nod": 0.0, "wave": 0.4, "enter": 0.0, "write": 0.5, "carry": 0.5}


def plan_actions(actions, face, T, held=()):
    """actions: storyboard action dicts; face: the character's face (default for point); T(phrase) -> seconds; held: hands (L/R) that hold a prop.
    -> [{"name", "T", "params", "stay"}]"""
    out = []
    for ac in actions:
        params = {k: v for k, v in ac.items() if k not in ("name", "at", "cue", "cues", "stay")}
        params.update(sbload.arm_params(ac["name"], held))
        if ac["name"] == "point":
            params.setdefault("face", face)
        if ac["name"] == "point_seq":
            params["times"] = [T(c) for c in ac["cues"]]
            params.setdefault("face", face)
            t0 = params["times"][0] - 0.45
        elif "cue" in ac:
            t0 = max(0.0, T(ac["cue"]) - PEAK.get(ac["name"], 0.0))
        else:
            t0 = ac.get("at", 0.0)
        out.append({"name": ac["name"], "T": round(t0, 3), "params": params, "stay": bool(ac.get("stay"))})
    return out
