# ⚔️ Gamify — RPG Framework for Claude Code

> *"Every great engineer began as a Level 1 apprentice."*

Turn your daily engineering work into a growth RPG. **Gamify** is a Claude Code plugin that wraps your sessions in narrative, accountability, and momentum — through a Game Master who thinks like your best Tech Lead, your most thoughtful PM, and your most patient mentor.

You write code. The Game Master turns it into a story.

---

## What It Does

Every session, the Game Master:

- **Reads your current state** from `MILESTONES.md` — your quest board, XP ledger, and chronicle
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

Then drop `MILESTONES.md` into your project root or `~/.gamify/`:

```bash
# Copy the template to your project
cp path/to/gamify/templates/MILESTONES.md ./MILESTONES.md

# Or globally (works across all projects)
mkdir -p ~/.gamify
cp path/to/gamify/templates/MILESTONES.md ~/.gamify/MILESTONES.md
```

Edit the `Player Profile` block at the top — set your name, class, and guild. That's it.

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
│   └── gm-quest-tracker/    # XP, streaks, achievements, state
├── hooks/
│   └── hooks.json           # Lifecycle hooks (PreToolUse, PostToolUse, Stop)
└── templates/
    ├── MILESTONES.md        # Your quest board — copy this to your project
    └── ACHIEVEMENTS.md      # Full achievement catalog
```

### The Game Master Agent
A Claude subagent that runs at session start, reads your `MILESTONES.md`, and opens with a briefing: your level, active quests, streak, and one focused question — *"What are we conquering today?"*

### Quest Suggestion Skill
When you have no active quests, or your work drifts from your current quest context, this skill generates 2–3 contextual quest proposals with timelines, expected outcomes, and difficulty ratings. You can **Accept**, **Negotiate** the terms, or say *"Find new quests about [topic]"* to generate a fresh set.

### Quest Tracker Skill
Owns all writes to `MILESTONES.md`. Handles quest completions, XP awards, streak updates, level-up detection, craft badge progress, and all 18 hidden achievement triggers — atomically. It never writes partial state.

### Lifecycle Hooks
Three hooks fire automatically in every Claude Code session:
- `PreToolUse` — logs the activity type and files you're touching
- `PostToolUse` — awards XP per tool call, checks achievement triggers
- `Stop` — writes the session summary back to `MILESTONES.md`

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

## MILESTONES.md

This file is the heart of the framework. It lives in your project root (or `~/.gamify/` for global use) and tracks everything:

- **Player Profile** — name, class, level, XP, streak, last active date
- **Main Quests** — your 8-chapter journey, locked and unlocked
- **Active Side Quests** — what the Game Master has assigned
- **Completed Quests** — your archive of victories
- **Achievements Unlocked** — revealed as earned
- **XP Ledger** — every award, sourced and dated
- **Session Log** — a running chronicle of every session
- **Game Master Notes** — the GM's observations after significant sessions

The hooks update it automatically. The Game Master reads it at the start of every session.

---

## Customization

### Bring Your Own Class
Edit the `Class` field in your `MILESTONES.md` Player Profile. The framework doesn't enforce a class list — choose something that resonates with how you work. *Engineer*, *Architect*, *Sage*, *Alchemist*, *Debugger*, *Scribe* — or something you invent.

### Custom Quests
Tell the Game Master: `"Find new quests about [topic]"` — it will generate a fresh set of proposals tailored to whatever you're building. Accept, negotiate the timeline, or keep generating.

### Multiple Projects
Use a project-root `MILESTONES.md` for project-specific tracking, or `~/.gamify/MILESTONES.md` for a single global profile that follows you across every repo. The Game Master searches for the file in order: project root → repo root → `~/.gamify/`.

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
│   └── gm-quest-tracker/
│       └── SKILL.md         # State management: XP, streaks, achievements
├── hooks/
│   └── hooks.json           # PreToolUse / PostToolUse / Stop handlers
├── scripts/
│   └── gamify_hook.py       # Hook implementation (Python)
└── templates/
    ├── MILESTONES.md        # Quest board template
    └── ACHIEVEMENTS.md      # Achievement catalog
```

### Contributing
PRs welcome. A few things worth knowing before you open one:

- The Game Master's voice is intentional — warm but precise, specific never generic. Changes to `agents/game-master.md` that drift toward cheerleading or vagueness will be declined.
- Quest names should feel like RPG chapter titles, not Jira tickets.
- New achievements should be genuinely earnable through normal engineering behavior — nothing that requires gaming the system.
- All writes to `MILESTONES.md` must go through `gm-quest-tracker` — never direct manipulation from other components.

---

## License

MIT — use it, fork it, build on it.

---

*Gamify v1.0 | Built with Claude Code*
