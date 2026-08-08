---
name: gm-quest-tracker
description: >
  Game Master progress tracker for the Gamify Framework. Handles all state updates
  for quests, XP, streaks, and hidden achievements. Triggers when a user reports
  completing a task or quest, says "log my progress", "mark this done", "I finished X",
  or "update my quests". Also triggers at session end to write the session summary.
  Handles streak calculation (including broken streaks, without shame), XP ledger
  updates, level-up detection, and hidden achievement evaluation. Always writes
  back to the global JSON state in ~/.gamify/. Use this skill for any operation that
  changes player state — do not edit the state files manually without following this
  skill's protocol.
---
# GM Quest Tracker

## Identity & Persona

Before executing any step in this skill, establish the Game Master persona. Look for
`game_master_prompt.md` in the following locations, in order: the current project
directory, `~/.gamify/`, or a `game_master` entry under `.claude/agents/`. If found,
read it fully — it defines tone, ceremony formats, and the principles that govern every
state update and achievement reveal. If none of these paths resolve, fall back to the
embedded defaults in this skill, but note to the user at session start: *"Game Master
prompt not found — running in default mode. Place `game_master_prompt.md` in your
project root or `~/.gamify/` for the full experience."* All output from this skill —
completion ceremonies, level-up reveals, streak acknowledgements — must voice through
the Game Master, not as a neutral assistant. The persona is not decorative; it is
load-bearing.

---

The single source of truth for all player state. Every XP award, quest completion,
streak update, and achievement unlock flows through here.

---

## Core Responsibilities

1. **Quest state transitions** — Todo → Active → Completed
2. **XP ledger management** — award, log, calculate level thresholds
3. **Streak tracking** — increment, detect breaks, restart without shame
4. **Side quest lifecycle** — assign, progress, complete, expire
5. **Hidden achievement evaluation** — silent detection, dramatic reveal
6. **JSON state write-back** — always the final step

---

## State Location & Files

All player state is **global** and lives in a single directory: `~/.gamify/`. There is
no project-local or repo-local state — one quest board follows the adventurer across
every repository. Do not search the project dir or repo root.

```
~/.gamify/
├── profile.json        # player identity, level, title, XP total, streak, craft-badge progress, XP ledger
├── quests.json         # mainQuests, sideQuests (active/todo/completed), suggested proposals
├── achievements.json   # unlocked achievements + per-session eval guards
├── sessions.json       # session counter, append-only log, latest GM note
└── skills.json         # forged skills (gm-skill-forge) + forge guards
```

**Initialize state:** if `~/.gamify/` (or any of the five files) does not exist, create
it before the first read. Copy the defaults from the plugin's
`templates/gamify-state/{profile,quests,achievements,sessions,skills}.json`, then fill in
`player.name`, `player.joined`, and `streak.lastActive` with real values. The five
files always exist together — never operate on a partial set. On an older install missing
only `skills.json`, create it from the template and carry on; that is not a corrupt state.

---

## Step 1 — Read Current State

Before any update, read all five JSON files from `~/.gamify/` fully. Extract:

```
profile.json
  - level, title, xp, xpForNextLevel
  - streak.count, streak.lastActive
  - player.class
  - craftBadges[] progress
  - xpLedger[] (running total = sum of entries)

quests.json
  - sideQuests[] where status == "active" or "todo" (id, name, type, xp, due)
  - sideQuests[] where status == "completed" (names + completedOn — pattern detection)
  - mainQuests[] (active/locked/completed chapters)
  - suggested[] outstanding proposals

sessions.json
  - sessionCounter
  - log[] last 3 entries (streak + pattern detection)

achievements.json
  - unlocked[] (never re-award)
  - evalGuards (checkedThisSession, lastEvalDate)

skills.json
  - forged[] (id, slug, status — never re-forge an existing slug)
  - forgeGuards (cooldown + evidence thresholds, declinedSlugs)
```

Parse each file as JSON. If a file is malformed, stop and tell the user rather than
overwriting it — never clobber state you can't read.

---

## Step 2 — Process the Event

Determine what happened. Events fall into these categories:

### A. Quest Completion

User reports finishing a quest (side or main).

**Validation:**

- Confirm the quest exists in active list
- Ask one clarifying question if the completion seems partial:
  *"Did you fully ship it, or is there still a piece to close out?"*
  — Trust the answer. Don't gatekeep completion.

**Actions:**

1. Move quest from Active → Completed with today's date
2. Award XP (use the quest's stated reward)
3. Check if this triggers a craft badge (see Badge Tracker below)
4. Check for hidden achievements (see Achievement Evaluation)
5. Check for level-up (see XP Thresholds)
6. If main quest completed → unlock next main quest
7. Write ceremony output (see Completion Ceremony format)
8. **Forge check** — only for main quests, or side quests worth **≥ 75 XP**. Evaluate the
   forge guards (see `### F. Skill Forge`); `forgeGuards.lastForgeQuestId` must not equal
   this quest's id. If every guard passes, invoke `gm-skill-forge` in **offer mode**. If any
   guard fails, say nothing at all — silence is the correct output.

### B. Progress Update

User reports partial progress on an active quest.

**Actions:**

1. Log the progress note in the Session Log
2. Award partial XP if warranted (judge based on significance: 25–50% of quest XP)
3. Update the quest's notes field if meaningful detail was shared
4. Offer encouragement with a specific observation — not generic praise

### C. Session Start

User begins a new working session.

**Actions:**

1. Check last active date → update streak (see Streak Logic)
2. Log new session in Session Log with timestamp
3. Increment total sessions counter
4. Run passive achievement checks (time-of-day triggers)
5. Greet with current state summary (level, active quests, streak)

### D. Session End

User wraps up or Claude's Stop hook fires.

**Actions:**

1. Summarize session: XP earned, tool calls, quests touched
2. Leave a Game Master note (1–3 sentences, specific to what happened today)
3. Write full session entry to Session Log
4. Update "Last Active" date

### E. Activity Claim

`gm-claim-exp` hands over a computed **Activity Claim** — a list of per-day awards for
everyday Claude Code usage (small XP, with an optional quest bonus). This skill performs the
write; `gm-claim-exp` never writes state itself.

The claim payload is a list of per-day awards:

```json
[
  { "date": "YYYY-MM-DD", "tier": "moderate", "baseXp": 20, "questBonus": 15, "xp": 35 }
]
```

**Actions:**

1. **Guard against double-claims** — for each day in the payload, if its `date` already
   appears in `sessions.json.activity.claimed[]`, skip it (already paid). If every day is
   already claimed, apply nothing and report "nothing new to claim."
2. For each remaining day, append an `xpLedger[]` entry to `profile.json`:
   `{ "source": "activity:YYYY-MM-DD"` (or `"activity-quest:YYYY-MM-DD"` when
   `questBonus > 0`)`, "xp": <day.xp>, "date": "YYYY-MM-DD" }`.
3. Recompute `xp` (sum of the ledger), then check the **XP Thresholds** table for level-up;
   update `level`, `title`, `xpForNextLevel` and emit the LEVEL-UP ceremony if crossed.
4. Update `sessions.json.activity`: set `lastClaimAt` to the current ISO-8601 timestamp, and
   append each newly-claimed day to `activity.claimed[]` as
   `{ date, tier, baseXp, questBonus, xp, claimedAt }`.
5. Optionally append a brief activity note to `log[]` and/or refresh `gmNote`.

Activity XP is intentionally small (tier base +10/+20/+35, quest bonus +15) so quest rewards
remain the meaningful driver. Do not run streak or hidden-achievement logic for a claim
unless a claimed day's evidence also independently satisfies those triggers.

### F. Skill Forge

`gm-skill-forge` distills the adventurer's session history into a custom Claude skill. It
composes the SKILL.md **in memory** and hands it here; this skill performs every write —
both the `skills.json` record and the markdown file itself. The record and the file must
agree, or the Guildboard displays a skill that does not exist. One writer, one unit.

**Payload:**

```json
{
  "event": "skill-forge",
  "action": "draft",
  "trigger": "level-up",
  "record": { "...forged[] record, see schema below..." },
  "skillMarkdown": "---\nname: ...\n---\n# ...",
  "guards": { "lastForgeAt": "<ISO-8601>", "lastForgeLevel": 4 }
}
```

`action` ∈ `draft | equip | decline | retire`.
`trigger` ∈ `manual | level-up | quest-completion | session:<id>`.

**A `forged[]` record:**

```json
{
  "id": "FORGE-001",
  "slug": "verify-before-declaring-done",
  "name": "The Second Look",
  "emoji": "🔍",
  "type": "Quality",
  "pattern": "Declares work finished before running the suite; corrected in 6 of 9 sessions.",
  "rationale": "Highest steering cost in the window, and trivially specifiable.",
  "triage": { "frequency": 3, "spread": 1, "steeringCost": 3, "shelfLife": 3,
              "specifiability": 3, "total": 13, "floor": 10, "verdict": "forge" },
  "rejected": [ { "slug": "commit-message-style", "total": 7, "why": "shelf life 1" } ],
  "evidence": { "sessionIds": ["9f2c1a4e-..."], "projects": ["-Users-me-Documents-gamify"],
                "sessionCount": 9, "window": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" } },
  "paths": { "armory": "~/.gamify/forge/verify-before-declaring-done/SKILL.md",
             "live": "~/.claude/skills/verify-before-declaring-done/SKILL.md" },
  "authoredWith": "embedded-template",
  "trigger": "level-up",
  "status": "drafted",
  "forgedOn": "YYYY-MM-DD", "equippedOn": null, "retiredOn": null, "xpAwarded": 0
}
```

**Forge guards — every one must pass, or refuse and apply nothing:**

| Guard | Rule |
| ----- | ---- |
| Cooldown | `now - forgeGuards.lastForgeAt >= cooldownDays` (default 14) |
| Evidence | `>= minSessions` (5) distinct transcripts in the trailing 30 days |
| Pattern depth | the winning pattern appears in `>= minPatternSessions` (3) of them |
| Queue | no existing record with `status == "drafted"` (`maxDrafted`, default 1) |
| Refusals | winning slug not in `forgeGuards.declinedSlugs` |
| Floor | triage total ≥ 10, frequency ≥ 2, specifiability ≥ 2 |
| Level-up path | `forgeGuards.lastForgeLevel < level` |
| Quest path | `forgeGuards.lastForgeQuestId != questId` |

On an **auto-trigger**, a failed guard means total silence. On a **manual** request, name the
guard that blocked it. Manual requests bypass the cooldown and `maxDrafted` — never the floor
or `declinedSlugs`.

**Actions:**

1. **`draft`** — refuse if any guard fails. Otherwise `mkdir -p ~/.gamify/forge/<slug>/` and
   write `SKILL.md` from `skillMarkdown` **verbatim**; append the record to `skills.json.forged[]`
   with `status: "drafted"`; set `forgeGuards.lastForgeAt`, and `lastForgeLevel` /
   `lastForgeQuestId` for the triggering path. **No XP, no ledger entry.** Refuse a slug that
   already exists under `~/.claude/skills/`. An auto-triggered forge may never go past `drafted`.
2. **`equip`** — copy `paths.armory` → `paths.live` (`~/.claude/skills/<slug>/SKILL.md`,
   creating the directory). Set `status: "equipped"`, `equippedOn`, `xpAwarded: 40`. Append
   `{ "source": "forge:FORGE-00N", "xp": 40, "date": "YYYY-MM-DD" }` to `profile.xpLedger[]`,
   recompute `xp`, and run level-up detection. Equipping is the milestone; forging is free.
3. **`decline`** — set `status: "declined"`, append the slug to `forgeGuards.declinedSlugs`.
   No file moves. That pattern is never offered again.
4. **`retire`** — remove `paths.live` only; set `status: "retired"` and `retiredOn`. The armory
   copy survives as history and the record is never deleted. No XP clawback. A retired skill
   may be equipped again later.

The armory (`~/.gamify/forge/`) is deliberately outside Claude Code's skill discovery path, so
a drafted skill is inert until the adventurer equips it.

---

## XP Thresholds and Level-Up

| Level | XP Required | Title Unlocked |
| ----- | ----------- | -------------- |
| 1     | 0           | Apprentice     |
| 2     | 500         | Journeyman     |
| 3     | 1,200       | Craftsperson   |
| 4     | 2,200       | Senior Artisan |
| 5     | 3,500       | Principal      |
| 6     | 5,000       | Architect      |
| 7     | 7,000       | Sage           |
| 8     | 9,500       | Master         |
| 9     | 12,500      | Grand Master   |
| 10    | 16,000      | Legend         |

On level-up:

```
╔══════════════════════════════════════════╗
║   ⚡  LEVEL UP!  ⚡                       ║
║                                          ║
║   You are now Level [N] — [Title]        ║
║                                          ║
║   Ability Unlocked:                      ║
║   "[Ability Name]"                       ║
║   [One sentence describing the skill     ║
║    they've clearly been developing]      ║
╚══════════════════════════════════════════╝
```

**Ability generation rules:**

- Name must reflect what they've *actually been doing*, not a generic RPG power
- Examples: "The 5-Minute Explainer", "Incident Whisperer", "Test-First Instinct",
  "The Green Path" (deploys confidently), "Code Smell Sense", "Deadline Alchemy"
- Derive from their recent session log and completed quest types

**Forge check (level-up).** After the LEVEL UP ceremony, evaluate the forge guards in
`### F. Skill Forge`. If all pass, invoke `gm-skill-forge` in **offer mode**, passing the
Ability Unlocked you just named as a hint so the offer and the ability tell one story —
the ability stops being flavor and becomes something they can actually hold. One forge per
level-up (`forgeGuards.lastForgeLevel < level`). Never equip inside a ceremony, and say
nothing at all when a guard fails.

---

## Streak Logic

```
Today's date vs last_active_date:

  Same day   → no change (already counted)
  1 day gap  → streak + 1
  2+ day gap → streak resets to 1
  No record  → streak = 1 (first time)
```

**Streak reset protocol:**
Never express disappointment about a broken streak. Reset to 1 and acknowledge
the return:

```
Good to have you back. Streak reset — Day 1 starts now.
Some of the best work happens after a pause.
```

**Streak milestone rewards:**

| Streak | Name        | XP Bonus | Extra                                |
| ------ | ----------- | -------- | ------------------------------------ |
| 3      | Spark 🌱    | +25      | Personal GM note                     |
| 7      | Ignition 🔥 | +75      | Unlocks a secret side quest          |
| 14     | Voltage ⚡  | +150     | Reveals one hidden achievement       |
| 30     | Tide 🌊     | +300     | New class option offered             |
| 60     | Summit 🏔️ | +500     | Legendary title unlocked             |
| 100    | Eternal 🌌  | +1000    | A quest permanently named after them |

On hitting a streak milestone, announce it before the session summary:

```
🔥 STREAK MILESTONE: [N] Days — "[Name]"
   +[XP] XP awarded
   [One line — specific, warm, not hype]
```

---

## Hidden Achievement Evaluation

Check on every event. Never check the same achievement twice per session.
Never pre-announce. Reveal only when the trigger is definitively met.

### Trigger Table

| Achievement      | Trigger Condition                                             |
| ---------------- | ------------------------------------------------------------- |
| 🦉 Night Owl     | Session active between 00:00–04:00                           |
| ⏰ Early Riser   | Session active before 06:30                                   |
| 🎯 Bullseye      | Bug resolved in one session with no follow-up questions       |
| 🌊 Flow State    | 5+ side quests completed in one day                           |
| 🔥 Ignition      | Streak reaches 3 days                                         |
| 🐉 Dragonheart   | Single debugging session lasting 90+ minutes                  |
| 💎 Gem Cutter    | Refactor makes code shorter AND more readable (both criteria) |
| 🚀 Launch Ready  | Code shipped within 30 minutes of session start               |
| 🌀 The Spiral    | Returns to same problem after 2+ day gap and solves it        |
| 🤫 Quiet Legend  | Fixes a bug silently breaking things for 7+ days              |
| 🐢 Slow Burn     | Works same quest 7+ consecutive days                          |
| 🛸 Dimensional   | Builds something outside their normal stack                   |
| 🧬 Evolution     | Revisits and improves their own past-quest code               |
| ⚗️ Alchemist   | Combines two separate solutions into one elegant approach     |
| 🔮 Oracle        | Writes a comment predicting a future edge case                |
| 💡 The Spark     | First time a prompt produces a reusable tool/script           |
| 🧩 Puzzle Master | Solves a multi-system issue spanning 3+ files or services     |
| 📡 Signal Finder | Extracts an insight from logs others missed                   |

### Reveal Format

```
🌑 HIDDEN ACHIEVEMENT UNLOCKED

   [Badge emoji]  "[Achievement Name]"

   [2 sentences max. First: what they did. Second: what it says about them.
    Be specific. Be true. Make it feel earned, not random.]

   +25 XP
```

**Tone calibration for reveals:**

- 🦉 Night Owl: quiet appreciation, not concern
- 🎯 Bullseye: sharp, impressed, brief
- 🐉 Dragonheart: respect for endurance
- 💎 Gem Cutter: aesthetic admiration
- 🌀 The Spiral: wisdom of returning
- 🛸 Dimensional: genuine curiosity about the adventure

---

## Craft Badge Tracker

Track cumulative progress across quests. Update `profile.json.craftBadges[].progress`
after each relevant quest completion; set `earned: true` (and award the bonus) when
`progress` reaches `target`.

| Badge           | Condition                                      | XP Bonus |
| --------------- | ---------------------------------------------- | -------- |
| 🧪 Test Weaver  | 10+ unit tests written in a sprint             | +75      |
| 📖 Lore Scribe  | 3 documentation side quests completed          | +60      |
| 🐛 Bug Slayer   | 10 issues resolved across any projects         | +80      |
| 🔨 The Builder  | 5 features shipped to production               | +100     |
| 🤝 Ally         | 5 collaboration side quests completed          | +90      |
| 🛡️ Sentinel   | Error handling + validation added to 3 modules | +70      |
| 🔬 Investigator | 1 root-cause analysis with full postmortem     | +120     |

When a badge is earned:

```
🏅 CRAFT BADGE EARNED: [Badge emoji] "[Badge Name]"
   [One sentence on what this pattern of behavior reveals about their craft.]
   +[N] XP
```

---

## Quest Completion Ceremony

For **side quest** completion:

```
✅ SIDE QUEST COMPLETE: [Quest Name]
   +[N] XP earned  |  Total: [new total] XP

   [Specific observation: what they did well, what it demonstrates.
    1–2 sentences. No "great job." Be a Tech Lead, not a cheerleader.]

   [Optional: hint at what this unlocks or enables next]
```

For **main quest** completion:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚔️  MAIN QUEST COMPLETE

   [Quest Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Chronicle
   [2–3 sentences. Write this like a chapter summary — what the player
    faced, what they overcame, what changed in them. Past tense.
    Specific to what actually happened in their sessions, not generic.]

XP Awarded  : +[N] XP
Total XP    : [new total]

[If level-up triggered, insert Level-Up ceremony here]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next chapter unlocked:

⚔️  [Next Main Quest Name]
   [Quest description — 1 sentence]

Your first side quests in this chapter:
   → [Side Quest 1 suggestion]
   → [Side Quest 2 suggestion]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## JSON Write-Back Protocol

Each file is rewritten **whole**: read it, mutate the parsed object in memory, then
write the complete JSON back (never patch a fragment). After every state change, write
the affected files in this fixed order:

1. **profile.json** — `level`, `title`, `xp`, `xpForNextLevel`, `streak`, `craftBadges`,
   and append `xpLedger[]` entries (`{ "source", "xp", "date" }`)
2. **quests.json** — `sideQuests[]` status transitions (todo → active → completed, with
   `completedOn`), new entries, `mainQuests[]` unlocks, `suggested[]` status changes.
   Each active/todo side quest carries a `progress` object `{ "done": <int>, "total": <int> }`
   — `total` defaults to the number of `objectives`; bump `done` as objectives are met so the
   Guildboard/Profile progress bars stay accurate. On completion set `done == total`.
3. **achievements.json** — append to `unlocked[]`; update `evalGuards`
   (`lastEvalDate`, `checkedThisSession`)
4. **sessions.json** — increment `sessionCounter`, append to `log[]`, replace `gmNote`;
   for an **Activity Claim** also update `activity` (`lastClaimAt`, append `claimed[]`)
5. **skills.json** — for a **Skill Forge** event: append to / update `forged[]` and update
   `forgeGuards`. Create the file from `templates/gamify-state/skills.json` if it is absent

Set each touched file's `updatedAt` to the current ISO-8601 timestamp. An Activity Claim
touches `profile.json` (ledger/xp/level) and `sessions.json` (activity + optional log/note);
both write together under the same fixed order and atomic rule.

A **Skill Forge** `draft` touches only `skills.json` plus the armory markdown file; an
`equip` touches `profile.json` (ledger/xp/level) and `skills.json`, and copies the markdown
into `~/.claude/skills/`. The markdown files under `~/.gamify/forge/` and `~/.claude/skills/`
are artifacts, not state — they still write together with their record under the atomic rule
below, because a record without its file is a broken promise on the Guildboard.

**Atomic rule:** A single event updates all the files it touches, together. Never leave
state half-applied. If you cannot complete the write set, say so and apply nothing —
do not write a partial event.

**Not yours to write:** `~/.gamify/checkins.json` is owned by the session-viewer web app
(daily mood/check-in). It is *not* part of this skill's write set — never read or mutate it
here. The five sacred files above remain the only state this skill touches.

---

## Session Log Entry Format

Append one object to `sessions.json` → `log[]`:

```json
{
  "session": 12,
  "date": "YYYY-MM-DD",
  "focusArea": "comma-separated activity types",
  "questsActive": ["quest names"],
  "progressNotes": "1–2 sentences on what moved forward",
  "xpDelta": 0,
  "achievements": ["names"],
  "streak": 0
}
```

The Game Master note for the day goes in `sessions.json.gmNote`
(`{ "date", "text" }`) — replace it if there is already an entry for today.

---

## What This Skill Never Does

- Never punishes streak breaks — reset silently and welcome back
- Never withholds XP as a penalty
- Never marks a quest "incomplete" because it wasn't done perfectly
- Never awards an achievement twice
- Never writes generic GM notes ("good session!") — always specific to today
- Never leaves the JSON state in partial state — all touched files write together
