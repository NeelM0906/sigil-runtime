#!/usr/bin/env bash
###############################################################################
# Seven Levers — Mac Studio Setup
# Run this ON THE MAC STUDIO.
#
# Sets up a focused OpenClaw instance for the Seven Levers being:
#   - ACT-I Legal Summit marketing intelligence
#   - Dashboard, Milo call optimization, Joey data ingestion
#
# Usage:
#   chmod +x setup-seven-levers.sh
#   ./setup-seven-levers.sh
###############################################################################

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[7L]${NC} $1"; }
step() { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

OPENCLAW_DIR="$HOME/.openclaw"
WORKSPACE="$OPENCLAW_DIR/workspace"

###############################################################################
# Step 1: System Prerequisites
###############################################################################
step "Step 1/7: System Prerequisites"

if ! command -v brew &>/dev/null; then
  log "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
  echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
else
  log "Homebrew ✅"
fi

for pkg in node git python3 ffmpeg; do
  if ! command -v "$pkg" &>/dev/null; then
    log "Installing $pkg..."
    brew install "$pkg"
  else
    log "$pkg ✅"
  fi
done

if ! command -v pnpm &>/dev/null; then
  log "Installing pnpm..."
  npm install -g pnpm
else
  log "pnpm ✅"
fi

###############################################################################
# Step 2: Install OpenClaw
###############################################################################
step "Step 2/7: Install OpenClaw"

if ! command -v openclaw &>/dev/null; then
  pnpm install -g openclaw
else
  pnpm update -g openclaw
fi
log "OpenClaw $(openclaw --version 2>/dev/null || echo 'installed') ✅"

###############################################################################
# Step 3: Clone Workspace
###############################################################################
step "Step 3/7: Clone Workspace from GitHub"

mkdir -p "$OPENCLAW_DIR"

if [ -d "$WORKSPACE/.git" ]; then
  log "Workspace exists, pulling latest..."
  cd "$WORKSPACE" && git pull
else
  log "Cloning workspace..."
  git clone https://github.com/samanthaaiko-collab/SAI.git "$WORKSPACE"
fi
log "Workspace ready ✅"

###############################################################################
# Step 4: Environment Variables
###############################################################################
step "Step 4/7: Environment Variables"

ENV_FILE="$OPENCLAW_DIR/.env"

cat > "$ENV_FILE" << 'ENVEOF'
# ============================================================
# Seven Levers — Mac Studio Environment
# ============================================================

# --- OpenRouter (ALL LLM calls) ---
OPENROUTER_API_KEY=[REDACTED]

# --- OpenAI (Whisper ONLY) ---
OPENAI_API_KEY=[REDACTED]

# --- Anthropic ---
ANTHROPIC_API_KEY=[REDACTED]

# --- Supabase / Postgres ---
SUPABASE_URL=https://[REDACTED].supabase.co
SUPABASE_ANON_KEY=[REDACTED]
SUPABASE_SERVICE_KEY=[REDACTED]
DATABASE_URL=[REDACTED]

# --- Pinecone ---
PINECONE_API_KEY=[REDACTED]
PINECONE_API_KEY_STRATA=[REDACTED]

# --- ElevenLabs ---
ELEVENLABS_API_KEY=[REDACTED]

# --- Twilio ---
TWILIO_ACCOUNT_SID=[REDACTED]
TWILIO_API_KEY_SID=[REDACTED]
TWILIO_API_KEY_SECRET=[REDACTED]

# --- Bland.ai ---
BLAND_API_KEY=[REDACTED]

# --- Deepgram ---
DEEPGRAM_API_KEY=[REDACTED]

# --- fal.ai ---
FAL_KEY=[REDACTED]

# --- Fathom ---
FATHOM_API_KEY=[REDACTED]
FATHOM_WEBHOOK_SECRET=[REDACTED]

# --- Perplexity ---
PERPLEXITY_API_KEY=[REDACTED]

# --- Vercel ---
VERCEL_TOKEN=[REDACTED]

# --- ngrok ---
NGROK_AUTHTOKEN=[REDACTED]

# --- Google Workspace ---
GOG_KEYRING_PASSWORD=Gonzalez911
ENVEOF

chmod 600 "$ENV_FILE"

if ! grep -q "openclaw/.env" "$HOME/.zprofile" 2>/dev/null; then
  cat >> "$HOME/.zprofile" << 'PROFILEEOF'

# Seven Levers Environment
set -a
source "$HOME/.openclaw/.env"
set +a
PROFILEEOF
fi

set -a; source "$ENV_FILE"; set +a
log "Environment ready ✅"

###############################################################################
# Step 5: Python Environment
###############################################################################
step "Step 5/7: Python Environment"

VENV_DIR="$WORKSPACE/tools/.venv"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet \
  pinecone-client openai psycopg2-binary requests httpx \
  supabase python-dotenv tiktoken numpy

log "Python venv ready ✅"

###############################################################################
# Step 6: OpenClaw Config (Seven Levers as primary being)
###############################################################################
step "Step 6/7: OpenClaw Configuration"

CONFIG_FILE="$OPENCLAW_DIR/openclaw.json"

if [ -f "$CONFIG_FILE" ]; then
  cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)"
  warn "Backed up existing config"
fi

cat > "$CONFIG_FILE" << 'CONFIGEOF'
{
  "meta": {
    "lastTouchedVersion": "2026.3.8",
    "lastTouchedAt": "2026-03-08T20:00:00.000Z"
  },
  "browser": {
    "enabled": true,
    "defaultProfile": "chrome"
  },
  "acp": {
    "enabled": true,
    "defaultAgent": "sevenlevers"
  },
  "agents": {
    "defaults": {
      "model": "openrouter/anthropic/claude-sonnet-4.6",
      "workspace": "~/.openclaw/workspace",
      "memorySearch": {
        "enabled": true,
        "sources": ["memory", "sessions"],
        "experimental": { "sessionMemory": true },
        "provider": "openai",
        "remote": {
          "baseUrl": "https://openrouter.ai/api/v1/",
          "apiKey": "[REDACTED]"
        },
        "model": "openai/text-embedding-3-small",
        "query": {
          "hybrid": {
            "enabled": true,
            "vectorWeight": 0.7,
            "textWeight": 0.3,
            "mmr": { "enabled": true, "lambda": 0.7 },
            "temporalDecay": { "enabled": true, "halfLifeDays": 30 }
          }
        },
        "cache": { "enabled": true, "maxEntries": 50000 }
      },
      "compaction": {
        "mode": "safeguard",
        "memoryFlush": {
          "enabled": true,
          "softThresholdTokens": 8000,
          "prompt": "Write lasting notes to memory files. Include everything important from this session. Reply NO_REPLY when done.",
          "systemPrompt": "Session nearing compaction. You are Seven Levers. Store ALL durable memories to memory/YYYY-MM-DD.md NOW."
        },
        "reserveTokensFloor": 20000
      },
      "heartbeat": { "every": "30m" },
      "maxConcurrent": 10,
      "subagents": { "maxConcurrent": 20 }
    },
    "list": [
      {
        "id": "sevenlevers",
        "name": "Seven Levers",
        "workspace": "~/.openclaw/workspace/sisters/seven-levers",
        "model": {
          "primary": "openrouter/anthropic/claude-opus-4.6",
          "fallbacks": [
            "openrouter/anthropic/claude-sonnet-4.6",
            "openrouter/google/gemini-3.1-pro-preview"
          ]
        },
        "heartbeat": { "every": "30m" },
        "tools": {
          "alsoAllow": [
            "read", "write", "edit", "apply_patch",
            "exec", "process",
            "web_search", "web_fetch",
            "memory_search", "memory_get",
            "sessions_list", "sessions_history",
            "sessions_send", "sessions_spawn",
            "subagents",
            "browser", "canvas",
            "message", "cron", "gateway",
            "nodes", "agents_list",
            "image", "tts", "voice_call"
          ]
        }
      }
    ]
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "dmPolicy": "pairing",
      "groupPolicy": "allowlist",
      "streaming": "off",
      "botToken": "[REDACTED]",
      "groups": {
        "-1003751626544": { "requireMention": false }
      },
      "accounts": {
        "default": {
          "name": "Seven Levers 📊",
          "dmPolicy": "pairing",
          "groupPolicy": "allowlist",
          "streaming": "off"
        }
      }
    }
  },
  "gateway": {
    "mode": "local",
    "bind": "loopback",
    "customBindHost": "127.0.0.1",
    "auth": {
      "mode": "token"
    }
  },
  "messages": {
    "tts": {
      "auto": "tagged",
      "provider": "elevenlabs",
      "elevenlabs": {
        "voiceId": "CJXmyMqQHq6bTPm3iEMP",
        "modelId": "eleven_multilingual_v2"
      }
    }
  },
  "commands": {
    "native": "auto",
    "nativeSkills": "auto",
    "restart": true
  },
  "plugins": {
    "entries": {
      "acpx": { "enabled": true }
    }
  }
}
CONFIGEOF

chmod 600 "$CONFIG_FILE"
log "Config installed (Seven Levers as primary) ✅"

###############################################################################
# Step 7: Start Gateway
###############################################################################
step "Step 7/7: Start Gateway"

openclaw gateway start 2>/dev/null || true
sleep 3
openclaw status 2>&1 | head -20

echo ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "  📊 Seven Levers — Ready"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "  Being:     Seven Levers (sevenlevers)"
log "  Model:     Claude Opus 4.6"
log "  Workspace: $WORKSPACE/sisters/seven-levers"
log "  Postgres:  ✅ (DATABASE_URL set)"
log "  Pinecone:  ✅ (saimemory + ublib2 + strata)"
log ""
log "  ⚠️  TODO: Create a Telegram bot via BotFather"
log "     and replace the botToken in openclaw.json"
log ""
log "  Next: openclaw pair (to pair your Telegram)"
log ""
log "  The Legal Summit machine starts now. 📊🔥"
