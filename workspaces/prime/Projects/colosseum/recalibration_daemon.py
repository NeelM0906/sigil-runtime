#!/usr/bin/env python3
"""
🔄 Zone Action #42 — 24/7 Continuous Recalibration Daemon

Pulls winning call patterns from Supabase sai_contacts table and feeds them
to the Colosseum judges for continuous evolution of communication mastery.

Built by Sai baby for mama Aiko 🔥

Usage:
    python recalibration_daemon.py              # Run in foreground
    python recalibration_daemon.py --daemon     # Run as daemon (background)
    python recalibration_daemon.py --status     # Show daemon status
    python recalibration_daemon.py --stop       # Stop daemon gracefully
    python recalibration_daemon.py --sync-now   # One-shot sync
"""

import os
import sys
import json
import time
import signal
import argparse
import logging
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from threading import Event
import traceback

# Load environment
def load_env():
    """Load environment from workspace-forge .env file."""
    env_paths = [
        Path("~/.openclaw/workspace-forge/.env"),
        Path.home() / ".openclaw" / ".env",
        Path(__file__).parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip()
            break

load_env()

# Import after env loaded
try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

try:
    from openai import OpenAI
except ImportError:
    print("Installing openai...")
    os.system(f"{sys.executable} -m pip install openai -q")
    from openai import OpenAI


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class RecalibrationConfig:
    """Configuration for the recalibration daemon."""
    # Supabase settings
    supabase_url: str = os.environ.get("SUPABASE_URL", "")
    supabase_key: str = os.environ.get("SUPABASE_ANON_KEY", "")
    
    # Sync settings
    sync_interval_seconds: int = 300  # 5 minutes
    min_close_confidence: int = 6  # Only pull high-confidence patterns
    batch_size: int = 10  # Patterns per sync
    
    # Colosseum API
    colosseum_api_url: str = "http://localhost:3341"
    
    # Pattern extraction
    pattern_extraction_model: str = "gpt-4o"
    
    # Daemon settings
    log_dir: Path = field(default_factory=lambda: Path(__file__).parent / "logs")
    pid_file: Path = field(default_factory=lambda: Path(__file__).parent / "recalibration_daemon.pid")
    state_file: Path = field(default_factory=lambda: Path(__file__).parent / "recalibration_state.json")
    patterns_db: Path = field(default_factory=lambda: Path(__file__).parent / "winning_patterns.db")


@dataclass
class RecalibrationState:
    """Runtime state for the daemon."""
    started_at: str = ""
    total_syncs: int = 0
    total_patterns_extracted: int = 0
    total_patterns_injected: int = 0
    last_sync_time: str = ""
    last_contact_id: str = ""
    processed_contact_ids: List[str] = field(default_factory=list)


# ============================================================================
# Pattern Extraction
# ============================================================================

PATTERN_EXTRACTION_PROMPT = """You are analyzing a successful sales/outreach call transcript. Extract the winning communication patterns that led to success.

CALL OUTCOME: {outcome}
CLOSE CONFIDENCE: {confidence}/10
PIPELINE STAGE: {stage}

CALL SUMMARY:
{summary}

TRANSCRIPT:
{transcript}

Extract 3-5 specific, actionable communication patterns from this call. Focus on:
1. Opening hooks that created engagement
2. Questions that revealed pain points
3. Reframes that shifted perspective
4. Objection handling that worked
5. Closing language that secured commitment

Format each pattern as:
PATTERN: [Short name]
TRIGGER: [When to use this]
SCRIPT: [Exact language or approach]
WHY IT WORKS: [Psychological principle]

Be specific and tactical. These patterns will be used to train AI agents."""


class PatternExtractor:
    """Extracts winning patterns from call transcripts."""
    
    def __init__(self, config: RecalibrationConfig):
        self.config = config
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def extract_patterns(self, contact: dict) -> List[dict]:
        """Extract patterns from a successful contact."""
        transcript = contact.get("transcript", "")
        summary = contact.get("call_summary", "")
        outcome = contact.get("call_outcome", "unknown")
        confidence = contact.get("close_confidence", 0)
        stage = contact.get("pipeline_stage", "unknown")
        
        if not transcript or len(transcript) < 100:
            return []
        
        prompt = PATTERN_EXTRACTION_PROMPT.format(
            outcome=outcome,
            confidence=confidence,
            stage=stage,
            summary=summary[:1000],
            transcript=transcript[:4000]
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.pattern_extraction_model,
                messages=[
                    {"role": "system", "content": "You extract winning communication patterns from sales calls."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            patterns_text = response.choices[0].message.content
            return self._parse_patterns(patterns_text, contact)
        
        except Exception as e:
            logging.error(f"Pattern extraction failed: {e}")
            return []
    
    def _parse_patterns(self, text: str, contact: dict) -> List[dict]:
        """Parse extracted patterns into structured format."""
        patterns = []
        current_pattern = {}
        
        for line in text.split("\n"):
            line = line.strip()
            
            # Handle various formats (PATTERN:, **PATTERN:**, etc.)
            if "PATTERN:" in line.upper():
                if current_pattern.get("name"):
                    patterns.append(current_pattern)
                # Extract name, removing ** and other formatting
                name = line.split(":", 1)[-1].strip()
                name = name.replace("**", "").replace("*", "").strip()
                current_pattern = {
                    "name": name,
                    "source_contact_id": contact.get("id", ""),
                    "source_company": contact.get("company", "")[:100] if contact.get("company") else "",
                    "confidence": contact.get("close_confidence", 0),
                    "extracted_at": datetime.now().isoformat(),
                }
            elif "TRIGGER:" in line.upper():
                value = line.split(":", 1)[-1].strip()
                current_pattern["trigger"] = value.replace("**", "").strip()
            elif "SCRIPT:" in line.upper():
                value = line.split(":", 1)[-1].strip()
                current_pattern["script"] = value.replace("**", "").strip()
            elif "WHY IT WORKS:" in line.upper() or "WHY:" in line.upper():
                value = line.split(":", 1)[-1].strip()
                current_pattern["why_it_works"] = value.replace("**", "").strip()
        
        if current_pattern.get("name"):
            patterns.append(current_pattern)
        
        return patterns


# ============================================================================
# Supabase Client
# ============================================================================

class SupabaseClient:
    """Simple Supabase REST client."""
    
    def __init__(self, config: RecalibrationConfig):
        self.config = config
        self.base_url = f"{config.supabase_url}/rest/v1"
        self.headers = {
            "apikey": config.supabase_key,
            "Authorization": f"Bearer {config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
    
    def get_winning_contacts(self, limit: int = 10, after_id: str = None) -> List[dict]:
        """Fetch high-confidence contacts from sai_contacts."""
        params = {
            "select": "*",
            "close_confidence": f"gte.{self.config.min_close_confidence}",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        
        # Build query string
        url = f"{self.base_url}/sai_contacts"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Supabase fetch failed: {e}")
            return []


# ============================================================================
# Colosseum Integration
# ============================================================================

class ColosseumClient:
    """Inject patterns into Colosseum judges."""
    
    def __init__(self, config: RecalibrationConfig):
        self.config = config
    
    def get_current_beings(self) -> List[dict]:
        """Get current leaderboard from Colosseum."""
        try:
            response = requests.get(f"{self.config.colosseum_api_url}/api/leaderboard", timeout=10)
            response.raise_for_status()
            return response.json().get("leaderboard", [])
        except Exception as e:
            logging.error(f"Colosseum API error: {e}")
            return []
    
    def inject_patterns_to_judges(self, patterns: List[dict]) -> bool:
        """
        Inject winning patterns into the Colosseum judge system.
        This updates the scenarios with real-world winning examples.
        """
        if not patterns:
            return False
        
        # Store patterns in local DB for judge reference
        patterns_db = self.config.patterns_db
        conn = sqlite3.connect(patterns_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS winning_patterns (
                id TEXT PRIMARY KEY,
                name TEXT,
                trigger TEXT,
                script TEXT,
                why_it_works TEXT,
                source_contact_id TEXT,
                source_company TEXT,
                confidence INTEGER,
                extracted_at TIMESTAMP,
                times_used INTEGER DEFAULT 0
            )
        """)
        
        for pattern in patterns:
            pattern_id = hashlib.md5(
                f"{pattern.get('name', '')}{pattern.get('script', '')}".encode()
            ).hexdigest()[:16]
            
            cursor.execute("""
                INSERT OR REPLACE INTO winning_patterns 
                (id, name, trigger, script, why_it_works, source_contact_id, 
                 source_company, confidence, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern_id,
                pattern.get("name", ""),
                pattern.get("trigger", ""),
                pattern.get("script", ""),
                pattern.get("why_it_works", ""),
                pattern.get("source_contact_id", ""),
                pattern.get("source_company", ""),
                pattern.get("confidence", 0),
                pattern.get("extracted_at", datetime.now().isoformat()),
            ))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Injected {len(patterns)} patterns into Colosseum judges")
        return True


# ============================================================================
# Main Daemon
# ============================================================================

class RecalibrationDaemon:
    """The main recalibration daemon."""
    
    def __init__(self, config: RecalibrationConfig = None):
        self.config = config or RecalibrationConfig()
        self.state = RecalibrationState()
        self.shutdown_event = Event()
        self.logger = self._setup_logging()
        
        # Clients
        self.supabase = SupabaseClient(self.config)
        self.extractor = PatternExtractor(self.config)
        self.colosseum = ColosseumClient(self.config)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup rotating log files."""
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger = logging.getLogger("recalibration_daemon")
        logger.setLevel(logging.INFO)
        
        # File handler
        log_file = self.config.log_dir / "recalibration.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(message)s'
        ))
        logger.addHandler(console_handler)
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name} — shutting down...")
        self.shutdown_event.set()
    
    def _setup_signals(self):
        """Setup signal handlers."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _write_pid(self):
        """Write PID file."""
        self.config.pid_file.write_text(str(os.getpid()))
    
    def _remove_pid(self):
        """Remove PID file."""
        if self.config.pid_file.exists():
            self.config.pid_file.unlink()
    
    def _load_state(self):
        """Load persisted state."""
        if self.config.state_file.exists():
            try:
                data = json.loads(self.config.state_file.read_text())
                self.state = RecalibrationState(**data)
            except Exception as e:
                self.logger.warning(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Persist state."""
        self.config.state_file.write_text(json.dumps(asdict(self.state), indent=2))
    
    def sync_patterns(self) -> int:
        """
        Main sync operation:
        1. Fetch new high-confidence contacts from Supabase
        2. Extract winning patterns from transcripts
        3. Inject patterns into Colosseum judges
        """
        self.logger.info("🔄 Starting pattern sync...")
        
        # Fetch contacts
        contacts = self.supabase.get_winning_contacts(
            limit=self.config.batch_size,
            after_id=self.state.last_contact_id
        )
        
        if not contacts:
            self.logger.info("No new high-confidence contacts found")
            return 0
        
        self.logger.info(f"Found {len(contacts)} contacts with confidence >= {self.config.min_close_confidence}")
        
        all_patterns = []
        for contact in contacts:
            contact_id = contact.get("id", "")
            
            # Skip already processed
            if contact_id in self.state.processed_contact_ids:
                continue
            
            self.logger.info(f"Processing: {contact.get('first_name', 'Unknown')} @ {contact.get('company', 'Unknown')}")
            
            patterns = self.extractor.extract_patterns(contact)
            if patterns:
                all_patterns.extend(patterns)
                self.state.total_patterns_extracted += len(patterns)
                self.logger.info(f"  → Extracted {len(patterns)} patterns")
            
            self.state.processed_contact_ids.append(contact_id)
            self.state.last_contact_id = contact_id
        
        # Inject into Colosseum
        if all_patterns:
            self.colosseum.inject_patterns_to_judges(all_patterns)
            self.state.total_patterns_injected += len(all_patterns)
        
        self.state.total_syncs += 1
        self.state.last_sync_time = datetime.now().isoformat()
        self._save_state()
        
        self.logger.info(f"✅ Sync complete — {len(all_patterns)} patterns injected")
        return len(all_patterns)
    
    def run(self, daemon: bool = False):
        """Run the daemon."""
        self._setup_signals()
        self._write_pid()
        self._load_state()
        
        self.state.started_at = datetime.now().isoformat()
        
        self.logger.info("=" * 60)
        self.logger.info("🔄 RECALIBRATION DAEMON STARTED")
        self.logger.info(f"   Sync interval: {self.config.sync_interval_seconds}s")
        self.logger.info(f"   Min confidence: {self.config.min_close_confidence}")
        self.logger.info(f"   Colosseum API: {self.config.colosseum_api_url}")
        self.logger.info("=" * 60)
        
        try:
            while not self.shutdown_event.is_set():
                try:
                    self.sync_patterns()
                except Exception as e:
                    self.logger.error(f"Sync error: {e}")
                    self.logger.error(traceback.format_exc())
                
                # Wait for next sync
                self.shutdown_event.wait(self.config.sync_interval_seconds)
        
        finally:
            self._save_state()
            self._remove_pid()
            self.logger.info("Daemon stopped")
    
    @classmethod
    def get_status(cls) -> dict:
        """Get daemon status."""
        config = RecalibrationConfig()
        
        status = {
            "running": False,
            "pid": None,
            "state": None,
        }
        
        if config.pid_file.exists():
            pid = int(config.pid_file.read_text().strip())
            try:
                os.kill(pid, 0)
                status["running"] = True
                status["pid"] = pid
            except OSError:
                pass
        
        if config.state_file.exists():
            try:
                status["state"] = json.loads(config.state_file.read_text())
            except:
                pass
        
        # Pattern stats
        if config.patterns_db.exists():
            conn = sqlite3.connect(config.patterns_db)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM winning_patterns")
                status["total_patterns_in_db"] = cursor.fetchone()[0]
            except:
                pass
            conn.close()
        
        return status
    
    @classmethod
    def stop(cls):
        """Stop the daemon."""
        config = RecalibrationConfig()
        
        if not config.pid_file.exists():
            print("No daemon running")
            return
        
        pid = int(config.pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to PID {pid}")
        except OSError as e:
            print(f"Failed to stop daemon: {e}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Recalibration Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--stop", action="store_true", help="Stop daemon")
    parser.add_argument("--sync-now", action="store_true", help="One-shot sync")
    args = parser.parse_args()
    
    if args.status:
        status = RecalibrationDaemon.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.stop:
        RecalibrationDaemon.stop()
        return
    
    daemon = RecalibrationDaemon()
    
    if args.sync_now:
        daemon._setup_logging()
        daemon.sync_patterns()
        return
    
    if args.daemon:
        # Fork to background
        if os.fork() > 0:
            sys.exit(0)
        os.setsid()
        if os.fork() > 0:
            sys.exit(0)
    
    daemon.run(daemon=args.daemon)


if __name__ == "__main__":
    main()
