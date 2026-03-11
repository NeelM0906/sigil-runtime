# Environment Template — Mac Studio

Create `~/.openclaw/.env` with these keys before running the setup script.

```bash
mkdir -p ~/.openclaw
nano ~/.openclaw/.env
# paste the block below, fill in values
chmod 600 ~/.openclaw/.env
```

## Required Keys

```env
# OpenRouter (ALL LLM calls)
OPENROUTER_API_KEY=

# OpenAI (Whisper transcription ONLY)
OPENAI_API_KEY=

# Anthropic (direct, fallback)
ANTHROPIC_API_KEY=

# Supabase / Postgres
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
DATABASE_URL=

# Pinecone
PINECONE_API_KEY=
PINECONE_API_KEY_STRATA=

# ElevenLabs
ELEVENLABS_API_KEY=

# Telegram Bot (create in BotFather for this instance)
TELEGRAM_BOT_TOKEN_7L=
```

## Optional Keys (add as needed)

```env
# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_API_KEY_SID=
TWILIO_API_KEY_SECRET=

# Bland.ai
BLAND_API_KEY=

# Deepgram
DEEPGRAM_API_KEY=

# fal.ai
FAL_KEY=

# Fathom
FATHOM_API_KEY=
FATHOM_WEBHOOK_SECRET=

# Perplexity
PERPLEXITY_API_KEY=

# Vercel
VERCEL_TOKEN=

# ngrok
NGROK_AUTHTOKEN=

# Google Workspace
GOG_KEYRING_PASSWORD=
```

## Setup Steps

1. Create the `.env` file with your keys
2. Run the setup script:
   ```bash
   git clone https://github.com/samanthaaiko-collab/SAI.git ~/.openclaw/workspace
   chmod +x ~/.openclaw/workspace/tools/setup-seven-levers.sh
   ~/.openclaw/workspace/tools/setup-seven-levers.sh
   ```
3. Create a Telegram bot in BotFather, add token to `.env`
4. Restart gateway: `openclaw gateway restart`
5. Pair your Telegram: `openclaw pair`

Ask Sai (on the Mac mini) for the actual key values.
