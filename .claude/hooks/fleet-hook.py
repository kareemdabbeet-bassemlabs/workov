#!/usr/bin/env python3
"""Claude Code hook: record a worker's activity into job/hook-status.json.

Reads one hook event as JSON on stdin. Only acts when the marker
job/ticket.json (written for fleet workers) is found by walking up from the
cwd; any other session is left untouched. Always exits 0 and prints nothing
to stdout, so it can never block or alter a session. Failures are logged to
<main>/job/logs/fleet-hook.log when the marker names an existing main checkout.
"""
import json
import os
import sys
import time

MAX_SUBAGENTS = 20
MAX_ATTENTION = 300
ATTENTION_TYPES = {"permission_prompt", "idle_prompt", "agent_needs_input", "elicitation_dialog"}
EVENTS = {"SessionStart", "PostToolUse", "SubagentStop", "Stop", "Notification", "SessionEnd"}


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(main, msg):
    try:
        if not isinstance(main, str) or not os.path.isdir(main):
            return
        d = os.path.join(main, "job", "logs")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "fleet-hook.log"), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (now(), " ".join(str(msg).split())))
    except Exception:
        pass


def write_atomic(path, data):
    tmp = os.path.join(os.path.dirname(path), ".hook-status.%d.tmp" % os.getpid())
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_status(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def find_worktree(start):
    """Walk up from start to the dir holding job/ticket.json.

    Stops after the first directory containing a .git entry, and at the root.
    """
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, "job", "ticket.json")):
            return d
        if os.path.lexists(os.path.join(d, ".git")):
            return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def apply_event(st, ev, marker, event, ts):
    st["version"] = 1
    st["ticket"] = marker.get("ticket")
    st["kind"] = marker.get("kind")
    if ev.get("session_id"):
        st["sessionId"] = ev["session_id"]
    if ev.get("transcript_path"):
        st["transcriptPath"] = ev["transcript_path"]
    resets = event == "SessionStart" and ev.get("source") in (None, "", "startup")
    if resets or not st.get("startedAt"):
        st["startedAt"] = ts
    st.setdefault("lastTool", None)
    st.setdefault("lastActivityAt", None)
    if not isinstance(st.get("subagents"), list):
        st["subagents"] = []
    st["attention"] = None
    st["attentionType"] = None

    if event == "PostToolUse":
        st["lastTool"] = ev.get("tool_name")
        st["lastActivityAt"] = ts
    if event == "SubagentStop":
        st["subagents"].append({"type": ev.get("agent_type") or "unknown", "stoppedAt": ts})
        st["subagents"] = st["subagents"][-MAX_SUBAGENTS:]
        st["lastActivityAt"] = ts

    if event == "Stop":
        st["state"] = "idle"
    elif event == "Notification":
        st["state"] = "needs-attention"
        st["attention"] = str(ev.get("message") or "")[:MAX_ATTENTION]
        st["attentionType"] = ev.get("notification_type")
    elif event == "SessionEnd":
        st["state"] = "ended"
    else:
        st["state"] = "active"
    st["updatedAt"] = ts


def main():
    main_dir = None
    try:
        try:
            ev = json.load(sys.stdin)
        except ValueError:
            return 0
        if not isinstance(ev, dict):
            return 0
        event = ev.get("hook_event_name")
        if event not in EVENTS:
            return 0
        if event == "SubagentStop" and ev.get("agent_type") == "":
            return 0  # internal agent
        if event == "Notification" and ev.get("notification_type", None) not in ATTENTION_TYPES | {None}:
            return 0
        root = find_worktree(ev.get("cwd") or os.getcwd())
        if root is None:
            return 0
        with open(os.path.join(root, "job", "ticket.json"), encoding="utf-8") as f:
            marker = json.load(f)
        if not isinstance(marker, dict):
            return 0
        main_dir = marker.get("main")
        status_path = os.path.join(root, "job", "hook-status.json")
        st = load_status(status_path)
        apply_event(st, ev, marker, event, now())
        write_atomic(status_path, st)
    except Exception as e:
        log(main_dir, "fleet-hook error: %s: %s" % (type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
