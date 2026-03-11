#!/usr/bin/env python3
"""
🏛️ The Colosseum — CLI Tournament Runner
Where ACT-I beings evolve through influence mastery.

Usage:
    python run_tournament.py                    # Default blitz (8 beings, 20 rounds)
    python run_tournament.py --mode deep        # Deep (gpt-4o, 10 rounds)
    python run_tournament.py --mode marathon    # Marathon (16 beings, 100 rounds)
    python run_tournament.py --beings 16 --rounds 50 --lineage mixed
"""

import argparse
import os
import sys
from pathlib import Path

from bomba_sr.openclaw.script_support import load_portable_env

load_portable_env(Path(__file__))

from colosseum.tournament import TournamentConfig, run_tournament
from colosseum.scenarios import Difficulty, Category


def main():
    parser = argparse.ArgumentParser(
        description="🏛️ ACT-I Colosseum — Where Beings Evolve",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--mode", choices=["blitz", "deep", "marathon"], default="blitz",
                        help="Tournament mode (default: blitz)")
    parser.add_argument("--beings", type=int, default=None,
                        help="Number of beings (default: 8 for blitz, 16 for marathon)")
    parser.add_argument("--rounds", type=int, default=None,
                        help="Number of rounds (default: 20 for blitz, 100 for marathon)")
    parser.add_argument("--lineage", choices=["callie", "athena", "mixed"], default="callie",
                        help="Being lineage (default: callie)")
    parser.add_argument("--difficulty", choices=["bronze", "silver", "gold", "platinum"], default=None,
                        help="Lock difficulty level")
    parser.add_argument("--category", choices=[c.value for c in Category], default=None,
                        help="Lock scenario category")
    parser.add_argument("--model", default=None, help="Override generation model")
    parser.add_argument("--judge-model", default=None, help="Override judge model")
    parser.add_argument("--evolve-every", type=int, default=None, help="Evolution frequency")

    args = parser.parse_args()

    # Build config
    if args.mode == "deep":
        config = TournamentConfig.deep(args.beings or 8, args.rounds or 10)
    elif args.mode == "marathon":
        config = TournamentConfig.marathon(args.beings or 16, args.rounds or 100)
    else:
        config = TournamentConfig.blitz(args.beings or 8, args.rounds or 20)

    config.lineage = args.lineage
    if args.difficulty:
        config.difficulty = Difficulty(args.difficulty)
    if args.category:
        config.category = Category(args.category)
    if args.model:
        config.model = args.model
    if args.judge_model:
        config.judge_model = args.judge_model
    if args.evolve_every:
        config.evolve_every = args.evolve_every

    # Run it
    print("\n🔥 THE COLOSSEUM OPENS 🔥\n")
    state = run_tournament(config)
    print(f"\n✅ Tournament {state.id} complete. {state.total_rounds_completed} rounds. "
          f"{len(state.beings)} beings evolved.\n")


if __name__ == "__main__":
    main()
