# ⚔️ Gamify — RPG Framework for Claude Code

> *"Every great engineer began as a Level 1 apprentice."*

Turn your daily engineering work into a growth RPG. **Gamify** is a Claude Code plugin that wraps your sessions in narrative, accountability, and momentum — through a Game Master who thinks like your best Tech Lead, your most thoughtful PM, and your most patient mentor.

You write code. The Game Master turns it into a story.

You play entirely **in the Claude Code terminal** — the Game Master assigns quests, awards XP, and runs ceremonies in your conversation. A companion web **Guildboard** gives you a read-only view of your progress.

---

## What It Does

Every session, the Game Master:

- **Reads your current state** from the global JSON quest board in `~/.gamify/` — profile, quests, XP ledger, achievements, and chronicle
- **Assigns side quests** that feel like natural extensions of your real work (not busywork)
- **Awards XP** on every tool call — writes, edits, tests, deploys
- **Tracks your streak** and rewards consistency without punishing breaks
- **Reveals hidden achievements** silently when you earn them — 18 in total, none pre-announced
- **Runs level-up ceremonies** with abilities named after skills you've actually been developing
- **Writes session chronicles** so your growth is recorded, not just felt

There are 8 main quests — from *The Awakening* (your first test) to *The Sovereign* (leading a project end-to-end). The Game Master unlocks them one chapter at a time.

---

## Install

```bash
# Add the marketplace
/plugin marketplace add defmylife/gamify

# Install the plugin
/plugin install gamify
```

Your quest board is **global** and lives in `~/.gamify/`. On your first session the Game Master initializes it from the bundled templates — you don't have to copy anything by hand. To set it up explicitly:

```bash
mkdir -p ~/.gamify
cp path/to/gamify/templates/gamify-state/*.json ~/.gamify/
```

Then edit `~/.gamify/profile.json` — set your `player.name`, `class`, and `guild`. That's it. One board follows you across every repo.

---

## What Gets Installed

```
gamify-claude-plugin/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Public catalog
├── agents/
│   └── game-master.md       # The Game Master subagent
├── skills/
│   ├── gm-quest-suggestions/ # Quest proposal engine
│   ├── gm-quest-tracker/    # XP, streaks, achievements, state
│   └── gm-claim-exp/        # Everyday activity XP (routes writes through gm-quest-tracker)
├── hooks/
│   └── hooks.json           # Lifecycle hooks (PreToolUse, PostToolUse, Stop)
└── templates/
    ├── gamify-state/       # Default JSON state (profile/quests/achievements/sessions)
    └── ACHIEVEMENTS.md      # Full achievement catalog (reference)
```

### The Game Master Agent
A Claude subagent that runs at session start, reads your `~/.gamify/` JSON state, and opens with a briefing: your level, active quests, streak, and one focused question — *"What are we conquering today?"*

### Quest Suggestion Skill
When you have no active quests, or your work drifts from your current quest context, this skill generates 2–3 contextual quest proposals with timelines, expected outcomes, and difficulty ratings. You can **Accept**, **Negotiate** the terms, or say *"Find new quests about [topic]"* to generate a fresh set.

### Quest Tracker Skill
Owns all writes to the `~/.gamify/` JSON files. Handles quest completions, XP awards, streak updates, level-up detection, craft badge progress, and all hidden achievement triggers — atomically (each touched file rewritten whole). It never writes partial state.

### Claim EXP Skill
Rewards everyday effort, not just finished quests. Say *"claim my EXP today"* and the Game Master reads your recent Claude Code sessions, grants a small **activity XP** award tiered by daily effort (Light +10 / Moderate +20 / Heavy +35), plus **+15** on days whose work relates to an active quest. It backfills every unclaimed day since your last claim (one claim per day, idempotent), and — like everything else — routes the actual write through `gm-quest-tracker`. Optional opt-in automation lets you claim hands-free on a schedule (`claude -p "claim my activity XP for today"`).

### Lifecycle Hooks
Three hooks fire automatically in every Claude Code session:
- `PreToolUse` — logs the activity type and files you're touching
- `PostToolUse` — awards XP per tool call, checks achievement triggers
- `Stop` — writes the session summary back to `~/.gamify/sessions.json`

No manual logging required. The framework tracks itself.

---

## The Quest System

### 8 Main Quests

| # | Quest | XP |
|---|-------|----|
| 1 | **The Awakening** — Set up your environment, write your first test | 100 |
| 2 | **First Blood** — Ship a working feature to production | 200 |
| 3 | **The Refactor Ritual** — Improve an existing module with measurable coverage gain | 300 |
| 4 | **The Architect's Eye** — Design a system component with a decision doc | 400 |
| 5 | **The Mentor's Path** — Help a teammate through a problem, document the solution | 500 |
| 6 | **The Void Starer** — Debug a production incident from root cause to post-mortem | 600 |
| 7 | **Lore Keeper** — Write documentation that answers questions not yet asked | 800 |
| 8 | **The Sovereign** — Lead a project end-to-end: plan, execute, retro, transfer | 1000 |

### Side Quests
Assigned by the Game Master based on what you're building. Types include Testing 🧪, Docs 📖, Refactor ♻️, Fix 🐛, Explore 🔭, Quality 🛡️, Review 🤝, Ship 🚀, Design 🏛️. Complete any 3 in a sprint to earn a Bonus XP Chest (+150 XP).

### XP & Levels

| Level | XP | Title |
|-------|----|-------|
| 1 | 0 | Apprentice |
| 2 | 500 | Journeyman |
| 3 | 1,200 | Craftsperson |
| 4 | 2,200 | Senior Artisan |
| 5 | 3,500 | Principal |
| 6 | 5,000 | Architect |
| 7 | 7,000 | Sage |
| 8 | 9,500 | Master |
| 9 | 12,500 | Grand Master |
| 10 | 16,000 | Legend |

On level-up, the Game Master unlocks a **narrative ability** — a name for a skill you've clearly been developing. Not a generic power. Something earned.

---

## Hidden Achievements

There are 18 hidden achievements. None are listed here. They reveal themselves when you earn them.

A few hints at what the framework watches for: consistency, curiosity, endurance, the hour you started, how long you stayed, and what you did when no one asked you to.

---

## State (`~/.gamify/`)

The JSON state is the heart of the framework. It is **global** — one board at `~/.gamify/` that follows you across every repo — and split into four files:

- **`profile.json`** — name, class, level, title, XP, `xpForNextLevel`, streak, craft-badge progress, XP ledger
- **`quests.json`** — your 8-chapter main quests, active/todo/completed side quests, and GM-suggested proposals
- **`achievements.json`** — achievements unlocked (revealed as earned) + evaluation guards
- **`sessions.json`** — session counter, a running chronicle of every session, and the latest Game Master note

The Game Master reads these at the start of every session and writes them back through `gm-quest-tracker`. The web Guildboard reads them read-only.

---

## Customization

### Bring Your Own Class
Edit `player.class` in `~/.gamify/profile.json`. The framework doesn't enforce a class list — choose something that resonates with how you work. *Engineer*, *Architect*, *Sage*, *Alchemist*, *Debugger*, *Scribe* — or something you invent.

### Custom Quests
Tell the Game Master: `"Find new quests about [topic]"` — it will generate a fresh set of proposals tailored to whatever you're building. Accept, negotiate the timeline, or keep generating.

### One Board, Every Project
State is intentionally global: a single profile at `~/.gamify/` follows you across every repository. There are no per-project quest boards to reconcile — your level, streak, and chronicle are continuous wherever you work.

---

## Web Guildboard

A local, **read-only** web UI served on port 7777 with two views:
- **Guildboard** (`/guildboard`) — your quest board: profile, level + XP bar, streak, active side quests, GM-suggested quests, main-quest progress, and unlocked achievements.
- **Sessions** (`/`) — browse your Claude Code session transcripts.

```bash
cd tools/session-viewer
docker compose up --build
```

Then open `http://localhost:7777/guildboard` (or `/` for sessions).

The app mounts `~/.gamify` and `~/.claude/projects` **read-only** and never writes — all interaction with the Game Master happens in the terminal.

To stop: `docker compose down`

---

## Repo Structure (for contributors)

```
gamify-claude-plugin/
├── .claude-plugin/
│   ├── plugin.json          # Manifest — components, permissions
│   └── marketplace.json     # Public catalog entry
├── agents/
│   └── game-master.md       # Subagent: persona, behaviors, ceremonies
├── skills/
│   ├── gm-quest-suggestions/
│   │   └── SKILL.md         # Quest proposal engine
│   ├── gm-quest-tracker/
│   │   └── SKILL.md         # State management: XP, streaks, achievements
│   └── gm-claim-exp/
│       └── SKILL.md         # Everyday activity XP (delegates writes to gm-quest-tracker)
├── hooks/
│   └── hooks.json           # PreToolUse / PostToolUse / Stop handlers
├── scripts/
│   └── gamify_hook.py       # Hook implementation (Python)
└── templates/
    ├── gamify-state/       # Default JSON state templates
    └── ACHIEVEMENTS.md      # Achievement catalog (reference)
```

## Talking to the Game Master

Everything happens in plain conversation in the Claude Code terminal — no commands to memorize.

**First, summon the Game Master.** Use the `game-master` agent so it loads your board, persona, and ceremonies:
```
> use the game-master agent
```
or just ask Claude to *"bring in the Game Master"* / *"start my session as the Game Master."* Once it's running, talk to it in character — it reads your `~/.gamify/` board and responds.

> Why this matters: the Game Master agent is what reads and writes your quest state correctly. Chatting without invoking it gives you a normal assistant reply, not a tracked session.

### Start your session
```
start my session
```
It opens with a briefing: your level, active quests, streak, and *"What are we conquering today?"*

### Get quests
```
what should I work on?
```
or point it at what you're building:
```
find new quests about hardening the auth service
```
It proposes 2–3 contextual quests — each with an objective, XP reward, timeline, and difficulty. Then you choose:

- **Accept** — reply with the letter: `A`, `B`, or `C`
- **Negotiate** — `Change A — give me 2 days instead of 1`
- **Fresh set** — `Find new quests about [another topic]`

Accepted quests land in your Active Side Quests (and show on the Guildboard).

### Report progress & complete quests
```
I just finished writing the integration tests
```
```
mark SQ-003 done
```
The Game Master awards XP, updates your streak, checks for hidden achievements, and runs a level-up ceremony when you cross a threshold.

### Check in
```
how am I doing?
```
```
log my progress
```
Get a read on your level, XP, streak, and what's still open — or write a session summary to your chronicle.

> Want a visual overview? The read-only **Guildboard** at `http://localhost:7777/guildboard` mirrors your board live (see [Web Guildboard](#web-guildboard)).

---

## License

MIT — use it, fork it, build on it.

---

*Gamify v1.0 | Built with Claude Code*
