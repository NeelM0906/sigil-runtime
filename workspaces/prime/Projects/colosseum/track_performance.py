#!/usr/bin/env python3
"""
Being Performance Tracker — Miner 19
Analyzes tournament results, ranks beings by mastery, tracks evolution,
and identifies DNA trait patterns that correlate with success.
"""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
import statistics

DB_PATH = Path(__file__).parent / "colosseum.db"


@dataclass
class BeingStats:
    """Full statistics for a being."""
    id: str
    name: str
    generation: int
    lineage: str
    energy: dict
    traits: list
    strengths: list
    wins: int
    losses: int
    total_rounds: int
    avg_mastery_score: float
    best_score: float
    parent_ids: list
    
    @property
    def win_rate(self) -> float:
        return self.wins / self.total_rounds if self.total_rounds > 0 else 0.0
    
    @property
    def primary_energy(self) -> str:
        if not self.energy:
            return "unknown"
        return max(self.energy.items(), key=lambda x: x[1])[0]


def load_all_beings() -> list[BeingStats]:
    """Load all beings with full statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, generation, lineage, energy_json, traits_json, 
               strengths_json, wins, losses, total_rounds, 
               avg_mastery_score, best_score, parent_ids_json
        FROM beings
        WHERE total_rounds > 0
        ORDER BY avg_mastery_score DESC
    """)
    rows = c.fetchall()
    conn.close()
    
    beings = []
    for row in rows:
        beings.append(BeingStats(
            id=row[0],
            name=row[1],
            generation=row[2],
            lineage=row[3],
            energy=json.loads(row[4]) if row[4] else {},
            traits=json.loads(row[5]) if row[5] else [],
            strengths=json.loads(row[6]) if row[6] else [],
            wins=row[7],
            losses=row[8],
            total_rounds=row[9],
            avg_mastery_score=row[10],
            best_score=row[11],
            parent_ids=json.loads(row[12]) if row[12] else [],
        ))
    return beings


def load_round_details() -> list[dict]:
    """Load all round results with scores breakdown."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.scenario_id, r.being_id, r.mastery_score, r.won, 
               r.scores_json, r.tournament_id, b.generation, b.lineage
        FROM rounds r
        JOIN beings b ON r.being_id = b.id
        ORDER BY r.id
    """)
    rows = c.fetchall()
    conn.close()
    
    rounds = []
    for row in rows:
        scores = json.loads(row[5]) if row[5] else {}
        rounds.append({
            'round_id': row[0],
            'scenario_id': row[1],
            'being_id': row[2],
            'mastery_score': row[3],
            'won': row[4],
            'scores': scores.get('scores', {}),
            'tournament_id': row[6],
            'generation': row[7],
            'lineage': row[8],
        })
    return rounds


def analyze_trait_correlations(beings: list[BeingStats]) -> dict:
    """Analyze which traits correlate with higher mastery scores."""
    trait_scores = defaultdict(list)
    strength_scores = defaultdict(list)
    energy_scores = defaultdict(list)
    
    for being in beings:
        if being.total_rounds < 1:
            continue
            
        score = being.avg_mastery_score
        
        # Track trait performance
        for trait in being.traits:
            trait_scores[trait].append(score)
        
        # Track strength performance
        for strength in being.strengths:
            strength_scores[strength].append(score)
        
        # Track primary energy performance
        energy_scores[being.primary_energy].append(score)
    
    # Calculate averages
    trait_analysis = {
        trait: {
            'avg_score': statistics.mean(scores),
            'count': len(scores),
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0
        }
        for trait, scores in trait_scores.items()
        if len(scores) >= 3
    }
    
    strength_analysis = {
        strength: {
            'avg_score': statistics.mean(scores),
            'count': len(scores),
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0
        }
        for strength, scores in strength_scores.items()
        if len(scores) >= 3
    }
    
    energy_analysis = {
        energy: {
            'avg_score': statistics.mean(scores),
            'count': len(scores),
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0
        }
        for energy, scores in energy_scores.items()
    }
    
    return {
        'traits': trait_analysis,
        'strengths': strength_analysis,
        'energies': energy_analysis,
    }


def analyze_generational_evolution(beings: list[BeingStats]) -> dict:
    """Track performance evolution across generations."""
    gen_stats = defaultdict(lambda: {
        'beings': [],
        'scores': [],
        'win_rates': [],
        'lineages': defaultdict(int),
        'top_traits': defaultdict(int),
    })
    
    for being in beings:
        gen = being.generation
        gen_stats[gen]['beings'].append(being)
        gen_stats[gen]['scores'].append(being.avg_mastery_score)
        gen_stats[gen]['win_rates'].append(being.win_rate)
        gen_stats[gen]['lineages'][being.lineage] += 1
        for trait in being.traits:
            gen_stats[gen]['top_traits'][trait] += 1
    
    evolution = {}
    for gen, stats in sorted(gen_stats.items()):
        evolution[gen] = {
            'count': len(stats['beings']),
            'avg_score': statistics.mean(stats['scores']) if stats['scores'] else 0,
            'max_score': max(stats['scores']) if stats['scores'] else 0,
            'min_score': min(stats['scores']) if stats['scores'] else 0,
            'std_dev': statistics.stdev(stats['scores']) if len(stats['scores']) > 1 else 0,
            'avg_win_rate': statistics.mean(stats['win_rates']) if stats['win_rates'] else 0,
            'lineage_breakdown': dict(stats['lineages']),
            'most_common_traits': sorted(
                stats['top_traits'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5],
        }
    
    return evolution


def analyze_top_performers(beings: list[BeingStats], top_n: int = 10) -> dict:
    """Analyze patterns in top performing beings."""
    top_beings = sorted(beings, key=lambda b: b.avg_mastery_score, reverse=True)[:top_n]
    
    trait_frequency = defaultdict(int)
    strength_frequency = defaultdict(int)
    energy_totals = defaultdict(float)
    lineage_count = defaultdict(int)
    
    for being in top_beings:
        for trait in being.traits:
            trait_frequency[trait] += 1
        for strength in being.strengths:
            strength_frequency[strength] += 1
        for energy, value in being.energy.items():
            energy_totals[energy] += value
        lineage_count[being.lineage] += 1
    
    n = len(top_beings)
    return {
        'top_beings': [
            {
                'name': b.name,
                'id': b.id,
                'generation': b.generation,
                'lineage': b.lineage,
                'avg_mastery': b.avg_mastery_score,
                'best_score': b.best_score,
                'win_rate': b.win_rate,
                'primary_energy': b.primary_energy,
                'traits': b.traits,
                'strengths': b.strengths,
            }
            for b in top_beings
        ],
        'trait_frequency': sorted(trait_frequency.items(), key=lambda x: x[1], reverse=True),
        'strength_frequency': sorted(strength_frequency.items(), key=lambda x: x[1], reverse=True),
        'avg_energy_blend': {k: v/n for k, v in energy_totals.items()} if n > 0 else {},
        'lineage_distribution': dict(lineage_count),
    }


def analyze_lineage_performance(beings: list[BeingStats]) -> dict:
    """Compare performance across lineages."""
    lineage_stats = defaultdict(lambda: {
        'scores': [],
        'win_rates': [],
        'generations': [],
        'best_score': 0,
        'champion': None,
    })
    
    for being in beings:
        lin = being.lineage
        lineage_stats[lin]['scores'].append(being.avg_mastery_score)
        lineage_stats[lin]['win_rates'].append(being.win_rate)
        lineage_stats[lin]['generations'].append(being.generation)
        if being.avg_mastery_score > lineage_stats[lin]['best_score']:
            lineage_stats[lin]['best_score'] = being.avg_mastery_score
            lineage_stats[lin]['champion'] = being.name
    
    return {
        lineage: {
            'count': len(stats['scores']),
            'avg_score': statistics.mean(stats['scores']) if stats['scores'] else 0,
            'std_dev': statistics.stdev(stats['scores']) if len(stats['scores']) > 1 else 0,
            'avg_win_rate': statistics.mean(stats['win_rates']) if stats['win_rates'] else 0,
            'avg_generation': statistics.mean(stats['generations']) if stats['generations'] else 0,
            'best_score': stats['best_score'],
            'champion': stats['champion'],
        }
        for lineage, stats in lineage_stats.items()
    }


def analyze_scoring_dimensions(rounds: list[dict]) -> dict:
    """Analyze which scoring dimensions are most predictive of success."""
    score_keys = [
        'emotional_rapport', 'truth_to_pain', 'hui_creation', 'agreement_formation',
        'scarcity', 'matching_mirroring', 'acknowledgement', 'level_5_listening',
        'love_boundaries', 'energetic_transference', 'reciprocity', 'question_mastery',
        'validation', 'congruence', 'context', 'contrast',
        'fun', 'aspirational', 'goddess', 'zeus',
        'human_likeness', 'contamination_score',
    ]
    
    winning_scores = defaultdict(list)
    losing_scores = defaultdict(list)
    
    for r in rounds:
        scores = r.get('scores', {})
        for key in score_keys:
            if key in scores:
                if r['won']:
                    winning_scores[key].append(scores[key])
                else:
                    losing_scores[key].append(scores[key])
    
    analysis = {}
    for key in score_keys:
        win_avg = statistics.mean(winning_scores[key]) if winning_scores[key] else 0
        lose_avg = statistics.mean(losing_scores[key]) if losing_scores[key] else 0
        analysis[key] = {
            'win_avg': win_avg,
            'lose_avg': lose_avg,
            'delta': win_avg - lose_avg,
            'win_count': len(winning_scores[key]),
            'lose_count': len(losing_scores[key]),
        }
    
    # Sort by delta (biggest difference = most predictive)
    sorted_dims = sorted(analysis.items(), key=lambda x: x[1]['delta'], reverse=True)
    return dict(sorted_dims)


def generate_report(output_path: Path) -> str:
    """Generate comprehensive performance analysis report."""
    print("🔍 Loading data...")
    beings = load_all_beings()
    rounds = load_round_details()
    
    print(f"📊 Analyzing {len(beings)} beings across {len(rounds)} rounds...")
    
    # Run all analyses
    trait_correlations = analyze_trait_correlations(beings)
    generational_evolution = analyze_generational_evolution(beings)
    top_performers = analyze_top_performers(beings, top_n=15)
    lineage_performance = analyze_lineage_performance(beings)
    scoring_dimensions = analyze_scoring_dimensions(rounds)
    
    # Build report
    report = []
    report.append("# Being Performance Analysis 🏛️")
    report.append("")
    report.append(f"*Analyzed {len(beings)} beings across {len(rounds)} tournament rounds*")
    report.append("")
    
    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    
    total_beings = len(beings)
    avg_mastery = statistics.mean([b.avg_mastery_score for b in beings]) if beings else 0
    top_score = max(b.avg_mastery_score for b in beings) if beings else 0
    top_being = top_performers['top_beings'][0] if top_performers['top_beings'] else None
    
    report.append(f"- **Total Active Beings:** {total_beings}")
    report.append(f"- **Average Mastery Score:** {avg_mastery:.3f}")
    report.append(f"- **Top Score:** {top_score:.3f}")
    if top_being:
        report.append(f"- **Champion:** {top_being['name']} (Gen {top_being['generation']}, {top_being['lineage']})")
    report.append("")
    
    # Top Performers
    report.append("## 🏆 Top 15 Performers")
    report.append("")
    report.append("| Rank | Name | Gen | Lineage | Avg Mastery | Best | Win Rate | Primary Energy |")
    report.append("|------|------|-----|---------|-------------|------|----------|----------------|")
    
    for i, being in enumerate(top_performers['top_beings'], 1):
        report.append(
            f"| {i} | {being['name']} | {being['generation']} | {being['lineage']} | "
            f"{being['avg_mastery']:.3f} | {being['best_score']:.2f} | "
            f"{being['win_rate']:.0%} | {being['primary_energy']} |"
        )
    report.append("")
    
    # Lineage Comparison
    report.append("## 📊 Lineage Performance Comparison")
    report.append("")
    report.append("| Lineage | Count | Avg Score | Std Dev | Win Rate | Champion |")
    report.append("|---------|-------|-----------|---------|----------|----------|")
    
    for lineage, stats in sorted(lineage_performance.items(), key=lambda x: x[1]['avg_score'], reverse=True):
        report.append(
            f"| {lineage} | {stats['count']} | {stats['avg_score']:.3f} | "
            f"{stats['std_dev']:.3f} | {stats['avg_win_rate']:.0%} | {stats['champion']} |"
        )
    report.append("")
    
    # Key Finding
    best_lineage = max(lineage_performance.items(), key=lambda x: x[1]['avg_score'])[0]
    report.append(f"**Key Finding:** The `{best_lineage}` lineage shows the highest average mastery scores.")
    report.append("")
    
    # Generational Evolution
    report.append("## 🧬 Generational Evolution")
    report.append("")
    report.append("| Generation | Beings | Avg Score | Max | Min | Std Dev | Avg Win Rate |")
    report.append("|------------|--------|-----------|-----|-----|---------|--------------|")
    
    for gen, stats in sorted(generational_evolution.items()):
        report.append(
            f"| Gen {gen} | {stats['count']} | {stats['avg_score']:.3f} | "
            f"{stats['max_score']:.2f} | {stats['min_score']:.2f} | "
            f"{stats['std_dev']:.3f} | {stats['avg_win_rate']:.0%} |"
        )
    report.append("")
    
    # Evolution insight
    if len(generational_evolution) > 1:
        gen_scores = [(g, s['avg_score']) for g, s in generational_evolution.items()]
        if gen_scores[1][1] > gen_scores[0][1]:
            report.append("**Evolution Insight:** Gen 1+ shows improvement over Gen 0, suggesting evolution is working!")
        else:
            report.append("**Evolution Insight:** Gen 0 still outperforms evolved generations—may need tuning.")
    report.append("")
    
    # Trait Correlations
    report.append("## 🎯 DNA Trait Correlations with Success")
    report.append("")
    
    # Top traits
    report.append("### Personality Traits (ranked by avg mastery)")
    report.append("")
    sorted_traits = sorted(
        trait_correlations['traits'].items(), 
        key=lambda x: x[1]['avg_score'], 
        reverse=True
    )
    
    report.append("| Trait | Avg Score | Count | Std Dev |")
    report.append("|-------|-----------|-------|---------|")
    for trait, stats in sorted_traits[:10]:
        report.append(f"| {trait} | {stats['avg_score']:.3f} | {stats['count']} | {stats['std_dev']:.3f} |")
    report.append("")
    
    if sorted_traits:
        best_trait = sorted_traits[0][0]
        worst_trait = sorted_traits[-1][0]
        report.append(f"**Best Trait:** `{best_trait}` correlates with highest mastery scores")
        report.append(f"**Weakest Trait:** `{worst_trait}` correlates with lowest mastery scores")
    report.append("")
    
    # Top strengths
    report.append("### Strengths (ranked by avg mastery)")
    report.append("")
    sorted_strengths = sorted(
        trait_correlations['strengths'].items(), 
        key=lambda x: x[1]['avg_score'], 
        reverse=True
    )
    
    report.append("| Strength | Avg Score | Count |")
    report.append("|----------|-----------|-------|")
    for strength, stats in sorted_strengths[:10]:
        report.append(f"| {strength} | {stats['avg_score']:.3f} | {stats['count']} |")
    report.append("")
    
    # Energy blend analysis
    report.append("### Primary Energy Correlation")
    report.append("")
    report.append("| Primary Energy | Avg Score | Count |")
    report.append("|----------------|-----------|-------|")
    
    sorted_energies = sorted(
        trait_correlations['energies'].items(), 
        key=lambda x: x[1]['avg_score'], 
        reverse=True
    )
    for energy, stats in sorted_energies:
        report.append(f"| {energy.title()} | {stats['avg_score']:.3f} | {stats['count']} |")
    report.append("")
    
    # Top performer energy blend
    report.append("### Top 15 Performers' Average Energy Blend")
    report.append("")
    avg_blend = top_performers['avg_energy_blend']
    if avg_blend:
        report.append(f"- **Fun:** {avg_blend.get('fun', 0):.1%}")
        report.append(f"- **Aspirational:** {avg_blend.get('aspirational', 0):.1%}")
        report.append(f"- **Goddess:** {avg_blend.get('goddess', 0):.1%}")
        report.append(f"- **Zeus:** {avg_blend.get('zeus', 0):.1%}")
    report.append("")
    
    # Scoring Dimensions Analysis
    report.append("## 📈 Most Predictive Scoring Dimensions")
    report.append("")
    report.append("*Dimensions sorted by delta (winner avg - loser avg)*")
    report.append("")
    report.append("| Dimension | Winner Avg | Loser Avg | Delta |")
    report.append("|-----------|------------|-----------|-------|")
    
    for dim, stats in list(scoring_dimensions.items())[:12]:
        report.append(
            f"| {dim.replace('_', ' ').title()} | {stats['win_avg']:.2f} | "
            f"{stats['lose_avg']:.2f} | +{stats['delta']:.2f} |"
        )
    report.append("")
    
    if scoring_dimensions:
        top_dim = list(scoring_dimensions.keys())[0]
        report.append(f"**Key Insight:** `{top_dim.replace('_', ' ').title()}` is the most predictive dimension—winners score significantly higher here.")
    report.append("")
    
    # Patterns in Top Performers
    report.append("## 🔮 Patterns in Top Performers")
    report.append("")
    
    # Most common traits among winners
    report.append("### Most Common Traits Among Top 15")
    report.append("")
    for trait, count in top_performers['trait_frequency'][:7]:
        pct = count / len(top_performers['top_beings']) * 100
        report.append(f"- **{trait}**: {count} beings ({pct:.0f}%)")
    report.append("")
    
    # Most common strengths
    report.append("### Most Common Strengths Among Top 15")
    report.append("")
    for strength, count in top_performers['strength_frequency'][:7]:
        pct = count / len(top_performers['top_beings']) * 100
        report.append(f"- **{strength}**: {count} beings ({pct:.0f}%)")
    report.append("")
    
    # Recommendations
    report.append("## 💡 Recommendations for Evolution")
    report.append("")
    
    # Build recommendations based on analysis
    recommendations = []
    
    if sorted_traits:
        recommendations.append(f"1. **Prioritize `{sorted_traits[0][0]}` trait** - Strongly correlated with mastery")
    
    if sorted_strengths:
        recommendations.append(f"2. **Favor `{sorted_strengths[0][0]}` strength** - Top performers excel here")
    
    if sorted_energies:
        best_energy = sorted_energies[0][0]
        recommendations.append(f"3. **Tune toward `{best_energy.title()}` energy** - Highest performing primary energy")
    
    if scoring_dimensions:
        top_dims = list(scoring_dimensions.keys())[:3]
        recommendations.append(f"4. **Focus training on:** {', '.join(d.replace('_', ' ').title() for d in top_dims)}")
    
    best_lineage_data = lineage_performance.get(best_lineage, {})
    if best_lineage_data:
        recommendations.append(f"5. **Consider `{best_lineage}` base DNA** - Shows {best_lineage_data.get('avg_score', 0):.2f} avg mastery")
    
    for rec in recommendations:
        report.append(rec)
    report.append("")
    
    # Footer
    report.append("---")
    report.append("*Generated by Being Performance Tracker — Miner 19*")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = "\n".join(report)
    output_path.write_text(report_text)
    
    print(f"✅ Report saved to: {output_path}")
    return report_text


if __name__ == "__main__":
    output_file = Path("~/.openclaw/workspace/memory/being-performance-analysis.md")
    report = generate_report(output_file)
    
    # Print summary to console
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nReport location: {output_file}")
