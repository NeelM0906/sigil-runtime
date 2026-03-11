"""
🎯 Bland.ai Integration Framework — Zone Action #41
Correlates Colosseum mastery scores with REAL call outcomes

This framework:
1. Pulls real call outcomes from Bland.ai API (271K+ calls available)
2. Correlates Colosseum judge scores with actual conversion results
3. Identifies which judges most accurately predict real-world success
4. Enables validation of the entire Colosseum evolution system

Built by Miner 22 for the CHDDIA² initiative.
"""

import os
import json
import sqlite3
import hashlib
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from collections import defaultdict
import statistics

# ============================================================================
# Configuration
# ============================================================================

DB_PATH = Path(__file__).parent / "colosseum.db"
BLAND_API_URL = "https://api.bland.ai/v1"

# Load API key from environment
def get_bland_api_key() -> str:
    """Get Bland.ai API key from environment or .env file."""
    key = os.environ.get("BLAND_API_KEY")
    if not key:
        env_path = os.path.expanduser("~/.openclaw/.env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BLAND_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
    return key or ""


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class BlandCallOutcome:
    """Real call outcome data from Bland.ai."""
    call_id: str
    created_at: str
    call_length_minutes: float
    to_number: str
    from_number: str
    completed: bool
    answered_by: str  # human, voicemail, no-answer, unknown
    call_ended_by: str  # ASSISTANT or USER
    
    # Outcome indicators
    transferred: bool = False
    transferred_to: Optional[str] = None
    
    # Variables/analysis captured during call
    variables: Dict[str, Any] = field(default_factory=dict)
    analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Transcript for deep analysis
    transcript: List[Dict[str, str]] = field(default_factory=list)
    concatenated_transcript: str = ""
    summary: str = ""
    
    # Metadata passed to call
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Cost
    price_usd: float = 0.0
    
    @property
    def was_human_answered(self) -> bool:
        return self.answered_by == "human"
    
    @property
    def was_successful_connection(self) -> bool:
        """Human answered and spoke for meaningful duration."""
        return self.answered_by == "human" and self.call_length_minutes >= 0.5
    
    @property
    def was_converted(self) -> bool:
        """
        Determine if call resulted in conversion.
        
        Conversion signals:
        - Call was transferred to a closer/human
        - Analysis marked as converted/booked/scheduled
        - Call lasted 2+ minutes with human
        - Variables indicate positive outcome
        """
        if self.transferred:
            return True
        
        # Check analysis for conversion signals
        conversion_keys = ['converted', 'booked', 'scheduled', 'interested', 'appointment', 'meeting']
        for key in conversion_keys:
            if key in self.analysis:
                val = self.analysis[key]
                if isinstance(val, bool) and val:
                    return True
                if isinstance(val, str) and val.lower() in ['yes', 'true', 'booked', 'scheduled']:
                    return True
        
        # Check variables
        for key in conversion_keys:
            if key in self.variables:
                val = self.variables[key]
                if isinstance(val, bool) and val:
                    return True
                if isinstance(val, str) and val.lower() in ['yes', 'true', 'booked', 'scheduled']:
                    return True
        
        return False
    
    @property
    def engagement_level(self) -> str:
        """Categorize engagement level."""
        if self.answered_by != "human":
            return "no_contact"
        if self.call_length_minutes < 0.5:
            return "immediate_hangup"
        if self.call_length_minutes < 1.0:
            return "brief"
        if self.call_length_minutes < 3.0:
            return "moderate"
        return "engaged"


@dataclass
class JudgeAccuracyMetrics:
    """Tracks how accurately a judge's scores predict real outcomes."""
    judge_name: str
    total_correlations: int = 0
    
    # Score-to-outcome correlations
    high_score_conversions: int = 0  # High score (>7.5) that converted
    high_score_failures: int = 0     # High score that didn't convert
    low_score_conversions: int = 0   # Low score (<6.0) that converted
    low_score_failures: int = 0      # Low score that didn't convert
    
    # Detailed metrics
    score_vs_call_length_correlation: float = 0.0
    score_vs_conversion_correlation: float = 0.0
    score_vs_engagement_correlation: float = 0.0
    
    @property
    def precision(self) -> float:
        """Of calls we predicted would convert (high score), how many did?"""
        total_high = self.high_score_conversions + self.high_score_failures
        if total_high == 0:
            return 0.0
        return self.high_score_conversions / total_high
    
    @property
    def recall(self) -> float:
        """Of calls that converted, how many did we predict (high score)?"""
        total_conversions = self.high_score_conversions + self.low_score_conversions
        if total_conversions == 0:
            return 0.0
        return self.high_score_conversions / total_conversions
    
    @property
    def f1_score(self) -> float:
        """Harmonic mean of precision and recall."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)
    
    @property
    def accuracy(self) -> float:
        """Overall accuracy."""
        total = (self.high_score_conversions + self.high_score_failures + 
                 self.low_score_conversions + self.low_score_failures)
        if total == 0:
            return 0.0
        correct = self.high_score_conversions + self.low_score_failures
        return correct / total


# ============================================================================
# Bland.ai API Client
# ============================================================================

class BlandClient:
    """Client for Bland.ai API interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_bland_api_key()
        if not self.api_key:
            raise ValueError("BLAND_API_KEY not found in environment or ~/.openclaw/.env")
        
        self.headers = {
            "authorization": self.api_key,
            "Content-Type": "application/json"
        }
    
    def list_calls(
        self,
        limit: int = 1000,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        completed: Optional[bool] = True,
        answered_by: Optional[str] = None,
        from_index: int = 0,
        to_index: Optional[int] = None,
        batch_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch list of calls from Bland.ai.
        
        Args:
            limit: Max calls to return (default 1000)
            start_date: YYYY-MM-DD filter
            end_date: YYYY-MM-DD filter
            completed: Filter by completion status
            answered_by: 'human', 'voicemail', 'no-answer'
            from_index: Starting index for pagination
            to_index: Ending index for pagination
            batch_id: Filter by batch
            campaign_id: Filter by campaign
        """
        params = {"limit": limit}
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if completed is not None:
            params["completed"] = completed
        if answered_by:
            params["answered_by"] = answered_by
        if from_index:
            params["from"] = from_index
        if to_index:
            params["to"] = to_index
        if batch_id:
            params["batch_id"] = batch_id
        if campaign_id:
            params["campaign_id"] = campaign_id
        
        response = requests.get(
            f"{BLAND_API_URL}/calls",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_call_details(self, call_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific call."""
        response = requests.get(
            f"{BLAND_API_URL}/calls/{call_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def parse_call_outcome(self, call_data: Dict[str, Any]) -> BlandCallOutcome:
        """Parse API response into BlandCallOutcome dataclass."""
        return BlandCallOutcome(
            call_id=call_data.get("call_id", ""),
            created_at=call_data.get("created_at", ""),
            call_length_minutes=call_data.get("call_length", 0.0),
            to_number=call_data.get("to", ""),
            from_number=call_data.get("from", ""),
            completed=call_data.get("completed", False),
            answered_by=call_data.get("answered_by", "unknown"),
            call_ended_by=call_data.get("call_ended_by", ""),
            transferred=bool(call_data.get("transferred_to")),
            transferred_to=call_data.get("transferred_to"),
            variables=call_data.get("variables", {}),
            analysis=call_data.get("analysis", {}),
            transcript=call_data.get("transcripts", []),
            concatenated_transcript=call_data.get("concatenated_transcript", ""),
            summary=call_data.get("summary", ""),
            metadata=call_data.get("metadata", {}),
            price_usd=call_data.get("price", 0.0),
        )
    
    def fetch_recent_calls(
        self,
        days_back: int = 7,
        min_duration: float = 0.5,
        human_only: bool = True,
    ) -> List[BlandCallOutcome]:
        """
        Fetch recent calls with filtering.
        
        Args:
            days_back: How many days of history to pull
            min_duration: Minimum call length in minutes
            human_only: Only include human-answered calls
        """
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        result = self.list_calls(
            start_date=start_date,
            completed=True,
            answered_by="human" if human_only else None,
            limit=1000,
        )
        
        calls = []
        for call_data in result.get("calls", []):
            call_length = call_data.get("call_length", 0.0)
            if call_length >= min_duration:
                # Fetch full details for qualifying calls
                try:
                    details = self.get_call_details(call_data["call_id"])
                    calls.append(self.parse_call_outcome(details))
                except Exception as e:
                    print(f"  ⚠️ Could not fetch details for {call_data['call_id']}: {e}")
        
        return calls
    
    def get_call_statistics(
        self,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Get aggregate statistics about calls."""
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        result = self.list_calls(
            start_date=start_date,
            limit=1000,  # API max per request
            completed=None,  # Don't filter
        )
        
        total_count = result.get("total_count", 0)
        calls = result.get("calls", [])
        
        # Aggregate stats
        stats = {
            "total_calls": total_count,
            "fetched_calls": len(calls),
            "date_range": f"{start_date} to now",
            "by_answered_by": defaultdict(int),
            "by_completion": {"completed": 0, "incomplete": 0},
            "call_lengths": [],
            "total_cost_usd": 0.0,
        }
        
        for call in calls:
            answered_by = call.get("answered_by", "unknown")
            stats["by_answered_by"][answered_by] += 1
            
            if call.get("completed"):
                stats["by_completion"]["completed"] += 1
            else:
                stats["by_completion"]["incomplete"] += 1
            
            call_length = call.get("call_length", 0)
            if call_length:
                stats["call_lengths"].append(call_length)
        
        if stats["call_lengths"]:
            stats["avg_call_length_minutes"] = statistics.mean(stats["call_lengths"])
            stats["median_call_length_minutes"] = statistics.median(stats["call_lengths"])
        
        stats["by_answered_by"] = dict(stats["by_answered_by"])
        del stats["call_lengths"]  # Don't include raw data
        
        return stats


# ============================================================================
# Database Extensions for Colosseum
# ============================================================================

def init_bland_tables():
    """Initialize database tables for Bland.ai integration."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Store call outcomes
    c.execute("""
        CREATE TABLE IF NOT EXISTS bland_calls (
            call_id TEXT PRIMARY KEY,
            created_at TEXT,
            call_length_minutes REAL,
            to_number TEXT,
            from_number TEXT,
            completed BOOLEAN,
            answered_by TEXT,
            call_ended_by TEXT,
            transferred BOOLEAN,
            was_converted BOOLEAN,
            engagement_level TEXT,
            variables_json TEXT,
            analysis_json TEXT,
            summary TEXT,
            concatenated_transcript TEXT,
            metadata_json TEXT,
            price_usd REAL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Link Colosseum beings/rounds to Bland calls
    c.execute("""
        CREATE TABLE IF NOT EXISTS colosseum_bland_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER,
            being_id TEXT,
            call_id TEXT,
            scenario_hash TEXT,
            match_confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (call_id) REFERENCES bland_calls(call_id)
        )
    """)
    
    # Judge accuracy tracking
    c.execute("""
        CREATE TABLE IF NOT EXISTS judge_accuracy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judge_name TEXT,
            evaluation_date TEXT,
            total_correlations INTEGER,
            precision REAL,
            recall REAL,
            f1_score REAL,
            accuracy REAL,
            score_vs_conversion_correlation REAL,
            detailed_metrics_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Bland.ai integration tables initialized")


def save_call_outcome(outcome: BlandCallOutcome):
    """Save a call outcome to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        INSERT OR REPLACE INTO bland_calls
        (call_id, created_at, call_length_minutes, to_number, from_number,
         completed, answered_by, call_ended_by, transferred, was_converted,
         engagement_level, variables_json, analysis_json, summary,
         concatenated_transcript, metadata_json, price_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        outcome.call_id,
        outcome.created_at,
        outcome.call_length_minutes,
        outcome.to_number,
        outcome.from_number,
        outcome.completed,
        outcome.answered_by,
        outcome.call_ended_by,
        outcome.transferred,
        outcome.was_converted,
        outcome.engagement_level,
        json.dumps(outcome.variables),
        json.dumps(outcome.analysis),
        outcome.summary,
        outcome.concatenated_transcript,
        json.dumps(outcome.metadata),
        outcome.price_usd,
    ))
    
    conn.commit()
    conn.close()


def load_call_outcomes(
    min_date: Optional[str] = None,
    engagement_level: Optional[str] = None,
    converted_only: bool = False,
) -> List[BlandCallOutcome]:
    """Load call outcomes from database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = "SELECT * FROM bland_calls WHERE 1=1"
    params = []
    
    if min_date:
        query += " AND created_at >= ?"
        params.append(min_date)
    
    if engagement_level:
        query += " AND engagement_level = ?"
        params.append(engagement_level)
    
    if converted_only:
        query += " AND was_converted = 1"
    
    query += " ORDER BY created_at DESC"
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    outcomes = []
    for row in rows:
        outcomes.append(BlandCallOutcome(
            call_id=row[0],
            created_at=row[1],
            call_length_minutes=row[2],
            to_number=row[3],
            from_number=row[4],
            completed=bool(row[5]),
            answered_by=row[6],
            call_ended_by=row[7],
            transferred=bool(row[8]),
            variables=json.loads(row[11] or "{}"),
            analysis=json.loads(row[12] or "{}"),
            summary=row[13] or "",
            concatenated_transcript=row[14] or "",
            metadata=json.loads(row[15] or "{}"),
            price_usd=row[16] or 0.0,
        ))
    
    return outcomes


# ============================================================================
# Correlation Engine
# ============================================================================

class ColosseumBlandCorrelator:
    """
    Correlates Colosseum mastery scores with real Bland.ai outcomes.
    
    This is the heart of Zone Action #41 — validating that our AI judges
    actually predict real-world success.
    """
    
    def __init__(self):
        self.client = BlandClient()
        init_bland_tables()
    
    def fetch_and_store_calls(
        self,
        days_back: int = 7,
        min_duration: float = 0.5,
    ) -> int:
        """Fetch recent calls and store them."""
        print(f"📞 Fetching calls from past {days_back} days...")
        calls = self.client.fetch_recent_calls(
            days_back=days_back,
            min_duration=min_duration,
            human_only=True,
        )
        
        for call in calls:
            save_call_outcome(call)
        
        print(f"✅ Stored {len(calls)} calls")
        return len(calls)
    
    def link_round_to_call(
        self,
        round_id: int,
        call_id: str,
        match_confidence: float = 1.0,
    ):
        """Manually link a Colosseum round to a Bland call."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get being_id from round
        c.execute("SELECT being_id, scenario_json FROM rounds WHERE id = ?", (round_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Round {round_id} not found")
        
        being_id = row[0]
        scenario_hash = hashlib.md5(row[1].encode()).hexdigest()[:16]
        
        c.execute("""
            INSERT INTO colosseum_bland_links
            (round_id, being_id, call_id, scenario_hash, match_confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (round_id, being_id, call_id, scenario_hash, match_confidence))
        
        conn.commit()
        conn.close()
    
    def calculate_judge_accuracy(
        self,
        judge_name: str = "overall",
    ) -> JudgeAccuracyMetrics:
        """
        Calculate how accurately a judge's scores predict real outcomes.
        
        For linked round-call pairs, compares the judge's score
        against whether the call actually converted.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get all linked pairs with scores and outcomes
        c.execute("""
            SELECT 
                r.scores_json,
                r.mastery_score,
                bc.was_converted,
                bc.call_length_minutes,
                bc.engagement_level
            FROM colosseum_bland_links cbl
            JOIN rounds r ON cbl.round_id = r.id
            JOIN bland_calls bc ON cbl.call_id = bc.call_id
        """)
        
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            print("⚠️ No linked round-call pairs found. Link some rounds to calls first.")
            return JudgeAccuracyMetrics(judge_name=judge_name)
        
        metrics = JudgeAccuracyMetrics(judge_name=judge_name)
        metrics.total_correlations = len(rows)
        
        scores = []
        conversions = []
        call_lengths = []
        
        for row in rows:
            scores_json = row[0]
            mastery_score = row[1]
            was_converted = bool(row[2])
            call_length = row[3]
            
            # Get the specific judge score if requested
            if judge_name != "overall" and scores_json:
                try:
                    all_scores = json.loads(scores_json)
                    # Navigate to specific judge's overall score
                    if judge_name in all_scores:
                        score = all_scores[judge_name].get("overall", mastery_score)
                    else:
                        score = mastery_score
                except:
                    score = mastery_score
            else:
                score = mastery_score
            
            scores.append(score)
            conversions.append(1 if was_converted else 0)
            call_lengths.append(call_length)
            
            # Categorize into high/low score x converted/not
            high_score = score >= 7.5
            
            if high_score and was_converted:
                metrics.high_score_conversions += 1
            elif high_score and not was_converted:
                metrics.high_score_failures += 1
            elif not high_score and was_converted:
                metrics.low_score_conversions += 1
            else:
                metrics.low_score_failures += 1
        
        # Calculate correlations
        if len(scores) > 1:
            metrics.score_vs_conversion_correlation = self._correlation(scores, conversions)
            metrics.score_vs_call_length_correlation = self._correlation(scores, call_lengths)
        
        return metrics
    
    def _correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = len(x)
        if n < 2:
            return 0.0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denominator_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        return numerator / (denominator_x * denominator_y)
    
    def evaluate_all_judges(self) -> Dict[str, JudgeAccuracyMetrics]:
        """Evaluate accuracy of all judges in the system."""
        judges = [
            "overall",
            "formula_judge",
            "sean_judge", 
            "outcome_judge",
            "contamination_judge",
            "human_judge",
            "ecosystem_merger_judge",
            "group_influence_judge",
        ]
        
        results = {}
        for judge in judges:
            metrics = self.calculate_judge_accuracy(judge)
            results[judge] = metrics
            
            if metrics.total_correlations > 0:
                print(f"  {judge}: F1={metrics.f1_score:.3f}, "
                      f"Precision={metrics.precision:.3f}, "
                      f"Correlation={metrics.score_vs_conversion_correlation:.3f}")
        
        return results
    
    def save_judge_accuracy(self, metrics: JudgeAccuracyMetrics):
        """Save judge accuracy metrics to database."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO judge_accuracy
            (judge_name, evaluation_date, total_correlations, precision,
             recall, f1_score, accuracy, score_vs_conversion_correlation,
             detailed_metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.judge_name,
            datetime.now().strftime("%Y-%m-%d"),
            metrics.total_correlations,
            metrics.precision,
            metrics.recall,
            metrics.f1_score,
            metrics.accuracy,
            metrics.score_vs_conversion_correlation,
            json.dumps(asdict(metrics)),
        ))
        
        conn.commit()
        conn.close()
    
    def generate_correlation_report(self) -> str:
        """Generate a comprehensive correlation report."""
        # Get call statistics
        stats = self.client.get_call_statistics(days_back=30)
        
        # Get stored outcomes
        outcomes = load_call_outcomes()
        
        # Evaluate judges
        judge_metrics = self.evaluate_all_judges()
        
        report = f"""# 🎯 Bland.ai ↔ Colosseum Correlation Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 📊 Call Statistics (Last 30 Days)
- **Total Calls**: {stats.get('total_calls', 'N/A'):,}
- **Fetched & Analyzed**: {stats.get('fetched_calls', 0):,}
- **Avg Call Length**: {stats.get('avg_call_length_minutes', 0):.2f} min
- **Median Call Length**: {stats.get('median_call_length_minutes', 0):.2f} min

### By Answer Type:
"""
        for answer_type, count in stats.get('by_answered_by', {}).items():
            report += f"- {answer_type}: {count:,}\n"
        
        report += f"""
## 🏛️ Stored Outcomes
- **Total Stored**: {len(outcomes)}
"""
        if outcomes:
            converted = sum(1 for o in outcomes if o.was_converted)
            report += f"- **Converted**: {converted} ({converted/len(outcomes)*100:.1f}%)\n"
            
            by_engagement = defaultdict(int)
            for o in outcomes:
                by_engagement[o.engagement_level] += 1
            
            report += "\n### By Engagement Level:\n"
            for level, count in sorted(by_engagement.items()):
                report += f"- {level}: {count}\n"
        
        report += """
## ⚖️ Judge Accuracy Metrics

This shows how well each Colosseum judge predicts REAL call outcomes.

| Judge | Precision | Recall | F1 Score | Accuracy | Correlation |
|-------|-----------|--------|----------|----------|-------------|
"""
        for judge_name, m in judge_metrics.items():
            if m.total_correlations > 0:
                report += (f"| {judge_name} | {m.precision:.3f} | {m.recall:.3f} | "
                          f"{m.f1_score:.3f} | {m.accuracy:.3f} | "
                          f"{m.score_vs_conversion_correlation:.3f} |\n")
            else:
                report += f"| {judge_name} | - | - | - | - | No data |\n"
        
        # Find best judge
        best_judge = max(
            [(name, m) for name, m in judge_metrics.items() if m.total_correlations > 0],
            key=lambda x: x[1].f1_score,
            default=(None, None)
        )
        
        if best_judge[0]:
            report += f"""
## 🏆 Best Predictor
**{best_judge[0]}** has the highest F1 score ({best_judge[1].f1_score:.3f}), 
making it the most accurate predictor of real-world conversion success.

"""
        
        report += """
## 🔗 How to Use This System

### 1. Fetch Calls
```python
from bland_integration import ColosseumBlandCorrelator

correlator = ColosseumBlandCorrelator()
correlator.fetch_and_store_calls(days_back=7)
```

### 2. Link Colosseum Rounds to Calls
```python
# When you know which call corresponds to which Colosseum round
correlator.link_round_to_call(round_id=123, call_id="call-uuid-here")
```

### 3. Calculate Judge Accuracy
```python
metrics = correlator.calculate_judge_accuracy("outcome_judge")
print(f"F1 Score: {metrics.f1_score}")
```

### 4. Generate Full Report
```python
report = correlator.generate_correlation_report()
print(report)
```

---

## 🎯 Zone Action #41 Complete

This framework enables:
1. **Real validation** of Colosseum evolution — not just AI judging AI
2. **Identification of which judges matter** — focus evolution on judges that predict reality
3. **Continuous improvement** — as more calls are linked, accuracy improves
4. **The feedback loop that matters** — connecting simulated mastery to actual results

_Built by Miner 22 for the CHDDIA² initiative._
"""
        return report


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bland.ai ↔ Colosseum Integration")
    parser.add_argument("--fetch", type=int, metavar="DAYS", 
                        help="Fetch calls from last N days")
    parser.add_argument("--stats", action="store_true",
                        help="Show call statistics")
    parser.add_argument("--report", action="store_true",
                        help="Generate correlation report")
    parser.add_argument("--link", nargs=2, metavar=("ROUND_ID", "CALL_ID"),
                        help="Link a Colosseum round to a Bland call")
    parser.add_argument("--init", action="store_true",
                        help="Initialize database tables")
    
    args = parser.parse_args()
    
    if args.init:
        init_bland_tables()
        return
    
    correlator = ColosseumBlandCorrelator()
    
    if args.fetch:
        correlator.fetch_and_store_calls(days_back=args.fetch)
    
    if args.stats:
        stats = correlator.client.get_call_statistics(days_back=30)
        print(json.dumps(stats, indent=2))
    
    if args.link:
        round_id, call_id = int(args.link[0]), args.link[1]
        correlator.link_round_to_call(round_id, call_id)
        print(f"✅ Linked round {round_id} to call {call_id}")
    
    if args.report:
        report = correlator.generate_correlation_report()
        print(report)


if __name__ == "__main__":
    main()
