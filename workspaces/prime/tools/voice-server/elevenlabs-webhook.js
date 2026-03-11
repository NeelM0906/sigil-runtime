// ElevenLabs Post-Call Webhook Handler
// Receives transcripts and forwards to OpenClaw/Sai

import express from 'express';
import fs from 'fs';
import path from 'path';

const app = express();
app.use(express.json());

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(__dirname, '../../../../');
const MEMORY_DIR = process.env.OPENCLAW_MEMORY_DIR || path.join(REPO_ROOT, 'workspaces', 'prime', 'memory');
const WEBHOOK_PORT = 3335;

// POST /elevenlabs/webhook - Receive post-call data
app.post('/elevenlabs/webhook', async (req, res) => {
  try {
    const data = req.body;
    console.log('\n📞 ElevenLabs Post-Call Webhook Received');
    console.log('Agent:', data.agent_id);
    console.log('Call ID:', data.conversation_id);
    
    // Extract transcript
    const transcript = data.transcript || [];
    const messages = transcript.map(t => `${t.role}: ${t.message}`).join('\n');
    
    console.log('\n📝 Transcript:');
    console.log(messages);
    
    // Save to daily memory file
    const today = new Date().toISOString().split('T')[0];
    const memoryFile = path.join(MEMORY_DIR, `${today}.md`);
    
    const entry = `
## Voice Call via ElevenLabs — ${new Date().toLocaleTimeString()}
- **Agent:** ${data.agent_id}
- **Call ID:** ${data.conversation_id}
- **Duration:** ${data.call_duration_secs || 'unknown'}s

### Transcript
${messages}

---
`;
    
    fs.appendFileSync(memoryFile, entry);
    console.log(`\n✅ Saved to ${memoryFile}`);
    
    // TODO: Trigger OpenClaw message to process the call
    // Could use sessions_send or similar
    
    res.json({ status: 'ok', saved: true });
  } catch (err) {
    console.error('Webhook error:', err);
    res.status(500).json({ error: err.message });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'elevenlabs-webhook' });
});

app.listen(WEBHOOK_PORT, () => {
  console.log(`🎧 ElevenLabs Webhook listening on port ${WEBHOOK_PORT}`);
});
