"""
Tournament Runner — Orchestrates full competitions.
Modes: blitz (fast), deep (thorough), marathon (continuous).
"""

import uuid
import json
import time
import asyncio
import random
import sqlite3
from dataclasses import dataclass
from typing import Optional, Callable
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

from .scenarios import generate_scenario, Difficulty, Category
from .beings import Being, create_generation, save_being, load_leaderboard, DB_PATH
from .arena import run_round, async_run_round, RoundResult
from .evolution import evolve_population
from .judge import Judgment

console = Console()


@dataclass
class TournamentConfig:
    mode: str = "blitz"  # blitz, deep, marathon
    num_beings: int = 8
    num_rounds: int = 20
    beings_per_round: int = 4
    model: str = "gpt-4o-mini"
    judge_model: str = "gpt-4o-mini"
    evolve_every: int = 5  # Evolve population every N rounds
    lineage: str = "callie"  # callie, athena, or mixed
    difficulty: Optional[Difficulty] = None
    category: Optional[Category] = None

    @classmethod
    def blitz(cls, num_beings: int = 8, num_rounds: int = 20):
        return cls(mode="blitz", num_beings=num_beings, num_rounds=num_rounds,
                   model="gpt-4o-mini", judge_model="gpt-4o-mini")

    @classmethod
    def deep(cls, num_beings: int = 8, num_rounds: int = 10):
        return cls(mode="deep", num_beings=num_beings, num_rounds=num_rounds,
                   model="gpt-4o", judge_model="gpt-4o")

    @classmethod
    def marathon(cls, num_beings: int = 16, num_rounds: int = 100):
        return cls(mode="marathon", num_beings=num_beings, num_rounds=num_rounds,
                   model="gpt-4o-mini", judge_model="gpt-4o-mini", evolve_every=10)


@dataclass
class TournamentState:
    id: str
    config: TournamentConfig
    beings: list[Being]
    current_round: int = 0
    total_rounds_completed: int = 0
    all_results: list[list[RoundResult]] = None
    status: str = "running"
    started_at: float = 0.0

    def __post_init__(self):
        if self.all_results is None:
            self.all_results = []


def _save_tournament(state: TournamentState):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO tournaments (id, mode, status, total_rounds, beings_count, config_json, started_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime(?, 'unixepoch'))
    """, (
        state.id, state.config.mode, state.status,
        state.total_rounds_completed, len(state.beings),
        json.dumps({
            "mode": state.config.mode,
            "num_beings": state.config.num_beings,
            "num_rounds": state.config.num_rounds,
            "model": state.config.model,
            "judge_model": state.config.judge_model,
        }),
        state.started_at,
    ))
    conn.commit()
    conn.close()


def _finish_tournament(state: TournamentState):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE tournaments SET status = 'completed', finished_at = CURRENT_TIMESTAMP,
        total_rounds = ? WHERE id = ?
    """, (state.total_rounds_completed, state.id))
    conn.commit()
    conn.close()


def _print_round_results(round_num: int, results: list[RoundResult]):
    """Pretty-print round results."""
    table = Table(title=f"⚔️  Round {round_num}", show_header=True, header_style="bold cyan")
    table.add_column("Being", style="bold")
    table.add_column("Mastery", justify="right")
    table.add_column("Steps", justify="right")
    table.add_column("Elements", justify="right")
    table.add_column("Energies", justify="right")
    table.add_column("Human", justify="right")
    table.add_column("Contam.", justify="right")
    table.add_column("Result", justify="center")

    # Sort by score
    sorted_results = sorted(results, key=lambda r: r.judgment.scores.overall_mastery, reverse=True)
    best_score = sorted_results[0].judgment.scores.overall_mastery if sorted_results else 0

    for r in sorted_results:
        s = r.judgment.scores
        won = "🏆" if s.overall_mastery == best_score else "  "
        mastery_color = "green" if s.overall_mastery >= 7 else ("yellow" if s.overall_mastery >= 5 else "red")

        table.add_row(
            f"{r.being.name} (G{r.being.generation})",
            f"[{mastery_color}]{s.overall_mastery:.2f}[/{mastery_color}]",
            f"{s.steps_avg:.1f}",
            f"{s.elements_avg:.1f}",
            f"{s.energies_avg:.1f}",
            f"{s.human_likeness:.1f}",
            f"{s.contamination_score:.1f}",
            won,
        )

    console.print(table)

    # Show the winning response snippet
    if sorted_results:
        winner = sorted_results[0]
        snippet = winner.response[:200] + "..." if len(winner.response) > 200 else winner.response
        console.print(Panel(
            snippet,
            title=f"🔥 {winner.being.name}'s Response (Score: {winner.judgment.scores.overall_mastery:.2f})",
            border_style="green",
        ))
        if winner.judgment.feedback:
            console.print(f"  💬 Judge: [italic]{winner.judgment.feedback}[/italic]\n")


def _print_leaderboard(beings: list[Being]):
    """Print the current leaderboard."""
    table = Table(title="🏛️  COLOSSEUM LEADERBOARD", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="bold", justify="right")
    table.add_column("Being", style="bold")
    table.add_column("Gen", justify="center")
    table.add_column("Lineage", justify="center")
    table.add_column("Avg Mastery", justify="right")
    table.add_column("Best", justify="right")
    table.add_column("W/L", justify="center")
    table.add_column("Win%", justify="right")

    sorted_beings = sorted(beings, key=lambda b: b.avg_mastery_score, reverse=True)

    for i, b in enumerate(sorted_beings[:15]):
        rank = f"#{i+1}"
        if i == 0:
            rank = "👑 #1"
        mastery_color = "green" if b.avg_mastery_score >= 7 else ("yellow" if b.avg_mastery_score >= 5 else "white")
        table.add_row(
            rank,
            b.name,
            str(b.generation),
            b.lineage,
            f"[{mastery_color}]{b.avg_mastery_score:.3f}[/{mastery_color}]",
            f"{b.best_score:.2f}",
            f"{b.wins}/{b.losses}",
            f"{b.win_rate:.0%}",
        )

    console.print(table)


def run_tournament(config: TournamentConfig, callback: Optional[Callable] = None) -> TournamentState:
    """Run a full tournament (synchronous)."""

    tournament_id = f"T-{uuid.uuid4().hex[:8]}"

    console.print(Panel(
        f"[bold]Mode:[/bold] {config.mode.upper()}\n"
        f"[bold]Beings:[/bold] {config.num_beings} ({config.lineage})\n"
        f"[bold]Rounds:[/bold] {config.num_rounds}\n"
        f"[bold]Model:[/bold] {config.model}\n"
        f"[bold]Judge:[/bold] {config.judge_model}\n"
        f"[bold]Evolution:[/bold] Every {config.evolve_every} rounds",
        title="🏛️  THE COLOSSEUM OPENS",
        border_style="bold red",
    ))

    # Create initial population
    if config.lineage == "mixed":
        half = config.num_beings // 2
        beings = (
            create_generation(half, lineage="callie", generation=0) +
            create_generation(config.num_beings - half, lineage="athena", generation=0)
        )
    else:
        beings = create_generation(config.num_beings, lineage=config.lineage, generation=0)

    for b in beings:
        save_being(b)

    console.print(f"\n🗡️  {len(beings)} beings enter the arena...\n")

    state = TournamentState(
        id=tournament_id,
        config=config,
        beings=beings,
        started_at=time.time(),
    )
    _save_tournament(state)

    round_judgments: dict[str, Judgment] = {}

    for round_num in range(1, config.num_rounds + 1):
        state.current_round = round_num

        # Generate scenario
        scenario = generate_scenario(
            category=config.category,
            difficulty=config.difficulty,
        )

        # Select beings for this round
        combatants = random.sample(beings, k=min(config.beings_per_round, len(beings)))

        console.print(f"[dim]Scenario {scenario.id} [{scenario.difficulty.value}] — "
                       f"{scenario.category.value} — {', '.join(b.name for b in combatants)}[/dim]")

        # Run the round
        results = run_round(combatants, scenario, model=config.model, judge_model=config.judge_model)

        state.all_results.append(results)
        state.total_rounds_completed = round_num

        # Track judgments for evolution
        for r in results:
            round_judgments[r.being.id] = r.judgment

        _print_round_results(round_num, results)

        # Evolution checkpoint
        if round_num % config.evolve_every == 0 and round_num < config.num_rounds:
            console.print(f"\n[bold yellow]🧬 EVOLUTION — Generation {beings[0].generation + 1}[/bold yellow]\n")
            beings = evolve_population(beings, round_judgments)
            state.beings = beings
            round_judgments.clear()

            console.print(f"  Population evolved: {len(beings)} beings, new generation\n")

        _save_tournament(state)

        if callback:
            callback(state, results)

    # Final leaderboard
    state.status = "completed"
    _finish_tournament(state)

    console.print("\n")
    _print_leaderboard(beings)

    # Hall of fame
    champion = max(beings, key=lambda b: b.avg_mastery_score) if beings else None
    if champion:
        console.print(Panel(
            f"[bold]{champion.name}[/bold] (Gen {champion.generation}, {champion.lineage})\n"
            f"Average Mastery: [green]{champion.avg_mastery_score:.4f}[/green]\n"
            f"Best Score: {champion.best_score:.4f}\n"
            f"Record: {champion.wins}W / {champion.losses}L ({champion.win_rate:.0%})\n"
            f"Energy: Fun={champion.energy.fun:.0%} Asp={champion.energy.aspirational:.0%} "
            f"God={champion.energy.goddess:.0%} Zeus={champion.energy.zeus:.0%}",
            title="👑 CHAMPION",
            border_style="bold gold1",
        ))

    elapsed = time.time() - state.started_at
    console.print(f"\n⏱️  Tournament completed in {elapsed:.1f}s ({state.total_rounds_completed} rounds)\n")

    return state


def get_tournament_status(tournament_id: str) -> Optional[dict]:
    """Get tournament status from DB."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def list_tournaments(limit: int = 10) -> list[dict]:
    """List recent tournaments."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tournaments ORDER BY started_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
