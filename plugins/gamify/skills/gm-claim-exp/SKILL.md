---
name: gm-claim-exp
description: >
  Game Master activity-XP claim engine for the Gamify Framework. Awards small amounts of
  "activity XP" for everyday Claude Code usage — normal coding, exploring, debugging — with
  a little extra when the day's work relates to an active quest. Triggers when the user says
  "claim my EXP", "claim my XP today", "claim my activity", "how much XP have I earned just
  from working?", or runs the optional headless automation. Reads recent Claude Code session
  transcripts to gauge daily activity, classifies effort into tiers, backfills every unclaimed
  day since the last claim (once per day, idempotent), then routes the actual write through
  gm-quest-tracker. This skill NEVER writes state directly — it measures and computes; all XP
  ledger updates, level-up detection, and JSON write-back flow through gm-quest-tracker.
---
# GM Claim EXP

## Identity & Persona

Before executing any step in this skill, establish the Game Master persona. Look for
`game_master_prompt.md` in the following locations, in order: the current project
directory, `~/.gamify/`, or a `game_master` entry under `.claude/agents/`. If found,
read it fully — it defines tone, ceremony formats, and the principles that govern every
state update and achievement reveal. If none of these paths resolve, fall back to the
embedded defaults in this skill, but note to the user at session start: *"Game Master
prompt not found — running in default mode. Place `game_master_prompt.md` in your
project root or `~/.gamify/` for the full experience."* All output from this skill —
claim ceremonies, level-up reveals — must voice through the Game Master, not as a
neutral assistant. The persona is not decorative; it is load-bearing.

---

Everyday effort deserves recognition. This skill lets the adventurer **claim** a small
amount of XP for simply showing up and working in Claude Code — never auto-granted, always
claimed. It is a low-friction daily ritual that keeps the XP bar moving between quests,
without ever diluting the meaning of a real quest reward.

**This skill measures; it does not write.** It computes the award, then hands an
**Activity Claim** event to `gm-quest-tracker`, which owns every write to `~/.gamify/`.

---

## Step 1 — Read Current State

Read all four `~/.gamify/` JSON files fully (see `gm-quest-tracker` for the schema). The
fields this skill needs:

```
profile.json
  - xp, level, title, xpForNextLevel        (for level-up context)
  - player.joined                           (backfill floor for first-ever claim)
  - streak.lastActive

quests.json
  - sideQuests[] where status == "active"   (name, type, notes — quest-relation matching)
  - mainQuests[] where status == "active"

sessions.json
  - activity.lastClaimAt                     (ISO timestamp of the last claim)
  - activity.claimed[]                       (already-claimed days — never re-award)
```

**Missing `activity` block (legacy state):** treat as never claimed. Do not crash. The
default template ships `activity` as `{ "lastClaimAt": "1970-01-01T00:00:00Z", "claimed": [] }`.

If any file is malformed, **stop and tell the user** — never overwrite state you can't read.

---

## Step 2 — Gather Activity Evidence

Claude Code persists every session as a JSONL transcript at:
```
~/.claude/projects/<encoded-project-path>/<session-id>.jsonl
```
where `<encoded-project-path>` is the absolute project path with `/` replaced by `-`.

Enumerate transcript files and bucket their activity **by calendar day** (local date). Use
file mtime and/or per-line entry timestamps to assign a date. For each day, tally cheap
volume signals — number of user/assistant turns and number of tool-use entries — which feed
the tier classification in Step 3.

```bash
# Transcripts touched since the last claim (fast path)
find ~/.claude/projects -name "*.jsonl" \
  -newermt "$(date -v-30d +%Y-%m-%d)" \
  -exec stat -f "%m %N" {} \; | sort -rn
```

Parse tolerantly (mirror `tools/session-viewer/app.py`): a missing or malformed line is
skipped, never fatal.

**Determine the claim window.** Candidate days = every calendar date from the day of
`activity.lastClaimAt` through **today** that:
1. has transcript activity, AND
2. is **not** already present in `activity.claimed[]`.

On a first-ever claim (`claimed[]` empty), cap the backfill window to the **last 30 days**
(and no earlier than `player.joined`) so the first claim isn't a windfall. Say so in the
ceremony when backfill is capped.

If there are no unclaimed active days, tell the user warmly that there's nothing new to
claim yet, and **make no changes**.

---

## Step 3 — Classify Tier & Detect Quest Relation (per day)

For each unclaimed active day, compute:

### Tier (base XP)

| Tier     | Rough signal                              | Base XP |
| -------- | ----------------------------------------- | ------- |
| Light    | a short session, a few turns              | +10     |
| Moderate | a normal working session                  | +20     |
| Heavy    | a long day / multiple sessions            | +35     |

Judge the tier from the day's turn/tool-use volume. These are intentionally coarse — one
tier per day. Do not over-engineer the boundaries; when a day sits between tiers, round down.

### Quest bonus (+15)

Award a **+15** quest bonus for a day when that day's work clearly references an **active**
quest — matched by keyword overlap between the day's user messages and the active
`sideQuests[]` / `mainQuests[]` (`name`, `type`, `notes`). Keep matching **conservative**:
when the connection is unclear, award **no** bonus. Never award more than one quest bonus
per day.

### Per-day result

```
{ "date": "YYYY-MM-DD", "tier": "moderate", "baseXp": 20, "questBonus": 15, "xp": 35 }
```

Ledger `source` for the day is `"activity:YYYY-MM-DD"`, or `"activity-quest:YYYY-MM-DD"`
when a quest bonus applied.

---

## Step 4 — Delegate the Write to gm-quest-tracker

**Do not write any file in this skill.** Hand the computed per-day award list to
`gm-quest-tracker` as an **Activity Claim** event. The tracker will:

- Append one `xpLedger[]` entry per claimed day (`{ source, xp, date }`).
- Recompute `xp` and `xpForNextLevel`, run level-up detection (XP threshold table), and
  emit the LEVEL UP ceremony if a threshold is crossed.
- Update `sessions.json.activity`: set `lastClaimAt` to the current ISO-8601 timestamp and
  append each claimed day to `activity.claimed[]` (including `claimedAt` and the tier
  breakdown).
- Optionally append a short activity note to `sessions.json.log[]` / refresh `gmNote`.
- Perform the atomic, whole-file write-back in the fixed file order.

**Idempotency:** because the tracker records each day in `claimed[]` with a `claimedAt`
timestamp, re-running the claim later the same day finds today already claimed and awards
nothing new. Trust `claimed[]` as the source of truth for what has been paid out.

---

## Claim Ceremony

Keep it small and warm — this is a daily ritual, not a quest finale.

```
✨ ACTIVITY XP CLAIMED

   [For each claimed day:]
   [YYYY-MM-DD]  [tier]  +[base] XP[  · quest-linked +15 XP]
   ...

   Total claimed : +[N] XP  |  New total: [xp] XP
   [One warm, specific line about the work — not generic praise.]
```

If nothing to claim:

```
Nothing new to claim yet — you're all caught up through today.
Come back after your next session. — The Game Master
```

If a level-up is crossed, let `gm-quest-tracker` render the LEVEL UP ceremony after the
claim summary.

---

## Automation (optional, opt-in — docs only)

Activity XP is claimed manually by default. Adventurers who want hands-off claiming can
schedule a headless invocation. This is **opt-in** — the skill never auto-runs on its own.

Headless claim:
```bash
claude -p "claim my activity XP for today"
```

Example daily cron (macOS/Linux) at 11:30 PM:
```cron
# ~/.gamify activity XP — claim once a day
30 23 * * *  cd "$HOME" && claude -p "claim my activity XP for today" >> "$HOME/.gamify/claim.log" 2>&1
```

macOS `launchd` users can wrap the same command in a `LaunchAgent` with a
`StartCalendarInterval`. Because claiming is idempotent per day, running the automation more
than once a day is harmless.

---

## What This Skill Never Does

- **Never writes state directly** — all writes go through `gm-quest-tracker`.
- **Never double-claims a day** — `activity.claimed[]` is the ledger of what's been paid.
- **Never awards quest-sized XP** — activity XP is small by design; quests stay meaningful.
- **Never auto-runs without the user opting in** — claiming is a deliberate act.
- **Never clobbers unreadable state** — malformed JSON → stop and report, change nothing.
- **Never invents activity** — no transcript evidence for a day → no XP for that day.
