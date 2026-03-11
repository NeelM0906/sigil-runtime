#!/usr/bin/env python3
"""
🏛️ The Colosseum Daemon — Continuous Tournament Runner

A 24/7 automation framework that:
- Runs tournaments continuously
- Automatically evolves beings after each round
- Logs results to rotating log files
- Reports summary stats every hour
- Can be controlled via launchctl (macOS) or systemctl (Linux)

Usage:
    python colosseum_daemon.py              # Run in foreground
    python colosseum_daemon.py --daemon     # Run as daemon (background)
    python colosseum_daemon.py --status     # Show daemon status
    python colosseum_daemon.py --stop       # Stop daemon gracefully

Zone Action #31 — Built by Miner 21
"""

import os
import sys
import json
import time
import signal
import argparse
import logging
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from threading import Thread, Event
import traceback

# Ensure API key is loaded
# Always load env file to get all API keys (OPENROUTER, OPENAI, etc.)
env_path = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Add colosseum to path
sys.path.insert(0, str(Path(__file__).parent))

from colosseum.tournament import TournamentConfig
from colosseum.scenarios import generate_scenario, Difficulty, Category
from colosseum.beings import (
    Being, create_generation, save_being, load_all_beings, 
    load_leaderboard, DB_PATH, init_db
)
from colosseum.arena import run_round, RoundResult
from colosseum.evolution_v2 import evolve_population_v2, EvolutionConfig
from colosseum.judge import Judgment


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class DaemonConfig:
    """Configuration for the continuous tournament daemon."""
    # Tournament settings
    num_beings: int = 12
    beings_per_round: int = 4
    evolve_every: int = 5
    model: str = "anthropic/claude-opus-4.5"
    judge_model: str = "o1"
    lineage: str = "mixed"  # callie, athena, or mixed
    
    # Daemon settings
    round_delay_seconds: int = 5  # Pause between rounds
    hourly_report: bool = True
    max_rounds_per_session: int = 0  # 0 = unlimited
    
    # Paths
    log_dir: Path = Path(__file__).parent / "logs"
    pid_file: Path = Path(__file__).parent / "colosseum_daemon.pid"
    state_file: Path = Path(__file__).parent / "daemon_state.json"
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['log_dir'] = str(self.log_dir)
        d['pid_file'] = str(self.pid_file)
        d['state_file'] = str(self.state_file)
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> 'DaemonConfig':
        d = d.copy()
        d['log_dir'] = Path(d.get('log_dir', Path(__file__).parent / "logs"))
        d['pid_file'] = Path(d.get('pid_file', Path(__file__).parent / "colosseum_daemon.pid"))
        d['state_file'] = Path(d.get('state_file', Path(__file__).parent / "daemon_state.json"))
        return cls(**d)


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(log_dir: Path) -> logging.Logger:
    """Setup rotating log files."""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger('colosseum_daemon')
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Rotating file handler - 10MB max, keep 10 backup files
    file_handler = RotatingFileHandler(
        log_dir / "colosseum_daemon.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler for foreground mode
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '🏛️  %(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


# ============================================================================
# Daemon State
# ============================================================================

@dataclass
class DaemonState:
    """Persistent state for the daemon."""
    started_at: str = ""
    total_rounds: int = 0
    total_evolutions: int = 0
    total_beings_created: int = 0
    current_session_rounds: int = 0
    last_hourly_report: str = ""
    hourly_stats: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.hourly_stats is None:
            self.hourly_stats = {
                'rounds': 0,
                'evolutions': 0,
                'avg_score': 0.0,
                'best_score': 0.0,
                'best_being': '',
            }
    
    def save(self, path: Path):
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> 'DaemonState':
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                return cls(**data)
        return cls()


# ============================================================================
# The Daemon
# ============================================================================

class ColosseumDaemon:
    """Continuous tournament runner daemon."""
    
    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = setup_logging(config.log_dir)
        self.state = DaemonState.load(config.state_file)
        self.shutdown_event = Event()
        self.beings: list[Being] = []
        self.round_judgments: Dict[str, Judgment] = {}
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name} — initiating graceful shutdown...")
        self.shutdown_event.set()
    
    def _setup_signals(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGHUP, self._signal_handler)
    
    def _write_pid(self):
        """Write PID file for daemon management."""
        self.config.pid_file.write_text(str(os.getpid()))
        self.logger.debug(f"PID {os.getpid()} written to {self.config.pid_file}")
    
    def _remove_pid(self):
        """Remove PID file on shutdown."""
        if self.config.pid_file.exists():
            self.config.pid_file.unlink()
            self.logger.debug("PID file removed")
    
    def _initialize_population(self):
        """Initialize or load the being population."""
        existing = load_all_beings()
        
        if existing and len(existing) >= self.config.num_beings:
            # Use top performers from existing population
            self.beings = sorted(
                existing, 
                key=lambda b: b.avg_mastery_score, 
                reverse=True
            )[:self.config.num_beings]
            self.logger.info(f"Loaded {len(self.beings)} beings from database")
        else:
            # Create fresh population
            if self.config.lineage == "mixed":
                half = self.config.num_beings // 2
                self.beings = (
                    create_generation(half, lineage="callie", generation=0) +
                    create_generation(self.config.num_beings - half, lineage="athena", generation=0)
                )
            else:
                self.beings = create_generation(
                    self.config.num_beings, 
                    lineage=self.config.lineage, 
                    generation=0
                )
            
            for b in self.beings:
                save_being(b)
            
            self.state.total_beings_created += len(self.beings)
            self.logger.info(f"Created {len(self.beings)} new beings ({self.config.lineage})")
    
    def _run_single_round(self) -> list[RoundResult]:
        """Run a single tournament round."""
        # Generate scenario
        scenario = generate_scenario()
        
        # Select combatants
        combatants = random.sample(
            self.beings, 
            k=min(self.config.beings_per_round, len(self.beings))
        )
        
        self.logger.debug(
            f"Round scenario: {scenario.id} [{scenario.difficulty.value}] "
            f"Category: {scenario.category.value}"
        )
        self.logger.debug(f"Combatants: {', '.join(b.name for b in combatants)}")
        
        # Run the round
        results = run_round(
            combatants, 
            scenario, 
            model=self.config.model, 
            judge_model=self.config.judge_model
        )
        
        # Track judgments for evolution
        for r in results:
            self.round_judgments[r.being.id] = r.judgment
        
        return results
    
    def _log_round_results(self, round_num: int, results: list[RoundResult]):
        """Log round results."""
        sorted_results = sorted(
            results, 
            key=lambda r: r.judgment.scores.overall_mastery, 
            reverse=True
        )
        
        winner = sorted_results[0] if sorted_results else None
        
        if winner:
            scores = winner.judgment.scores
            self.logger.info(
                f"Round {round_num} complete — Winner: {winner.being.name} "
                f"(G{winner.being.generation}) Score: {scores.overall_mastery:.2f}"
            )
            
            # Update hourly stats
            all_scores = [r.judgment.scores.overall_mastery for r in results]
            avg = sum(all_scores) / len(all_scores) if all_scores else 0
            
            self.state.hourly_stats['rounds'] += 1
            
            # Running average
            prev_avg = self.state.hourly_stats['avg_score']
            n = self.state.hourly_stats['rounds']
            self.state.hourly_stats['avg_score'] = (prev_avg * (n-1) + avg) / n
            
            if scores.overall_mastery > self.state.hourly_stats['best_score']:
                self.state.hourly_stats['best_score'] = scores.overall_mastery
                self.state.hourly_stats['best_being'] = winner.being.name
    
    def _perform_evolution(self):
        """Evolve the population."""
        self.logger.info("🧬 EVOLUTION — Natural selection in progress...")
        
        old_gen = self.beings[0].generation if self.beings else 0
        self.beings, evolution_stats = evolve_population_v2(self.beings, self.round_judgments, EvolutionConfig())
        self.logger.info(f"Evolution stats: {evolution_stats}")
        new_gen = self.beings[0].generation if self.beings else 0
        
        self.round_judgments.clear()
        
        self.state.total_evolutions += 1
        self.state.hourly_stats['evolutions'] += 1
        
        new_beings = sum(1 for b in self.beings if b.generation == new_gen)
        self.state.total_beings_created += new_beings
        
        self.logger.info(
            f"Evolution complete — Gen {old_gen} → {new_gen} | "
            f"Population: {len(self.beings)} | New beings: {new_beings}"
        )
    
    def _hourly_report(self):
        """Generate and log hourly summary report."""
        now = datetime.now().isoformat()
        
        # Get leaderboard
        leaders = load_leaderboard(limit=5)
        
        report_lines = [
            "",
            "=" * 60,
            f"📊 HOURLY REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            "",
            f"Rounds this hour: {self.state.hourly_stats['rounds']}",
            f"Evolutions: {self.state.hourly_stats['evolutions']}",
            f"Avg mastery score: {self.state.hourly_stats['avg_score']:.3f}",
            f"Best score: {self.state.hourly_stats['best_score']:.2f} ({self.state.hourly_stats['best_being']})",
            "",
            "🏆 Current Leaderboard:",
        ]
        
        for i, b in enumerate(leaders):
            report_lines.append(
                f"  #{i+1} {b.name} (G{b.generation}) — "
                f"Avg: {b.avg_mastery_score:.3f} | W/L: {b.wins}/{b.losses}"
            )
        
        report_lines.extend([
            "",
            f"📈 Total stats since start:",
            f"   Rounds: {self.state.total_rounds}",
            f"   Evolutions: {self.state.total_evolutions}",
            f"   Beings created: {self.state.total_beings_created}",
            "=" * 60,
            "",
        ])
        
        for line in report_lines:
            self.logger.info(line)
        
        # Reset hourly stats
        self.state.last_hourly_report = now
        self.state.hourly_stats = {
            'rounds': 0,
            'evolutions': 0,
            'avg_score': 0.0,
            'best_score': 0.0,
            'best_being': '',
        }
        self.state.save(self.config.state_file)
    
    def _should_report(self) -> bool:
        """Check if an hourly report is due."""
        if not self.config.hourly_report:
            return False
        
        if not self.state.last_hourly_report:
            return True
        
        try:
            last = datetime.fromisoformat(self.state.last_hourly_report)
            return datetime.now() - last >= timedelta(hours=1)
        except:
            return True
    
    def run(self):
        """Main daemon loop."""
        self._setup_signals()
        self._write_pid()
        
        # Initialize state
        if not self.state.started_at:
            self.state.started_at = datetime.now().isoformat()
        self.state.current_session_rounds = 0
        
        self.logger.info("=" * 60)
        self.logger.info("🏛️  THE COLOSSEUM DAEMON AWAKENS")
        self.logger.info("=" * 60)
        self.logger.info(f"Configuration:")
        self.logger.info(f"  Beings: {self.config.num_beings} ({self.config.lineage})")
        self.logger.info(f"  Model: {self.config.model}")
        self.logger.info(f"  Judge: {self.config.judge_model}")
        self.logger.info(f"  Evolution: Every {self.config.evolve_every} rounds")
        self.logger.info(f"  Round delay: {self.config.round_delay_seconds}s")
        self.logger.info("=" * 60)
        
        # Initialize DB and population
        init_db()
        self._initialize_population()
        
        round_num = 0
        
        try:
            while not self.shutdown_event.is_set():
                round_num += 1
                self.state.total_rounds += 1
                self.state.current_session_rounds += 1
                
                # Check max rounds
                if self.config.max_rounds_per_session > 0:
                    if self.state.current_session_rounds > self.config.max_rounds_per_session:
                        self.logger.info(
                            f"Max rounds ({self.config.max_rounds_per_session}) reached — stopping"
                        )
                        break
                
                # Run round
                try:
                    results = self._run_single_round()
                    self._log_round_results(round_num, results)
                except Exception as e:
                    self.logger.error(f"Round {round_num} failed: {e}")
                    self.logger.debug(traceback.format_exc())
                    time.sleep(30)  # Back off on error
                    continue
                
                # Evolution checkpoint
                if round_num % self.config.evolve_every == 0:
                    try:
                        self._perform_evolution()
                    except Exception as e:
                        self.logger.error(f"Evolution failed: {e}")
                        self.logger.debug(traceback.format_exc())
                
                # Hourly report
                if self._should_report():
                    self._hourly_report()
                
                # Save state periodically
                if round_num % 10 == 0:
                    self.state.save(self.config.state_file)
                
                # Delay between rounds
                if self.config.round_delay_seconds > 0:
                    self.shutdown_event.wait(self.config.round_delay_seconds)
        
        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}")
            self.logger.error(traceback.format_exc())
        
        finally:
            # Final report and cleanup
            self.logger.info("=" * 60)
            self.logger.info("🏛️  DAEMON SHUTDOWN")
            self.logger.info(f"Session rounds completed: {self.state.current_session_rounds}")
            self.logger.info(f"Total rounds all-time: {self.state.total_rounds}")
            self.logger.info("=" * 60)
            
            self.state.save(self.config.state_file)
            self._remove_pid()
    
    @classmethod
    def status(cls, config: DaemonConfig) -> dict:
        """Get daemon status."""
        status = {
            'running': False,
            'pid': None,
            'state': None,
        }
        
        if config.pid_file.exists():
            pid = int(config.pid_file.read_text().strip())
            # Check if process is running
            try:
                os.kill(pid, 0)
                status['running'] = True
                status['pid'] = pid
            except OSError:
                status['running'] = False
        
        if config.state_file.exists():
            status['state'] = DaemonState.load(config.state_file)
        
        return status
    
    @classmethod
    def stop(cls, config: DaemonConfig) -> bool:
        """Stop the daemon gracefully."""
        if not config.pid_file.exists():
            return False
        
        try:
            pid = int(config.pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to exit
            for _ in range(30):
                time.sleep(1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    return True
            
            # Force kill if still running
            os.kill(pid, signal.SIGKILL)
            return True
        except Exception:
            return False


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="🏛️ Colosseum Daemon — Continuous Tournament Runner",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    
    parser.add_argument('--daemon', '-d', action='store_true',
                        help='Run as daemon (background)')
    parser.add_argument('--status', '-s', action='store_true',
                        help='Show daemon status')
    parser.add_argument('--stop', action='store_true',
                        help='Stop running daemon')
    
    # Configuration options
    parser.add_argument('--beings', type=int, default=12,
                        help='Number of beings in population (default: 12)')
    parser.add_argument('--lineage', choices=['callie', 'athena', 'mixed'], default='mixed',
                        help='Being lineage (default: mixed)')
    parser.add_argument('--model', default='anthropic/claude-opus-4.5',
                        help='Generation model (default: claude-opus-4.5)')
    parser.add_argument('--judge-model', default='o1',
                        help='Judge model (default: o1)')
    parser.add_argument('--evolve-every', type=int, default=5,
                        help='Evolution frequency (default: 5 rounds)')
    parser.add_argument('--delay', type=int, default=5,
                        help='Delay between rounds in seconds (default: 5)')
    parser.add_argument('--max-rounds', type=int, default=0,
                        help='Maximum rounds per session (0=unlimited)')
    parser.add_argument('--no-hourly-report', action='store_true',
                        help='Disable hourly reports')
    
    args = parser.parse_args()
    
    # Build config
    config = DaemonConfig(
        num_beings=args.beings,
        lineage=args.lineage,
        model=args.model,
        judge_model=args.judge_model,
        evolve_every=args.evolve_every,
        round_delay_seconds=args.delay,
        max_rounds_per_session=args.max_rounds,
        hourly_report=not args.no_hourly_report,
    )
    
    # Handle commands
    if args.status:
        status = ColosseumDaemon.status(config)
        print("\n🏛️  COLOSSEUM DAEMON STATUS")
        print("=" * 40)
        
        if status['running']:
            print(f"✅ Running (PID: {status['pid']})")
        else:
            print("❌ Not running")
        
        if status['state']:
            s = status['state']
            print(f"\n📊 Statistics:")
            print(f"   Started: {s.started_at}")
            print(f"   Total rounds: {s.total_rounds}")
            print(f"   Total evolutions: {s.total_evolutions}")
            print(f"   Beings created: {s.total_beings_created}")
            print(f"   Last hourly report: {s.last_hourly_report}")
        print()
        return
    
    if args.stop:
        print("🛑 Stopping daemon...")
        if ColosseumDaemon.stop(config):
            print("✅ Daemon stopped")
        else:
            print("❌ Daemon not running or failed to stop")
        return
    
    if args.daemon:
        # Fork and run as daemon
        print("🏛️  Starting Colosseum Daemon...")
        
        pid = os.fork()
        if pid > 0:
            print(f"✅ Daemon started (PID: {pid})")
            print(f"   Logs: {config.log_dir}/colosseum_daemon.log")
            print(f"   Stop: python colosseum_daemon.py --stop")
            sys.exit(0)
        
        # Child process
        os.setsid()
        os.chdir(str(Path(__file__).parent))
        
        # Second fork to prevent zombie
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        
        # Redirect stdout/stderr
        sys.stdout = open(config.log_dir / "daemon_stdout.log", 'a')
        sys.stderr = open(config.log_dir / "daemon_stderr.log", 'a')
    
    # Run the daemon
    daemon = ColosseumDaemon(config)
    daemon.run()


if __name__ == "__main__":
    main()
