import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

PROJECTS_DIR = Path(os.environ.get("PROJECTS_DIR", Path.home() / ".claude" / "projects"))
GAMIFY_DIR = Path(os.environ.get("GAMIFY_DIR", Path.home() / ".gamify"))
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Theme ─────────────────────────────────────────────────────────────────────
# Pixel-art RPG dashboard. Palette lives in :root; the markup leans on a small set
# of utility classes (.parch, .inset, .bar, .btn-pix, .tab …) that reproduce the
# design's layered box-shadow "frames" without repeating them in every f-string.
FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700'
    '&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">'
)

CSS = """
:root{
  --bg:#0b1a12; --forest:#12261a; --frame:#3a2a1a; --wood:#5c3d22; --wood-dk:#33200f;
  --wood-mid:#7b5c34; --parch:#e9dab4; --parch2:#dfcda4; --parch3:#dcc9a0;
  --gold:#f2c14e; --gold2:#ffd27a; --amber:#a2601c; --brown:#6b5330; --brown2:#8a6a3a;
  --green:#5f9c4a; --green2:#8fd86a; --cream:#f7e6b8; --moss:#8fbf8a; --leaf:#cfe6c4;
}
*{box-sizing:border-box;margin:0;padding:0;image-rendering:pixelated;}
html,body{background:var(--bg);}
body{font-family:'JetBrains Mono',monospace;color:#e9dab4;font-size:14px;overflow-x:hidden;}
a{color:var(--gold);text-decoration:none;}
a:hover{color:var(--gold2);}
.pix{font-family:'Silkscreen',monospace;}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-track{background:#12261a}
::-webkit-scrollbar-thumb{background:#3f6b40;border:2px solid #12261a}

@keyframes gm-float{0%{transform:translateY(0)}50%{transform:translateY(-10px)}100%{transform:translateY(0)}}
@keyframes gm-pop{0%{transform:scale(.85);opacity:0}60%{transform:scale(1.04)}100%{transform:scale(1);opacity:1}}
@keyframes gm-fade{from{opacity:0}to{opacity:1}}

/* fixed background layers */
.bg-gif{position:fixed;inset:0;background:url('/static/background.gif') center/cover;image-rendering:pixelated;z-index:0}
.bg-grad{position:fixed;inset:0;z-index:1;pointer-events:none;background:linear-gradient(180deg,rgba(6,18,12,.72) 0%,rgba(6,18,12,.35) 38%,rgba(6,18,12,.82) 100%)}
.bg-scan{position:fixed;inset:0;z-index:1;pointer-events:none;opacity:.5;mix-blend-mode:multiply;background:repeating-linear-gradient(0deg,rgba(0,0,0,.14) 0 1px,transparent 1px 3px)}

/* header */
header.top{position:relative;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:24px;padding:18px 34px;flex-wrap:wrap}
.logo{width:26px;height:26px;background:var(--gold);box-shadow:6px 0 0 -2px #0b1a12,0 6px 0 -2px #0b1a12,inset 0 0 0 4px #8a5a20}
.navwrap{display:flex;background:#2a1d10;padding:5px;box-shadow:0 0 0 3px #6b4a24,0 0 0 6px #1a1109,0 8px 0 rgba(0,0,0,.35)}
.tab{font-family:'Silkscreen',monospace;font-size:11px;letter-spacing:1px;padding:11px 22px;border:0;cursor:pointer;text-shadow:1px 1px 0 rgba(0,0,0,.5);display:inline-block}
.tab:hover{filter:brightness(1.18)}
.tab-on{background:var(--gold);color:#2a1d10;box-shadow:inset 0 -4px 0 rgba(0,0,0,.22)}
.tab-off{background:transparent;color:#d8c79a}
.chip{display:flex;align-items:center;gap:7px;background:rgba(10,26,17,.75);padding:8px 12px;box-shadow:0 0 0 2px #4d7a45}

/* panels */
main{position:relative;z-index:4}
.wrap{max-width:1240px;margin:0 auto;padding:14px 40px 70px}
.parch{background:var(--parch);box-shadow:0 0 0 3px var(--frame),0 0 0 7px var(--wood-mid),0 12px 0 rgba(0,0,0,.4);background-image:repeating-linear-gradient(180deg,rgba(120,90,50,.045) 0 2px,transparent 2px 4px)}
.inset{background:var(--parch2);box-shadow:inset 0 0 0 3px #b79a68}
.dash{height:3px;background:repeating-linear-gradient(90deg,#b79a68 0 5px,transparent 5px 10px)}
.dash2{height:2px;background:repeating-linear-gradient(90deg,#b79a68 0 4px,transparent 4px 8px)}
.sect{font-family:'Silkscreen',monospace;font-size:13px;color:var(--frame)}
.dark{background:rgba(12,28,18,.86);box-shadow:0 0 0 3px #4d7a45,0 0 0 7px #14261a}

/* bars */
.bar{height:22px;background:#c3ab7c;box-shadow:inset 0 0 0 3px var(--frame);position:relative;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(180deg,#ffd97a 0%,#f2a93b 55%,#c9781d 100%);transition:width 1.2s cubic-bezier(.2,.9,.2,1)}
.bar-sm{height:12px;background:#c3ab7c;box-shadow:inset 0 0 0 2px #8a6a3a;overflow:hidden}
.bar-sm > i{display:block;height:100%;background:#5f9c4a}
.bar-grn{height:14px;background:#16301d;box-shadow:inset 0 0 0 2px #35603a;overflow:hidden}
.bar-grn > i{display:block;height:100%;background:linear-gradient(180deg,#8fd86a,#4f9440)}

/* buttons */
.btn-pix{font-family:'Silkscreen',monospace;border:0;cursor:pointer;display:inline-block;text-align:center;box-shadow:0 0 0 2px var(--frame),0 3px 0 rgba(0,0,0,.3)}
.btn-pix:hover{filter:brightness(1.12)}
.btn-grn{background:var(--green);color:#f7f0d8}
.btn-mut{background:#b79a68;color:#6b5330;cursor:default}

/* pills */
.pill{font-size:8.5px;letter-spacing:1.6px;padding:4px 7px;text-transform:uppercase;color:var(--parch);background:var(--frame)}

.empty{color:var(--leaf);padding:32px;text-align:center;background:rgba(10,26,17,.6);box-shadow:0 0 0 2px #35603a}

/* overlays */
.overlay{display:none;position:fixed;inset:0;z-index:60;background:rgba(4,12,8,.74);align-items:center;justify-content:center;padding:24px}
.overlay.open{display:flex;animation:gm-fade .25s ease both}
.modal{animation:gm-pop .3s steps(4) both}

@media (max-width:720px){.wrap{padding:14px 16px 60px}header.top{padding:14px 16px}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
"""


def html_page(title: str, active: str, state: dict, body: str, extra: str = "") -> str:
    """Full-bleed shell: background layers + header + page main content."""
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>{FONTS}<style>{CSS}</style>
</head><body>
<div class="bg-gif"></div><div class="bg-grad"></div><div class="bg-scan"></div>
{header_html(active, state)}
<main>{body}</main>
{extra}
</body></html>"""


def header_html(active: str, state: dict) -> str:
    profile = state.get("profile", {}) or {}
    player = profile.get("player", {}) or {}
    name = player.get("name", "Adventurer")
    pclass = player.get("class", "Engineer")
    level = profile.get("level", 1)
    streak = (profile.get("streak", {}) or {}).get("count", 0)

    def tab(href, key, label):
        cls = "tab tab-on" if key == active else "tab tab-off"
        return f'<a href="{href}" class="{cls}">{label}</a>'

    tabs = (
        tab("/", "home", "HOME")
        + tab("/sessions", "sessions", "SESSIONS")
        + tab("/profile", "profile", "PROFILE")
        + tab("/guildboard", "guildboard", "GUILDBOARD")
    )
    return f"""
<header class="top">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo"></div>
    <div style="display:flex;flex-direction:column;gap:2px">
      <span class="pix" style="font-size:15px;letter-spacing:1px;color:var(--cream);text-shadow:2px 2px 0 #06120c">GAMIFY</span>
      <span style="font-size:9px;letter-spacing:2px;color:var(--moss);text-transform:uppercase">CLAUDE RPG FRAMEWORK</span>
    </div>
  </div>
  <nav class="navwrap">{tabs}</nav>
  <div style="display:flex;align-items:center;gap:16px">
    <div class="chip">
      <span style="color:#ff9a4d;font-size:13px">▲</span>
      <span class="pix" style="font-size:11px;color:var(--gold2)">{streak}</span>
      <span style="font-size:9px;color:var(--moss);letter-spacing:1px">DAY STREAK</span>
    </div>
    <div class="chip" style="gap:9px;padding:7px 12px">
      <div style="width:26px;height:26px;background:#4d7a45;box-shadow:inset 0 0 0 3px #1a2f18"></div>
      <div style="display:flex;flex-direction:column">
        <span class="pix" style="font-size:10px;color:var(--cream)">{name}</span>
        <span style="font-size:9px;color:var(--moss)">Lv {level} · {pclass}</span>
      </div>
    </div>
  </div>
</header>"""


# ── Session transcript helpers (unchanged data logic) ──────────────────────────
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

def get_first_user_text(entries, limit: int = 60) -> Optional[str]:
    for e in entries:
        if e.get("type") != "user":
            continue
        content = e.get("message", {}).get("content", "")
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    break
                if isinstance(block, str):
                    text = block
                    break
        text = " ".join(text.split())
        if not text or text.startswith(("<", "[Request", "Caveat:")):
            continue
        return text[:limit] + ("…" if len(text) > limit else "")
    return None

def session_label(entries, stem: str) -> str:
    return get_session_title(entries) or get_first_user_text(entries) or stem[:8]

def count_turns(entries) -> int:
    return sum(1 for e in entries if e.get("type") in ("user", "assistant"))

def count_tool_calls(entries) -> int:
    n = 0
    for e in entries:
        if e.get("type") != "assistant":
            continue
        content = e.get("message", {}).get("content", [])
        if isinstance(content, list):
            n += sum(1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use")
    return n

def format_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts[:16] if ts else "—"

def parse_ts(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None

def relative_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    secs = (now - dt).total_seconds()
    if secs < 60:
        return "just now"
    mins = int(secs // 60)
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days}d ago"
    return f"{days // 7}w ago"

def latest_entry_ts(entries) -> Optional[datetime]:
    latest = None
    for e in entries:
        dt = parse_ts(e.get("timestamp", ""))
        if dt and (latest is None or dt > latest):
            latest = dt
    return latest

def today_local_str() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d")


# ── Gamify state ───────────────────────────────────────────────────────────────
def load_json(name: str, default):
    path = GAMIFY_DIR / name
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return default

def load_state():
    return {
        "profile": load_json("profile.json", {}),
        "quests": load_json("quests.json", {}),
        "achievements": load_json("achievements.json", {}),
        "sessions": load_json("sessions.json", {}),
    }

# checkins.json is VIEWER-OWNED (mood / daily check-in). It is deliberately NOT one
# of the four gm-quest-tracker "sacred" files, so writing it here does not violate
# the state-write contract. It is the only file this app ever writes.
def load_checkins() -> dict:
    return load_json("checkins.json", {"days": {}})

def save_checkin(date: str, mood: Optional[str]):
    data = load_checkins()
    if not isinstance(data, dict):
        data = {}
    days = data.setdefault("days", {})
    days[date] = {
        "mood": mood,
        "checkedInAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    GAMIFY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(GAMIFY_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, str(GAMIFY_DIR / "checkins.json"))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def experiences_since_claim():
    """Sessions whose latest activity is newer than activity.lastClaimAt.

    The first few (PARSE_LIMIT) are fully parsed for an accurate title, last-active
    time-of-day, and tool-call count; the rest are counted cheaply by mtime.
    """
    sessions_state = load_state()["sessions"]
    last_claim_raw = (sessions_state.get("activity") or {}).get(
        "lastClaimAt", "1970-01-01T00:00:00Z"
    )
    last_claim = parse_ts(last_claim_raw) or datetime(1970, 1, 1, tzinfo=timezone.utc)

    candidates = []
    for project_enc, path in iter_sessions():
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if mtime > last_claim:
            candidates.append((mtime, project_enc, path))

    candidates.sort(key=lambda c: c[0], reverse=True)

    experiences = []
    PARSE_LIMIT = 5
    for i, (mtime, project_enc, path) in enumerate(candidates):
        calls = None
        if i < PARSE_LIMIT:
            try:
                entries = parse_session(path)
                title = session_label(entries, path.stem)
                last_active = latest_entry_ts(entries) or mtime
                calls = count_tool_calls(entries)
            except Exception:
                title = path.stem[:8]
                last_active = mtime
        else:
            title = path.stem[:8]
            last_active = mtime
        experiences.append({
            "project_enc": project_enc,
            "project": decode_project_name(project_enc),
            "session_id": path.stem,
            "title": title,
            "last_active": last_active,
            "rel": relative_time(last_active),
            "time": last_active.astimezone().strftime("%H:%M"),
            "calls": calls,
        })

    return experiences, last_claim


def today_activity():
    """(session_count, tool_calls) for sessions whose mtime is today (local)."""
    today = today_local_str()
    count, calls = 0, 0
    for _proj, path in iter_sessions():
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
        except OSError:
            continue
        if mtime.strftime("%Y-%m-%d") != today:
            continue
        count += 1
        try:
            calls += count_tool_calls(parse_session(path))
        except Exception:
            pass
    return count, calls


def working_days() -> set:
    """Set of local date strings on which any session was active (by mtime)."""
    out = set()
    for _proj, path in iter_sessions():
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
            out.add(mtime.strftime("%Y-%m-%d"))
        except OSError:
            pass
    return out


def xp_today(profile: dict) -> int:
    today = today_local_str()
    total = 0
    for entry in profile.get("xpLedger", []) or []:
        if isinstance(entry, dict) and entry.get("date") == today:
            try:
                total += int(entry.get("xp", 0) or 0)
            except (TypeError, ValueError):
                pass
    return total


def claimed_today(sessions: dict):
    today = today_local_str()
    entries = []
    for c in (sessions.get("activity") or {}).get("claimed", []) or []:
        if not isinstance(c, dict):
            continue
        claimed_at = parse_ts(c.get("claimedAt", ""))
        if claimed_at and claimed_at.astimezone().strftime("%Y-%m-%d") == today:
            entries.append(c)
    entries.sort(key=lambda e: e.get("date", ""))
    total = 0
    for e in entries:
        try:
            total += int(e.get("xp", 0) or 0)
        except (TypeError, ValueError):
            pass
    return entries, total


def achievements_today(achievements: dict):
    today = today_local_str()
    return [a for a in achievements.get("unlocked", []) or []
            if isinstance(a, dict) and a.get("unlockedOn") == today]


TIER_EMOJI = {"light": "🟢", "moderate": "🔵", "heavy": "🟣"}


def xp_bar(profile: dict):
    """(pct_int, label) for the profile XP bar."""
    xp = profile.get("xp", 0)
    xp_next = profile.get("xpForNextLevel", 0) or 0
    pct = int(min(100, (xp / xp_next) * 100)) if xp_next else 100
    label = f"{xp:,} / {xp_next:,}" if xp_next else f"{xp:,}"
    return pct, label


# ── Celebration popup (claimed today) ──────────────────────────────────────────
def celebration_html(state: dict) -> str:
    entries, total_xp = claimed_today(state.get("sessions", {}))
    if not entries:
        return ""

    profile = state.get("profile", {})
    level = profile.get("level", 1)
    title = profile.get("title", "")
    pct, xp_label = xp_bar(profile)
    streak = (profile.get("streak", {}) or {}).get("count", 0)

    rows = []
    for e in entries:
        emoji = TIER_EMOJI.get(e.get("tier", ""), "✨")
        bonus = e.get("questBonus", 0) or 0
        bonus_html = (f'<span style="color:#a2601c;font-size:9px">+{bonus} quest</span>'
                      if bonus else "")
        rows.append(
            f'<div style="display:flex;align-items:center;gap:8px;font-size:11px;color:#4a3520;'
            f'padding:5px 0;border-bottom:1px solid #cdb98a">{emoji}<span>{e.get("date","")}</span>'
            f'<span style="color:#8a6a3a">· {e.get("tier","")}</span>{bonus_html}'
            f'<span class="pix" style="margin-left:auto;color:#a2601c">+{e.get("xp",0)}</span></div>'
        )
    breakdown = "".join(rows)

    ach = achievements_today(state.get("achievements", {}))
    ach_html = ""
    if ach:
        ach_rows = "".join(
            f'<div style="display:flex;gap:8px;font-size:11px;color:#3a2a1a;padding:4px 0">'
            f'{a.get("emoji","🏅")} {a.get("name","")}</div>' for a in ach)
        ach_html = (f'<div style="font-size:8.5px;letter-spacing:1.5px;color:#8a6a3a;'
                    f'text-transform:uppercase;margin:14px 0 6px">New achievements</div>{ach_rows}')

    n = len(entries)
    day_word = "day" if n == 1 else "days"
    return f"""
<div class="overlay" id="celebModal" onclick="if(event.target===this)closeCeleb()">
  <div class="modal parch" style="width:460px;max-width:100%;padding:0;overflow:hidden">
    <div style="background:linear-gradient(180deg,#ffd97a,#f2a93b);padding:20px 24px;color:#3a2a1a">
      <div class="pix" style="font-size:17px">+{total_xp} EXP CLAIMED 🎉</div>
      <div style="font-size:11px;margin-top:4px">{n} {day_word} of adventuring, logged.</div>
    </div>
    <div style="padding:20px 24px">
      <div style="font-size:8.5px;letter-spacing:1.5px;color:#8a6a3a;text-transform:uppercase;margin-bottom:6px">Breakdown</div>
      {breakdown}
      <div style="font-size:8.5px;letter-spacing:1.5px;color:#8a6a3a;text-transform:uppercase;margin:14px 0 6px">Standing</div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:#3a2a1a;margin-bottom:8px">
        <span>Level {level} — {title}</span><span style="color:#a2601c">▲ {streak} day streak</span></div>
      <div class="bar" style="height:14px"><div class="bar-fill" style="width:{pct}%"></div></div>
      <div style="font-size:9px;color:#6b5330;margin-top:6px">{xp_label} XP</div>
      {ach_html}
      <button class="btn-pix btn-grn pix" onclick="closeCeleb()" style="width:100%;margin-top:18px;font-size:12px;padding:13px 0;color:#f7f0d8">ONWARD ⚔️</button>
    </div>
  </div>
</div>
<script>
function closeCeleb(){{document.getElementById('celebModal').classList.remove('open');}}
window.addEventListener('load',function(){{document.getElementById('celebModal').classList.add('open');}});
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeCeleb();}});
</script>"""


# ── Daily login modal ──────────────────────────────────────────────────────────
AFFIRMATIONS = [
    "You do not have to finish it today. You only have to leave it clearer than you found it.",
    "Small commits are still commits. The bar moves either way.",
    "The bug you fear is usually smaller than the dread of opening the file.",
    "Yesterday's you left notes. Today's you gets to trust them.",
    "Read it once more before you rewrite it. Often that is the whole fix.",
    "Progress is quieter than you expect. Trust the streak.",
    "You are allowed to delete more than you add today.",
]
MOODS = [("Bright", "#f2c14e"), ("Steady", "#5f9c4a"), ("Foggy", "#8a9bb5"),
         ("Heavy", "#8a6a8a"), ("Restless", "#c2452d")]


def daily_login_html(state: dict) -> str:
    today = today_local_str()
    if today in (load_checkins().get("days") or {}):
        return ""  # already checked in today

    work = working_days()
    now = datetime.now().astimezone()
    cells = []
    for off in range(6, -1, -1):
        d = now - timedelta(days=off)
        ds = d.strftime("%Y-%m-%d")
        label = d.strftime("%a")[0]
        if off == 0:
            glyph, bg, border, fg = "★", "#f2c14e", "#a2601c", "#f7f0d8"
        elif ds in work:
            glyph, bg, border, fg = "✓", "#5f9c4a", "#8a6a3a", "#f7f0d8"
        else:
            glyph, bg, border, fg = "·", "#d0bc92", "#8a6a3a", "#a8946e"
        cells.append(
            f'<div style="text-align:center"><div class="pix" style="aspect-ratio:1;background:{bg};'
            f'box-shadow:inset 0 0 0 3px {border};display:flex;align-items:center;justify-content:center;'
            f'font-size:11px;color:{fg}">{glyph}</div>'
            f'<div style="font-size:8px;color:#8a6a3a;margin-top:5px;letter-spacing:1px">{label}</div></div>'
        )
    calendar = "".join(cells)

    affirmation = AFFIRMATIONS[now.toordinal() % len(AFFIRMATIONS)]
    mood_btns = "".join(
        f'<button type="button" class="mood-btn" data-mood="{label}" onclick="pickMood(this)" '
        f'style="flex:1;cursor:pointer;border:0;padding:12px 6px;background:#dfcda4;'
        f'box-shadow:inset 0 0 0 3px #b79a68;display:flex;flex-direction:column;align-items:center;gap:8px">'
        f'<span style="width:16px;height:16px;background:{dot};box-shadow:0 0 0 2px rgba(58,42,26,.55)"></span>'
        f'<span style="font-size:9px;color:#4a3520">{label}</span></button>'
        for label, dot in MOODS
    )

    return f"""
<div class="overlay open" id="dailyModal">
  <div class="modal parch" style="width:560px;max-width:100%;padding:30px 34px 26px">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">
      <span class="pix" style="font-size:15px;color:#3a2a1a">DAILY LOGIN</span>
      <span style="font-size:10px;color:#8a6a3a">{now.strftime('%A · %-d %B %Y')}</span>
    </div>
    <div class="dash" style="margin-bottom:20px"></div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-bottom:22px">{calendar}</div>
    <div class="inset" style="padding:16px 18px;margin-bottom:18px">
      <div style="font-size:8.5px;letter-spacing:1.6px;color:#8a6a3a;text-transform:uppercase;margin-bottom:9px">Word of affirmation</div>
      <div style="font-size:12.5px;color:#3a2a1a;line-height:2">{affirmation}</div>
    </div>
    <div style="font-size:8.5px;letter-spacing:1.6px;color:#8a6a3a;text-transform:uppercase;margin-bottom:10px">How are you arriving today?</div>
    <div style="display:flex;gap:9px;margin-bottom:22px">{mood_btns}</div>
    <button class="btn-pix btn-grn pix" onclick="closeDaily()" style="width:100%;font-size:12px;letter-spacing:1px;padding:14px 0;color:#f7f0d8">ENTER THE CLEARING</button>
  </div>
</div>
<script>
window.__mood=null;
function pickMood(el){{
  window.__mood=el.getAttribute('data-mood');
  document.querySelectorAll('.mood-btn').forEach(function(b){{b.style.boxShadow='inset 0 0 0 3px #b79a68';b.style.background='#dfcda4';}});
  el.style.boxShadow='inset 0 0 0 3px #a2601c';el.style.background='#f2c14e';
}}
function closeDaily(){{
  var m=document.getElementById('dailyModal');
  fetch('/api/checkin',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{mood:window.__mood}})}})
    .catch(function(){{}}).finally(function(){{m.classList.remove('open');}});
}}
</script>"""


# ── Transcript rendering ───────────────────────────────────────────────────────
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
                    parts.append(
                        f"<details><summary style='cursor:pointer;color:#8a6a3a'>🧠 thinking "
                        f"({len(block.get('thinking',''))} chars)</summary>"
                        f"<div style='white-space:pre-wrap;margin-top:6px'>{block.get('thinking','')[:2000]}</div></details>"
                    )
        return "\n".join(p for p in parts if p)
    return ""

def render_tool_calls(content) -> str:
    if not isinstance(content, list):
        return ""
    tools = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    if not tools:
        return ""
    badges = "".join(
        f'<span class="pix" style="display:inline-block;background:#2a1d10;color:#ffd27a;'
        f'padding:2px 8px;margin:2px 2px;font-size:10px;box-shadow:0 0 0 2px #6b4a24">⚙ {t["name"]}</span>'
        for t in tools)
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
        parts.append(f"cache:{usage['cache_read_input_tokens']}")
    if not parts:
        return ""
    model = msg.get("model", "")
    model_tag = f" · {model.split('-')[-1]}" if model else ""
    return (f'<div style="font-size:10px;color:#6b8a6a;padding:6px 14px;background:rgba(10,26,17,.5)">'
            f'🪙 {" · ".join(parts)}{model_tag}</div>')


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def idle():
    state = load_state()
    experiences, _ = experiences_since_claim()
    count = len(experiences)
    sess_today, calls_today = today_activity()
    ach_count = len((state.get("achievements", {}) or {}).get("unlocked", []) or [])

    now = datetime.now().astimezone()
    date_line = now.strftime("%A · %-d %B %Y").upper()

    pins = ["#c2452d", "#3f7fb5", "#7a9c3a", "#b8862b", "#8a5ab5"]
    cards = []
    for i, x in enumerate(experiences[:5]):
        proj = x["project"].split("/")[-1] or x["project"]
        calls = f"{x['calls']} tool calls" if x["calls"] is not None else "session"
        cards.append(f"""
<div style="animation:gm-float {4.2 + i*0.45:.2f}s ease-in-out infinite;animation-delay:{i*0.35:.2f}s">
  <a href="/session/{x['project_enc']}/{x['session_id']}" style="display:block;width:210px">
    <div class="parch" style="padding:14px 14px 12px;position:relative">
      <div style="display:flex;justify-content:space-between;margin-bottom:9px">
        <span style="font-size:8.5px;letter-spacing:1.5px;color:#8a6a3a;text-transform:uppercase">{proj}</span>
        <span style="font-size:8.5px;color:#8a6a3a">{x['time']}</span>
      </div>
      <div class="pix" style="font-size:11px;line-height:1.6;color:#3a2a1a;min-height:38px">{x['title']}</div>
      <div class="dash2" style="margin:10px 0"></div>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:9.5px;color:#6b5330">{calls}</span>
        <span style="font-size:9px;color:#8a6a3a">{x['rel']}</span>
      </div>
      <div class="pix btn-pix" onclick="event.preventDefault();openClaim()" style="margin-top:10px;font-size:9px;letter-spacing:1px;padding:7px 0;background:#5f9c4a;color:#f7f0d8;display:block">CLAIM</div>
      <div style="position:absolute;top:-9px;left:-9px;width:18px;height:18px;background:{pins[i % len(pins)]};box-shadow:0 0 0 3px #3a2a1a,inset -4px -4px 0 rgba(0,0,0,.28)"></div>
    </div>
  </a>
</div>""")

    if count > 5:
        cards.append(
            '<a href="/sessions" style="display:flex;align-items:center;justify-content:center;'
            'width:210px;min-height:150px;color:#cfe6c4;font-size:11px;'
            f'box-shadow:inset 0 0 0 2px #4d7a45">+{count - 5} more experiences →</a>')

    if count == 0:
        field = ('<div style="text-align:center;margin:40px 0;background:rgba(10,26,17,.82);'
                 'padding:16px 30px;display:inline-block;box-shadow:0 0 0 3px #4d7a45,0 0 0 6px #14261a">'
                 '<div class="pix" style="font-size:13px;color:#9be89b;margin-bottom:6px">ALL EXPERIENCE CLAIMED</div>'
                 '<div style="font-size:11px;color:#cfe6c4">The lantern is lit. Return tomorrow, or open your '
                 '<a href="/profile">profile</a>.</div></div>')
        modal = ""
        sub = "Everything from today is on the ledger. The forest keeps its own hours; come back tomorrow."
    else:
        field = f'<div style="display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-start;gap:22px;margin:46px 0 34px">{"".join(cards)}</div>'
        modal = """
<div class="overlay" id="claimModal" onclick="if(event.target===this)closeClaim()">
  <div class="modal parch" style="max-width:440px;width:100%;padding:26px 28px">
    <h2 class="pix" style="font-size:15px;color:#3a2a1a;margin-bottom:12px">✨ CLAIM YOUR EXPERIENCES</h2>
    <p style="font-size:12px;color:#6b5330;line-height:1.8;margin-bottom:12px">The Guildboard can't grant XP — only the <strong>Game Master</strong> can. Open Claude Code and ask directly:</p>
    <code id="claimPrompt" style="display:block;background:#2a1d10;color:#9be89b;padding:10px 12px;font-size:12px;margin-bottom:12px">Hey Game Master, claim my EXP today</code>
    <p style="font-size:11px;color:#8a6a3a;line-height:1.8;margin-bottom:16px">Naming the Game Master routes the claim through the quest system and backfills every unclaimed day.</p>
    <button class="btn-pix btn-grn pix" onclick="copyPrompt(this)" style="font-size:10px;padding:10px 16px;color:#f7f0d8">COPY PROMPT</button>
    <button class="btn-pix pix" onclick="closeClaim()" style="font-size:10px;padding:10px 16px;background:#b79a68;color:#3a2a1a;margin-left:8px">GOT IT</button>
  </div>
</div>
<script>
function openClaim(){document.getElementById('claimModal').classList.add('open');}
function closeClaim(){document.getElementById('claimModal').classList.remove('open');}
function copyPrompt(btn){var t=document.getElementById('claimPrompt').textContent;var d=function(){var o=btn.textContent;btn.textContent='COPIED!';setTimeout(function(){btn.textContent=o;},1500);};if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(d).catch(function(){window.prompt('Copy this prompt:',t);});}else{window.prompt('Copy this prompt:',t);}}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeClaim();});
</script>"""
        sub = ("Sessions were recorded while you worked. Claim them to move the bar — the Game "
               "Master has already read them and written the chronicle.")

    body = f"""
<div style="min-height:calc(100vh - 120px);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px 40px 70px">
  <div style="text-align:center;animation:gm-fade .8s ease both">
    <div style="font-size:10px;letter-spacing:5px;color:#9fd6a0;text-transform:uppercase;margin-bottom:16px">{date_line}</div>
    <h1 class="pix" style="font-size:40px;line-height:1.25;color:#f7f0d8;text-shadow:4px 4px 0 #06120c">The lantern is lit.</h1>
    <h1 class="pix" style="font-size:40px;line-height:1.25;color:#ffd27a;margin-bottom:18px;text-shadow:4px 4px 0 #06120c">Your day is waiting.</h1>
    <p style="max-width:520px;margin:0 auto;font-size:12.5px;line-height:2;color:#cfe6c4">{sub}</p>
  </div>
  {field}
  <div style="margin-top:20px;display:flex;justify-content:center;gap:20px;font-size:9.5px;letter-spacing:2px;color:rgba(200,230,190,.55);text-transform:uppercase;flex-wrap:wrap">
    <span>{sess_today} sessions today</span><span>·</span><span>{calls_today} tool calls</span><span>·</span><span>{ach_count} achievements</span>
  </div>
</div>
"""
    # Daily login and celebration are mutually exclusive: celebration only fires
    # when there's a claim today; the daily modal suppresses itself once checked in.
    _claimed, _ = claimed_today(state.get("sessions", {}))
    extra = celebration_html(state) if _claimed else daily_login_html(state)
    return HTMLResponse(html_page("Gamify", "home", state, body + modal, extra))


@app.get("/sessions", response_class=HTMLResponse)
def sessions_page():
    state = load_state()
    sessions = []
    for project_enc, path in iter_sessions():
        try:
            entries = parse_session(path)
            sessions.append({
                "project_enc": project_enc,
                "project": decode_project_name(project_enc),
                "session_id": path.stem,
                "title": session_label(entries, path.stem),
                "turns": count_turns(entries),
                "mtime": path.stat().st_mtime,
                "ts": format_ts(next((e.get("timestamp", "") for e in entries if e.get("timestamp")), "")),
            })
        except Exception:
            pass
    sessions.sort(key=lambda s: s["mtime"], reverse=True)

    if not sessions:
        body = (f'<div class="wrap"><h2 class="pix" style="font-size:22px;color:#f7e6b8">SESSIONS</h2>'
                f'<div class="empty" style="margin-top:20px">No sessions found in {PROJECTS_DIR}</div></div>')
        return HTMLResponse(html_page("Sessions", "sessions", state, body))

    cards = []
    for s in sessions:
        proj = s["project"].split("/")[-1] or s["project"]
        cards.append(f"""
<a href="/session/{s['project_enc']}/{s['session_id']}" style="display:block">
  <div class="inset" style="padding:13px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px">
    <div>
      <div class="pix" style="font-size:11px;color:#3a2a1a;line-height:1.6">{s['title']}</div>
      <div style="font-size:10px;color:#8a6a3a;margin-top:6px">
        <span class="pill">{proj}</span>
        &nbsp;<span style="color:#a2601c">{s['turns']} turns</span> &nbsp;· {s['ts']}
      </div>
    </div>
    <span style="color:#a2601c">›</span>
  </div>
</a>""")

    body = f"""
<div class="wrap">
  <h2 class="pix" style="font-size:22px;color:#f7e6b8;text-shadow:3px 3px 0 #06120c">SESSIONS</h2>
  <p style="margin:8px 0 18px;font-size:11px;color:#cfe6c4">{len(sessions)} recorded sessions · read-only</p>
  <div class="parch" style="padding:20px 22px"><div style="display:flex;flex-direction:column;gap:10px">{"".join(cards)}</div></div>
</div>"""
    return HTMLResponse(html_page("Sessions", "sessions", state, body))


@app.get("/session/{project_enc}/{session_id}", response_class=HTMLResponse)
def session_detail(project_enc: str, session_id: str):
    state = load_state()
    path = PROJECTS_DIR / project_enc / f"{session_id}.jsonl"
    if not path.exists():
        raise HTTPException(404, "Session not found")

    entries = parse_session(path)
    title = session_label(entries, session_id)
    proj_label = decode_project_name(project_enc).split("/")[-1]

    turns = []
    for e in entries:
        etype = e.get("type")
        ts = format_ts(e.get("timestamp", ""))
        if etype == "user":
            text = render_content(e.get("message", {}).get("content", ""))
            if not text.strip():
                continue
            turns.append(f"""
<div style="margin-bottom:14px;box-shadow:0 0 0 2px #6b4a24">
  <div class="pix" style="padding:8px 14px;font-size:10px;background:#2a1d10;color:#ffd27a;display:flex;justify-content:space-between"><span>👤 USER</span><span>{ts}</span></div>
  <div style="padding:12px 14px;background:rgba(233,218,180,.94);color:#3a2a1a;white-space:pre-wrap;word-break:break-word;line-height:1.7;font-size:13px">{text}</div>
</div>""")
        elif etype == "assistant":
            content = e.get("message", {}).get("content", [])
            text = render_content(content)
            tools = render_tool_calls(content)
            tokens = render_token_info(e.get("message", {}))
            if not text.strip() and not tools:
                continue
            turns.append(f"""
<div style="margin-bottom:14px;box-shadow:0 0 0 2px #35603a">
  <div class="pix" style="padding:8px 14px;font-size:10px;background:#16301d;color:#9be89b;display:flex;justify-content:space-between"><span>🤖 ASSISTANT</span><span>{ts}</span></div>
  <div style="padding:12px 14px;background:rgba(233,218,180,.94);color:#3a2a1a;white-space:pre-wrap;word-break:break-word;line-height:1.7;font-size:13px">{text}{tools}</div>
  {tokens}
</div>""")
        elif etype in ("system", "attachment"):
            content = e.get("message", {}).get("content", "")
            if isinstance(content, list):
                content = render_content(content)
            if not content or not str(content).strip():
                continue
            turns.append(f"""
<div style="margin-bottom:10px">
  <details><summary style="cursor:pointer;padding:8px 14px;background:rgba(10,26,17,.7);color:#8fbf8a;font-size:11px">⚙ {etype} · {ts}</summary>
  <div style="padding:12px 14px;background:rgba(233,218,180,.9);color:#3a2a1a;white-space:pre-wrap;font-size:12px">{str(content)[:300]}</div></details>
</div>""")

    body = f"""
<div class="wrap">
  <a href="/sessions" style="font-size:12px">← All sessions</a>
  <div style="font-size:11px;color:#8fbf8a;margin:12px 0 4px">{proj_label}</div>
  <h2 class="pix" style="font-size:18px;color:#f7e6b8">{title}</h2>
  <div style="font-size:10px;color:#6b8a6a;margin:6px 0 22px">{session_id}</div>
  {"".join(turns) if turns else '<div class="empty">No turns found</div>'}
</div>"""
    return HTMLResponse(html_page(title, "sessions", state, body))


@app.get("/profile", response_class=HTMLResponse)
def profile_page():
    state = load_state()
    profile = state["profile"]
    quests = state["quests"]
    achievements = state["achievements"]
    sessions = state["sessions"]

    if not profile:
        body = (f'<div class="wrap"><h2 class="pix" style="font-size:22px;color:#f7e6b8">PROFILE</h2>'
                f'<div class="empty" style="margin-top:20px">No profile found in {GAMIFY_DIR}.<br>'
                f'Start a session with the Game Master to begin.</div></div>')
        return HTMLResponse(html_page("Profile", "profile", state, body))

    player = profile.get("player", {}) or {}
    name = player.get("name", "Adventurer")
    pclass = player.get("class", "Engineer")
    joined = player.get("joined", "—")
    level = profile.get("level", 1)
    title = profile.get("title", "")
    pct, xp_label = xp_bar(profile)
    xp = profile.get("xp", 0)
    xp_next = profile.get("xpForNextLevel", 0) or 0
    to_next = max(0, xp_next - xp)
    streak = (profile.get("streak", {}) or {}).get("count", 0)

    craft = profile.get("craftBadges", []) or []
    unlocked_ach = achievements.get("unlocked", []) or []
    badges_earned = sum(1 for b in craft if b.get("earned")) + len(unlocked_ach)
    _sess_today, calls_today = today_activity()

    stat_tiles = "".join(
        f'<div class="inset" style="padding:14px 16px;text-align:center;min-width:88px">'
        f'<div class="pix" style="font-size:17px;color:#3a2a1a">{v}</div>'
        f'<div style="font-size:8.5px;letter-spacing:1.4px;color:#8a6a3a;margin-top:5px;text-transform:uppercase">{lbl}</div></div>'
        for v, lbl in [(calls_today, "Tool calls"), (streak, "Day streak"), (badges_earned, "Badges")]
    )

    banner = f"""
<div class="parch" style="padding:26px 30px;margin-bottom:22px">
  <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap">
    <div class="pix" style="width:96px;height:96px;background:#4d7a45;box-shadow:0 0 0 4px #3a2a1a,inset 0 0 0 6px #2f5c30;display:flex;align-items:center;justify-content:center;font-size:9px;color:#cfe6c4;text-align:center;line-height:1.6">SPRITE<br>128×128</div>
    <div style="flex:1;min-width:300px">
      <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
        <span class="pix" style="font-size:22px;color:#3a2a1a">{name}</span>
        <span style="font-size:11px;color:#8a6a3a">{pclass} · joined {joined}</span>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:14px">
        <span class="pix" style="font-size:15px;color:#a2601c">LV {level}</span>
        <div class="bar" style="flex:1"><div class="bar-fill" style="width:{pct}%"></div></div>
        <span class="pix" style="font-size:11px;color:#3a2a1a;min-width:112px;text-align:right">{xp_label}</span>
      </div>
      <div style="margin-top:9px;font-size:10.5px;color:#6b5330">{to_next:,} XP to <b>Level {level + 1}</b> — {title}</div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap">{stat_tiles}</div>
  </div>
</div>"""

    # Active quests with progress bars
    side = quests.get("sideQuests", []) or []
    active = [q for q in side if q.get("status") == "active"]
    q_cards = []
    for q in active:
        prog = q.get("progress") or {}
        total = prog.get("total") or len(q.get("objectives", []) or []) or 1
        done = prog.get("done", 0) or 0
        qp = int(min(100, (done / total) * 100)) if total else 0
        q_cards.append(f"""
<div class="inset" style="padding:14px 16px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px">
    <span class="pix" style="font-size:11px;color:#3a2a1a;line-height:1.5">{q.get('emoji','')} {q.get('name','')}</span>
    <span style="font-size:9.5px;color:#a2601c;white-space:nowrap">+{q.get('xp',0)} XP</span>
  </div>
  <div style="font-size:10px;color:#6b5330;margin:8px 0 11px;line-height:1.8">{q.get('description','')}</div>
  <div style="display:flex;align-items:center;gap:10px">
    <div class="bar-sm" style="flex:1"><i style="width:{qp}%"></i></div>
    <span style="font-size:9px;color:#6b5330;min-width:58px;text-align:right">{done} / {total}</span>
  </div>
</div>""")
    quests_html = "".join(q_cards) or '<div style="font-size:11px;color:#8a6a3a">No active quests.</div>'

    # Achievements grid: earned craft badges + unlocked hidden, padded with locked "?"
    revealed = []
    for b in craft:
        if b.get("earned"):
            revealed.append((b.get("emoji", "★"), b.get("name", "")))
    for a in unlocked_ach:
        revealed.append((a.get("emoji", "★"), a.get("name", "")))
    GRID = max(18, ((len(revealed) + 5) // 6) * 6)
    cells = []
    for i in range(GRID):
        if i < len(revealed):
            glyph, aname = revealed[i]
            cells.append(f'<div title="{aname}" class="pix" style="aspect-ratio:1;background:#f2c14e;'
                         f'box-shadow:inset 0 0 0 3px #a2601c;display:flex;align-items:center;justify-content:center;'
                         f'font-size:13px;color:#3a2a1a">{glyph}</div>')
        else:
            cells.append('<div title="Hidden" class="pix" style="aspect-ratio:1;background:#d0bc92;'
                         'box-shadow:inset 0 0 0 3px #b79a68;display:flex;align-items:center;justify-content:center;'
                         'font-size:13px;color:#a8946e">?</div>')
    grid = "".join(cells)

    latest = unlocked_ach[-1] if unlocked_ach else None
    latest_html = (
        f'<div style="font-size:8.5px;letter-spacing:1.5px;color:#8a6a3a;text-transform:uppercase;margin-bottom:7px">Latest reveal</div>'
        f'<div class="pix" style="font-size:11px;color:#3a2a1a;line-height:1.6">{latest.get("emoji","🏅")} {latest.get("name","")}</div>'
        f'<div style="font-size:10px;color:#6b5330;margin-top:7px;line-height:1.8">{latest.get("context","")}</div>'
        if latest else
        '<div style="font-size:10px;color:#6b5330;line-height:1.8">No reveals yet. Some achievements find you when you least expect them.</div>'
    )

    ach_panel = f"""
<div class="parch" style="padding:22px 24px">
  <div style="display:flex;justify-content:space-between;align-items:baseline">
    <span class="sect">ACHIEVEMENTS</span>
    <span style="font-size:10px;color:#8a6a3a">{len(revealed)} / {GRID} revealed</span>
  </div>
  <div class="dash" style="margin:4px 0 18px"></div>
  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:9px;margin-bottom:18px">{grid}</div>
  <div class="inset" style="padding:13px 15px">{latest_html}</div>
</div>"""

    # Chronicle from sessions.json log[]
    log = list(reversed(sessions.get("log", []) or []))[:8]
    chron_rows = "".join(
        f'<div style="display:flex;gap:16px;align-items:baseline">'
        f'<span style="font-size:9.5px;color:#8a6a3a;min-width:70px">{c.get("date","")}</span>'
        f'<span style="font-size:11px;color:#4a3520;line-height:1.9">{c.get("progressNotes","")}</span></div>'
        for c in log
    ) or '<div style="font-size:11px;color:#8a6a3a">The chronicle is empty. Your first logged session begins it.</div>'

    body = f"""
<div class="wrap">
  {banner}
  <div style="display:grid;grid-template-columns:1.15fr 1fr;gap:22px;align-items:start">
    <div class="parch" style="padding:22px 24px">
      <div class="sect">ACTIVE QUESTS</div>
      <div class="dash" style="margin:4px 0 18px"></div>
      <div style="display:flex;flex-direction:column;gap:14px">{quests_html}</div>
    </div>
    {ach_panel}
  </div>
  <div class="parch" style="padding:22px 24px;margin-top:22px">
    <div class="sect">CHRONICLE</div>
    <div class="dash" style="margin:4px 0 16px"></div>
    <div style="display:flex;flex-direction:column;gap:12px">{chron_rows}</div>
  </div>
</div>
<style>@media (max-width:860px){{.wrap > div[style*="grid-template-columns:1.15fr"]{{grid-template-columns:1fr!important}}}}</style>"""
    return HTMLResponse(html_page("Profile", "profile", state, body, celebration_html(state)))


@app.get("/guildboard", response_class=HTMLResponse)
def guildboard(view: str = "board"):
    state = load_state()
    profile = state["profile"]
    quests = state["quests"]

    if not profile:
        body = (f'<div class="wrap"><h2 class="pix" style="font-size:22px;color:#f7e6b8">GUILDBOARD</h2>'
                f'<div class="empty" style="margin-top:20px">No quest board found in {GAMIFY_DIR}.<br>'
                f'Start a session with the Game Master to begin.</div></div>')
        return HTMLResponse(html_page("Guildboard", "guildboard", state, body))

    ledger = view == "ledger"

    def toggle(v, label):
        on = (view == v) or (v == "board" and not ledger)
        bg = "#f2c14e" if on else "transparent"
        fg = "#2a1d10" if on else "#d8c79a"
        return (f'<a href="/guildboard?view={v}" class="pix" style="font-size:10px;padding:9px 16px;'
                f'background:{bg};color:{fg}">{label}</a>')

    modes = (f'<div style="display:flex;gap:6px;background:#2a1d10;padding:5px;box-shadow:0 0 0 3px #6b4a24">'
             f'{toggle("board","BOARD")}{toggle("ledger","LEDGER")}</div>')

    # Suggested quests (proposed)
    suggested = [q for q in quests.get("suggested", []) if q.get("status") == "proposed"]
    papers = ["#e9dab4", "#e4d3a8", "#efe2c2", "#e2d0a2", "#ece0bd"]
    sug_cards = []
    for i, q in enumerate(suggested):
        rot = 0 if ledger else ((i % 3) - 1) * 0.9
        sug_cards.append(f"""
<div style="position:relative;background:{papers[i % len(papers)]};padding:18px 18px 16px;transform:rotate({rot}deg);box-shadow:0 0 0 2px rgba(90,66,34,.5),0 8px 14px rgba(0,0,0,.45);background-image:repeating-linear-gradient(180deg,rgba(120,90,50,.05) 0 2px,transparent 2px 4px)">
  <div style="position:absolute;top:-8px;left:50%;width:16px;height:16px;margin-left:-8px;background:#c2452d;box-shadow:0 0 0 2px #3a2a1a,inset -4px -4px 0 rgba(0,0,0,.3)"></div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span class="pill">{q.get('type','Quest')}</span>
    <span style="font-size:9px;color:#8a6a3a">{q.get('timeline','')}</span>
  </div>
  <div class="pix" style="font-size:12px;color:#3a2a1a;line-height:1.6;margin-bottom:10px">{q.get('emoji','')} {q.get('name','')}</div>
  <div style="font-size:10px;color:#6b5330;line-height:1.9;margin-bottom:14px">{q.get('objective') or q.get('description','')}</div>
  <div class="dash2" style="margin-bottom:12px"></div>
  <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
    <span class="pix" style="font-size:12px;color:#a2601c">+{q.get('xp',0)} XP</span>
    <span class="pix btn-pix btn-grn" onclick="openAccept()" style="font-size:9px;letter-spacing:1px;padding:9px 14px;color:#f7f0d8;cursor:pointer">ACCEPT</span>
  </div>
</div>""")
    cols = "1fr" if ledger else "repeat(auto-fit,minmax(238px,1fr))"
    sug_html = (f'<div style="display:grid;grid-template-columns:{cols};gap:20px;align-items:start">{"".join(sug_cards)}</div>'
                if sug_cards else '<div style="color:#e9dab4;font-size:11px">No suggested quests right now. Ask the Game Master for fresh proposals.</div>')

    # In-progress active side quests
    side = quests.get("sideQuests", []) or []
    active = [q for q in side if q.get("status") == "active"]
    ip_rows = []
    for q in active:
        prog = q.get("progress") or {}
        total = prog.get("total") or len(q.get("objectives", []) or []) or 1
        done = prog.get("done", 0) or 0
        qp = int(min(100, (done / total) * 100)) if total else 0
        due = q.get("dueDate") or "—"
        ip_rows.append(f"""
<div style="display:grid;grid-template-columns:1.4fr 2fr 150px;gap:18px;align-items:center;background:rgba(30,56,38,.6);padding:13px 16px;box-shadow:inset 0 0 0 2px #35603a">
  <span class="pix" style="font-size:10.5px;color:#e9dab4;line-height:1.6">{q.get('emoji','')} {q.get('name','')}</span>
  <div style="display:flex;align-items:center;gap:12px">
    <div class="bar-grn" style="flex:1"><i style="width:{qp}%"></i></div>
    <span style="font-size:9.5px;color:#8fbf8a;min-width:52px">{done}/{total} · due {due}</span>
  </div>
  <span style="font-size:9.5px;color:#ffd27a;text-align:right">+{q.get('xp',0)} XP on completion</span>
</div>""")
    ip_html = "".join(ip_rows) or '<div style="color:#8fbf8a;font-size:11px">No quests underway.</div>'

    # Main quest strip
    status_icon = {"active": "🟡", "locked": "🔒", "completed": "✅"}
    status_col = {"active": "#e9dab4", "locked": "#6e8a6e", "completed": "#8fd86a"}
    mq_rows = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid #234029;font-size:12px;color:{status_col.get(q.get("status","locked"),"#e9dab4")}">'
        f'{status_icon.get(q.get("status","locked"),"")} <span>{q.get("name","")}</span>'
        f'<span style="margin-left:auto;color:#8fbf8a">+{q.get("xp",0)} XP</span></div>'
        for q in quests.get("mainQuests", []) or []
    ) or '<div style="color:#8fbf8a;font-size:11px">No main quests.</div>'

    accept_modal = """
<div class="overlay" id="acceptModal" onclick="if(event.target===this)closeAccept()">
  <div class="modal parch" style="max-width:440px;width:100%;padding:26px 28px">
    <h2 class="pix" style="font-size:14px;color:#3a2a1a;margin-bottom:12px">⚔️ ACCEPT A QUEST</h2>
    <p style="font-size:12px;color:#6b5330;line-height:1.8;margin-bottom:12px">The Guildboard is read-only. Accept a quest through the <strong>Game Master</strong> so it's tracked properly:</p>
    <code style="display:block;background:#2a1d10;color:#9be89b;padding:10px 12px;font-size:12px;margin-bottom:16px">Hey Game Master, I'll take that quest</code>
    <button class="btn-pix pix" onclick="closeAccept()" style="font-size:10px;padding:10px 16px;background:#b79a68;color:#3a2a1a">GOT IT</button>
  </div>
</div>
<script>
function openAccept(){document.getElementById('acceptModal').classList.add('open');}
function closeAccept(){document.getElementById('acceptModal').classList.remove('open');}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeAccept();});
</script>"""

    body = f"""
<div class="wrap">
  <div style="display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px">
    <div>
      <h2 class="pix" style="font-size:26px;color:#f7e6b8;text-shadow:3px 3px 0 #06120c">GUILDBOARD</h2>
      <p style="margin:8px 0 0;font-size:11px;color:#cfe6c4">Pinned by the Game Master, drawn from what you were already doing.</p>
    </div>
    {modes}
  </div>

  <div style="background:#5c3d22;padding:26px;box-shadow:0 0 0 5px #33200f,0 0 0 9px #7b5c34,0 14px 0 rgba(0,0,0,.45);background-image:repeating-linear-gradient(90deg,rgba(0,0,0,.16) 0 2px,transparent 2px 7px),repeating-linear-gradient(0deg,rgba(255,255,255,.03) 0 1px,transparent 1px 26px)">
    {sug_html}
  </div>

  <div class="dark" style="margin-top:24px;padding:22px 26px">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:16px">
      <span class="pix" style="font-size:13px;color:#9be89b">IN PROGRESS</span>
      <span style="font-size:10px;color:#8fbf8a">{len(active)} quests underway</span>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">{ip_html}</div>
  </div>

  <div class="dark" style="margin-top:24px;padding:22px 26px">
    <div class="pix" style="font-size:13px;color:#9be89b;margin-bottom:14px">MAIN QUEST</div>
    {mq_rows}
  </div>
</div>
{accept_modal}
<style>@media (max-width:720px){{.wrap [style*="grid-template-columns:1.4fr"]{{grid-template-columns:1fr!important;gap:8px!important}}}}</style>"""
    return HTMLResponse(html_page("Guildboard", "guildboard", state, body, celebration_html(state)))


@app.post("/api/checkin")
async def api_checkin(request: Request):
    """Persist a daily mood / check-in to the viewer-owned checkins.json."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    mood = payload.get("mood")
    if mood is not None and not isinstance(mood, str):
        mood = str(mood)
    date = payload.get("date") or today_local_str()
    try:
        save_checkin(date, mood)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    return JSONResponse({"ok": True, "date": date, "mood": mood})
