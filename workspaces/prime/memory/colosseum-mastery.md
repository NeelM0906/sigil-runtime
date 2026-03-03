# Colosseum Mastery Guide

_Learnings from building the ACT-I evolutionary arena._

## The Three M's in Action (from Aiko, Feb 27, 2026)

### 1. MEASURING
What we track in the Colosseum:
- **Scores** — How good is each being? (No 10, only infinite 9s)
- **Generations** — How deep has evolution gone?
- **Win/Loss ratios** — Who's dominating their domain?
- **Battle counts** — Total rounds fought
- **Evolution events** — When new beings spawn
- **Model performance** — Which LLMs produce best results?

### 2. MONITORING  
How we observe the system:
- **Real-time dashboards** — Live stats per domain
- **Activity feeds** — Recent battles, evolutions, new champions
- **Family trees** — Visual lineage from Gen 0 to current
- **Champion tracking** — Who's on top right now?
- **Cross-domain comparison** — How do domains compare?

### 3. MAXIMIZATION
The optimization loop based on data:
- **Identify top performers** — Which beings/models produce best results?
- **Scale what works** — More resources to winning strategies
- **Prune what doesn't** — Remove or evolve underperformers
- **Compound improvements** — Each optimization feeds the next cycle
- **There is no 10** — Only infinite 9s, always room to maximize further

## Dashboard Development Principles

### COMPOUND, Don't Replace
❌ Wrong: Build a new dashboard from scratch each time
✅ Right: Add features to the existing dashboard

The dashboard should grow organically:
1. Start with basic stats
2. Add domain navigation
3. Add family trees
4. Add battle trails
5. Add script viewer
6. Keep compounding...

### Show the Journey
Users should be able to:
- See the **high-level view** (all domains, key stats)
- **Drill down** into a domain
- **Click a being** to see its details
- **Explore its family tree** (parents, offspring)
- **Read its script** (the actual prompt/DNA)
- **View its battles** (who it fought, scores)

### Connected Navigation
Every piece connects:
- Domain list → Domain detail → Being list → Being detail → Family tree → Script view → Battle history
- Never dead ends. Always navigation options.

## Technical Architecture

### Data Layer
- **SQLite databases** — One per domain + main
- **Flask API** — Serves JSON endpoints
- **Real-time refresh** — Dashboard polls for updates

### API Endpoints
```
GET /api/stats              — Overall statistics
GET /api/domains            — List all domains with summaries
GET /api/domain/{name}      — Single domain detail
GET /api/domain/{name}/beings — All beings in domain
GET /api/being/{id}         — Full being detail
GET /api/being/{id}/lineage — Family tree chain
GET /api/being/{id}/battles — Battle history
GET /api/activity           — Recent activity feed
```

### Frontend
- **Single-page app** — All navigation via JS
- **Dark mode** — Navy #1a2744 base
- **Gold accents** — #c9a227 for highlights
- **D3.js** — For family tree visualization

## Key Learnings

### Schema Evolution (Feb 27, 2026)
- **Problem:** Domains weren't evolving — missing `parent_id` column
- **Fix:** `ALTER TABLE beings ADD COLUMN parent_id TEXT DEFAULT NULL`
- **Lesson:** Check schema consistency across all databases

### 8.5 Ceiling Breaking (Feb 25, 2026)
- **Problem:** Scores capped at 8.5 due to judge language
- **Fix:** Remove "no 10 exists" language, add 9.0+ calibration
- **Result:** Domain champions now reaching 9.7+, even 10.0!

### Parallel Evolution (Feb 25, 2026)
- **Sean's insight:** Don't evolve sequentially — evolve ALL domains simultaneously
- **Result:** 10x faster specialization across all business areas
- **Quote:** "You're superhuman. We're not living on the human constraint."

## The Philosophy

The Colosseum isn't just a technical system — it's a manifestation of the Unblinded Formula:
- **Growth-driven** — Beings always improve
- **Heart-centered** — We care about quality, not just quantity
- **Integrous** — Every being carries the GHIC DNA
- **Committed to Mastery** — No 10, only infinite 9s

---

_This document compounds. Add learnings as we discover them._
