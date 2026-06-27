import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

PROJECTS_DIR = Path(os.environ.get("PROJECTS_DIR", Path.home() / ".claude" / "projects"))

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; background: #0d1117; color: #c9d1d9; font-size: 14px; }
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.container { max-width: 900px; margin: 0 auto; padding: 24px 16px; }
h1 { font-size: 20px; font-weight: 600; margin-bottom: 4px; color: #e6edf3; }
.subtitle { color: #8b949e; font-size: 13px; margin-bottom: 24px; }
.session-list { display: flex; flex-direction: column; gap: 8px; }
.session-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px 16px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.session-card:hover { border-color: #58a6ff; }
.session-title { font-size: 14px; font-weight: 500; color: #e6edf3; }
.session-meta { font-size: 12px; color: #8b949e; margin-top: 4px; }
.badge { display: inline-block; padding: 1px 7px; border-radius: 12px; font-size: 11px; font-weight: 500; }
.badge-project { background: #1f2d3d; color: #58a6ff; border: 1px solid #1f4068; }
.badge-turns { background: #1f2d1f; color: #3fb950; border: 1px solid #1f4028; }
.turn { margin-bottom: 16px; border-radius: 8px; overflow: hidden; }
.turn-header { padding: 8px 14px; font-size: 12px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
.turn-user .turn-header { background: #1c2b3a; color: #58a6ff; }
.turn-assistant .turn-header { background: #1a2d1a; color: #3fb950; }
.turn-system .turn-header { background: #1e1e1e; color: #8b949e; }
.turn-body { padding: 12px 14px; background: #161b22; white-space: pre-wrap; word-break: break-word; line-height: 1.6; font-size: 13px; }
.tool-call { display: inline-block; background: #2d1f3a; border: 1px solid #6e40c9; color: #bc8cff; border-radius: 4px; padding: 1px 8px; margin: 2px 2px; font-size: 12px; }
.token-info { font-size: 11px; color: #8b949e; padding: 6px 14px; background: #0d1117; border-top: 1px solid #21262d; }
details summary { cursor: pointer; padding: 8px 14px; background: #1e1e1e; color: #8b949e; font-size: 12px; }
details summary:hover { color: #c9d1d9; }
details .turn-body { background: #161b22; }
.back { display: inline-block; margin-bottom: 20px; color: #58a6ff; font-size: 13px; }
.breadcrumb { color: #8b949e; font-size: 13px; margin-bottom: 6px; }
.empty { color: #8b949e; padding: 32px; text-align: center; }
"""

def html_page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head><body><div class="container">{body}</div></body></html>"""

def decode_project_name(encoded: str) -> str:
    return encoded.replace("-", "/").lstrip("/")

def iter_sessions():
    if not PROJECTS_DIR.exists():
        return
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        for f in project_dir.iterdir():
            if f.suffix == ".jsonl" and f.stem.count("-") == 4:
                yield project_dir.name, f

def parse_session(path: Path):
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries

def get_session_title(entries) -> Optional[str]:
    for e in entries:
        if e.get("type") == "custom-title":
            t = e.get("title") or e.get("message", {}).get("content", "")
            if isinstance(t, str) and t.strip():
                return t.strip()
    return None

def count_turns(entries) -> int:
    return sum(1 for e in entries if e.get("type") in ("user", "assistant"))

def format_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        local = dt.astimezone()
        return local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts[:16] if ts else "—"

def render_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "thinking":
                    parts.append(f"<details><summary>🧠 thinking ({len(block.get('thinking',''))} chars)</summary><div class='turn-body'>{block.get('thinking','')[:2000]}</div></details>")
                # image/other blocks skipped
        return "\n".join(p for p in parts if p)
    return ""

def render_tool_calls(content) -> str:
    if not isinstance(content, list):
        return ""
    tools = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    if not tools:
        return ""
    badges = "".join(f'<span class="tool-call">⚙ {t["name"]}</span>' for t in tools)
    return f'<div style="margin-top:8px">{badges}</div>'

def render_token_info(msg: dict) -> str:
    usage = msg.get("usage", {})
    if not usage:
        return ""
    parts = []
    if usage.get("input_tokens"):
        parts.append(f"in:{usage['input_tokens']}")
    if usage.get("output_tokens"):
        parts.append(f"out:{usage['output_tokens']}")
    if usage.get("cache_read_input_tokens"):
        parts.append(f"cache_hit:{usage['cache_read_input_tokens']}")
    if not parts:
        return ""
    model = msg.get("model", "")
    model_short = model.split("-")[-1] if model else ""
    model_tag = f" · {model_short}" if model_short else ""
    return f'<div class="token-info">🪙 {" · ".join(parts)}{model_tag}</div>'

@app.get("/", response_class=HTMLResponse)
def index():
    sessions = []
    for project_enc, path in iter_sessions():
        try:
            entries = parse_session(path)
            mtime = path.stat().st_mtime
            title = get_session_title(entries) or path.stem[:8]
            turns = count_turns(entries)
            first_ts = next((e.get("timestamp", "") for e in entries if e.get("timestamp")), "")
            sessions.append({
                "project_enc": project_enc,
                "project": decode_project_name(project_enc),
                "session_id": path.stem,
                "title": title,
                "turns": turns,
                "mtime": mtime,
                "ts": format_ts(first_ts),
            })
        except Exception:
            pass

    sessions.sort(key=lambda s: s["mtime"], reverse=True)

    if not sessions:
        body = '<h1>Claude Code Sessions</h1><div class="empty">No sessions found in ' + str(PROJECTS_DIR) + '</div>'
        return HTMLResponse(html_page("Claude Sessions", body))

    cards = []
    for s in sessions:
        proj_parts = s["project"].split("/")
        proj_label = proj_parts[-1] if proj_parts else s["project"]
        cards.append(f"""
<a href="/session/{s['project_enc']}/{s['session_id']}" style="display:block">
  <div class="session-card">
    <div>
      <div class="session-title">{s['title']}</div>
      <div class="session-meta">
        <span class="badge badge-project">{proj_label}</span>
        &nbsp;<span class="badge badge-turns">{s['turns']} turns</span>
        &nbsp;{s['ts']}
      </div>
    </div>
  </div>
</a>""")

    body = f"""
<h1>Claude Code Sessions</h1>
<div class="subtitle">{PROJECTS_DIR} · {len(sessions)} sessions</div>
<div class="session-list">{"".join(cards)}</div>
"""
    return HTMLResponse(html_page("Claude Sessions", body))


@app.get("/session/{project_enc}/{session_id}", response_class=HTMLResponse)
def session_detail(project_enc: str, session_id: str):
    path = PROJECTS_DIR / project_enc / f"{session_id}.jsonl"
    if not path.exists():
        raise HTTPException(404, "Session not found")

    entries = parse_session(path)
    title = get_session_title(entries) or session_id[:8]
    proj_label = decode_project_name(project_enc).split("/")[-1]

    turns_html = []
    for e in entries:
        etype = e.get("type")
        ts = format_ts(e.get("timestamp", ""))

        if etype == "user":
            msg = e.get("message", {})
            text = render_content(msg.get("content", ""))
            if not text.strip():
                continue
            turns_html.append(f"""
<div class="turn turn-user">
  <div class="turn-header"><span>👤 User</span><span>{ts}</span></div>
  <div class="turn-body">{text}</div>
</div>""")

        elif etype == "assistant":
            msg = e.get("message", {})
            content = msg.get("content", [])
            text = render_content(content)
            tools = render_tool_calls(content)
            tokens = render_token_info(msg)
            if not text.strip() and not tools:
                continue
            turns_html.append(f"""
<div class="turn turn-assistant">
  <div class="turn-header"><span>🤖 Assistant</span><span>{ts}</span></div>
  <div class="turn-body">{text}{tools}</div>
  {tokens}
</div>""")

        elif etype in ("system", "attachment"):
            msg = e.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, list):
                content = render_content(content)
            if not content or not str(content).strip():
                continue
            preview = str(content)[:300]
            turns_html.append(f"""
<div class="turn turn-system">
  <details>
    <summary>⚙ {etype} · {ts}</summary>
    <div class="turn-body">{preview}</div>
  </details>
</div>""")

    body = f"""
<a class="back" href="/">← All sessions</a>
<div class="breadcrumb">{proj_label}</div>
<h1>{title}</h1>
<div class="subtitle" style="margin-bottom:24px">{session_id}</div>
{"".join(turns_html) if turns_html else '<div class="empty">No turns found</div>'}
"""
    return HTMLResponse(html_page(title, body))
