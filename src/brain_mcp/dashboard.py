#!/usr/bin/env python3
"""Read-only dashboard: Kanban, changes, errors, sessions.  Stdlib HTTP only."""
import glob
import html
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config

TASKS = os.path.join(config.VAULT, "tasks")
COLS = [("backlog", "Backlog"), ("active", "Active"), ("blocked", "Blocked"), ("done", "Done")]
CHANGE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"}

CSS = """
body{font:14px -apple-system,Segoe UI,sans-serif;margin:0;background:#0f1117;color:#e6e6e6}
a{color:#6ea8fe;text-decoration:none}a:hover{text-decoration:underline}
header{background:#161a23;padding:12px 20px;border-bottom:1px solid #262b36;font-size:18px;font-weight:600}
header a{margin-right:18px;font-size:14px}.wrap{padding:18px 20px}
.kanban{display:flex;gap:14px;align-items:flex-start}.col{flex:1;background:#161a23;border:1px solid #262b36;border-radius:8px;padding:10px;min-width:0}
.col h3{margin:0 0 8px;font-size:13px;text-transform:uppercase;color:#9aa4b2}.card{background:#1d2230;border:1px solid #2b313f;border-radius:6px;padding:7px 9px;margin-bottom:6px;font-size:12px;word-break:break-word}
.badge{background:#2b313f;border-radius:10px;padding:1px 8px;font-size:11px;color:#9aa4b2}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #262b36;padding:6px 10px;text-align:left;font-size:13px;vertical-align:top}
.ev{font-family:ui-monospace,monospace;font-size:12px;color:#c9d1d9;word-break:break-all}.tool{color:#7ee787}.evt{color:#d2a8ff}.ts{color:#8b949e;white-space:nowrap}
.ok{color:#7ee787}.fail{color:#ff7b72;font-weight:600}h2{font-size:16px}.day{margin:18px 0 6px;color:#9aa4b2;font-size:13px;text-transform:uppercase}
"""


def page(title: str, body: str) -> str:
    nav = (
        "<header>Brain "
        "<a href=/>Kanban</a>"
        "<a href=/changes>Changes</a>"
        "<a href=/errors>Errors</a>"
        "<a href=/sessions>Sessions</a>"
        "</header>"
    )
    return f"<!doctype html><meta charset=utf-8><title>{title}</title><style>{CSS}</style>{nav}<div class=wrap>{body}</div>"


def esc(value: object) -> str:
    return html.escape(str(value))


def cards(column: str) -> list[str]:
    directory = os.path.join(TASKS, column)
    if not os.path.isdir(directory):
        return []
    return [
        f"<div class=card>{esc(os.path.basename(path)[:-3])}</div>"
        for path in sorted(glob.glob(f"{directory}/*.md"))
    ]


def days() -> list[str]:
    return sorted(
        [path for path in glob.glob(f"{config.AGENT_LOGS_DIR}/*") if os.path.isdir(path)],
        reverse=True,
    )


def read_events(day_path: str) -> list[dict]:
    events: list[dict] = []
    for file_path in glob.glob(f"{day_path}/*.jsonl"):
        session_id = os.path.basename(file_path)[:-6]
        for line in open(file_path, errors="ignore"):
            try:
                event = json.loads(line)
                event["_sid"] = session_id
                events.append(event)
            except json.JSONDecodeError:
                continue
    events.sort(key=lambda item: item.get("ts", ""))
    return events


def is_change(event: dict) -> bool:
    tool = event.get("tool") or ""
    if tool in CHANGE_TOOLS:
        return True
    lowered = tool.lower()
    return any(
        keyword in lowered
        for keyword in ("write", "append", "brain_log", "brain_lesson", "create", "update", "delete")
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        return

    def send_html(self, content: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode())

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/":
            self.send_html(self.kanban())
        elif parsed.path == "/changes":
            self.send_html(self.changes())
        elif parsed.path == "/errors":
            self.send_html(self.errors())
        elif parsed.path == "/sessions":
            self.send_html(self.sessions())
        elif parsed.path == "/session":
            self.send_html(self.session(query.get("d", [""])[0], query.get("s", [""])[0]))
        else:
            self.send_response(404)
            self.end_headers()

    def kanban(self) -> str:
        columns = ""
        for column, label in COLS:
            items = cards(column)
            columns += (
                f"<div class=col><h3>{label} <span class=badge>{len(items)}</span></h3>"
                f"{''.join(items)}</div>"
            )
        return page("Kanban", f"<div class=kanban>{columns}</div>")

    def changes(self) -> str:
        body = "<h2>Agent changes</h2>"
        found = False
        for day_path in days():
            events = [event for event in read_events(day_path) if is_change(event)]
            if not events:
                continue
            found = True
            day_name = os.path.basename(day_path)
            rows = "".join(self._change_row(event) for event in events)
            body += (
                f"<div class=day>{day_name} — {len(events)} changes</div>"
                f"<table><tr><th>Time</th><th>Tool</th><th>Target</th><th>OK</th><th>Session</th></tr>{rows}</table>"
            )
        if not found:
            body += "<p>No changes logged yet.</p>"
        return page("Changes", body)

    def errors(self) -> str:
        body = "<h2>Agent errors</h2>"
        found = False
        for day_path in days():
            events = [event for event in read_events(day_path) if event.get("ok") is False]
            if not events:
                continue
            found = True
            day_name = os.path.basename(day_path)
            rows = "".join(self._error_row(event) for event in events)
            body += (
                f"<div class=day>{day_name} — <span class=fail>{len(events)} errors</span></div>"
                f"<table><tr><th>Time</th><th>Tool</th><th>Detail</th><th>Session</th></tr>{rows}</table>"
            )
        if not found:
            body += "<p>No errors logged yet.</p>"
        return page("Errors", body)

    def sessions(self) -> str:
        rows = ""
        for day_path in days():
            day_name = os.path.basename(day_path)
            for file_path in sorted(glob.glob(f"{day_path}/*.jsonl"), key=os.path.getmtime, reverse=True):
                session_id = os.path.basename(file_path)[:-6]
                count = sum(1 for _ in open(file_path, errors="ignore"))
                modified = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%H:%M")
                rows += (
                    f"<tr><td>{day_name}</td><td>{modified}</td>"
                    f"<td><a href='/session?d={day_name}&s={esc(session_id)}'>{esc(session_id[:20])}</a></td>"
                    f"<td>{count}</td></tr>"
                )
        if not rows:
            rows = "<tr><td colspan=4>No session logs yet.</td></tr>"
        return page("Sessions", f"<h2>Sessions</h2><table><tr><th>Date</th><th>Time</th><th>Session</th><th>Events</th></tr>{rows}</table>")

    def session(self, day: str, session_id: str) -> str:
        file_path = f"{config.AGENT_LOGS_DIR}/{os.path.basename(day)}/{os.path.basename(session_id)}.jsonl"
        if not os.path.isfile(file_path):
            return page("404", "<p>Session not found.</p>")

        rows = ""
        for line in open(file_path, errors="ignore"):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            target = event.get("file") or event.get("cmd") or event.get("desc") or ""
            rows += (
                f"<tr><td class=ts>{esc((event.get('ts') or '')[11:19])}</td>"
                f"<td class=evt>{esc(event.get('event'))}</td>"
                f"<td class=tool>{esc(event.get('tool') or '')}</td>"
                f"<td class=ev>{esc(str(target)[:160])}</td></tr>"
            )
        return page(
            f"session {session_id}",
            f"<h2>{esc(day)} / {esc(session_id[:24])}</h2>"
            f"<p><a href=/sessions>← sessions</a></p>"
            f"<table><tr><th>Time</th><th>Event</th><th>Tool</th><th>Target</th></tr>{rows}</table>",
        )

    def _change_row(self, event: dict) -> str:
        target = event.get("file") or event.get("cmd") or event.get("desc") or ""
        ok = event.get("ok")
        status = (
            "<span class=ok>✓</span>"
            if ok is True
            else ("<span class=fail>✗</span>" if ok is False else "")
        )
        return (
            f"<tr><td class=ts>{esc((event.get('ts') or '')[11:19])}</td>"
            f"<td class=tool>{esc(event.get('tool') or '')}</td>"
            f"<td class=ev>{esc(str(target)[:200])}</td>"
            f"<td>{status}</td>"
            f"<td class=ts>{esc(event.get('_sid', '')[:8])}</td></tr>"
        )

    def _error_row(self, event: dict) -> str:
        target = event.get("cmd") or event.get("file") or event.get("desc") or ""
        return (
            f"<tr><td class=ts>{esc((event.get('ts') or '')[11:19])}</td>"
            f"<td class=tool>{esc(event.get('tool') or '')}</td>"
            f"<td class=ev>{esc(str(target)[:220])}</td>"
            f"<td class=ts>{esc(event.get('_sid', '')[:8])}</td></tr>"
        )


def main() -> None:
    ThreadingHTTPServer((config.DASHBOARD_HOST, config.DASHBOARD_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
