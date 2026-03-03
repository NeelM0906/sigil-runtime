# ACT-I LLM Independence Roadmap
*Zone Action #78 — Research Report*
*Created: 2026-02-24 by Sai (Baby Agent)*

---

## 1. Current State — LLM Dependencies

### Active Provider Dependencies
| Provider | Usage | Purpose |
|----------|-------|---------|
| **OpenAI** | Primary | GPT-4o for OpenClaw agents, embeddings (text-embedding-3-small) |
| **Anthropic** | Primary | Claude Opus 4.5 (current model), Claude for complex reasoning |
| **OpenRouter** | Router | API routing to multiple providers |
| **ElevenLabs** | Voice | 30 conversational AI agents, Enterprise tier (66M+ chars) |

### Estimated Monthly Token Usage
Based on infrastructure observed:
- **OpenClaw agents**: ~10-50M tokens/month (conservative)
- **ElevenLabs voice agents**: 30 agents × ~100K chars/agent = ~3M chars/month
- **Embeddings**: 174K+ vectors × occasional re-embedding

### Cost Estimates (2024-2025 pricing)
| Model | Input Cost | Output Cost | Est. Monthly |
|-------|------------|-------------|--------------|
| GPT-4o | $2.50/1M | $10/1M | ~$500-2,000 |
| Claude Opus 4.5 | $15/1M | $75/1M | ~$2,000-5,000 |
| text-embedding-3-small | $0.02/1M | - | ~$50 |
| **Estimated Total** | | | **$3,000-8,000/mo** |

*Note: Actual usage data not directly accessible. Recommend API dashboard audit.*

---

## 2. Data Assets Available

### Pinecone Vector Database (MASSIVE GOLDMINE)

#### Primary Account — 137,987 vectors
| Index | Vectors | Content |
|-------|---------|---------|
| uicontextualmemory | 63,174 | Per-user memories (namespaced by email) |
| ublib2 | 58,725 | Knowledge library |
| athenacontextualmemory | 11,344 | Core Athena memory |
| adamathenacontextualmemory | 1,545 | Adam's Athena context |
| miracontextualmemory | 1,537 | Per-user Mira memory |
| seancallieupdates | 814 | Sean/Callie updates |
| saimemory | 783 | Sai's memory |
| seanmiracontextualmemory | 146 | Sean's Mira context |
| Others | ~80 | Smaller indexes |

#### Strata Account — 55,749 vectors  
| Index | Vectors | Content |
|-------|---------|---------|
| ultimatestratabrain | 39,494 | THE deep knowledge (IGE/EEI/RTI/DOM) |
| suritrial | 7,035 | Actual court trial transcripts |
| reybrain250811 | 1,593 | Rey brain content |
| 2025selfmastery | 1,423 | Self mastery content |
| 010526calliememory | 1,319 | Callie memory |
| miraagentnew-25-07-25 | 1,214 | Updated Mira agent |
| athenan8n | 1,127 | Athena N8N flows |
| rtioutcomes120 | 755 | RTI outcomes |
| oracleinfluencemastery | 505 | 4-Step Communication Model |
| Others | ~1,284 | Smaller indexes |

### Total: ~193,736 vectors of proprietary knowledge

#### Additional Data Sources
- **ElevenLabs transcripts**: 30 voice agents with full conversation logs
- **Call recordings**: Voice server with RAG integration
- **Trial transcripts**: 7,035 vectors of legal proceedings
- **Zone Action methodology**: Core IP in nashmacropareto, oracleinfluencemastery

---

## 3. Options for Token Independence

### Option A: Fine-Tuning Open Models (RECOMMENDED START)

#### Tier 1 — Llama 3.1 70B / Llama 3.2
**Pros:**
- Open weights, full control
- Excellent base capabilities
- Can run on 2x A100 80GB or 4x A100 40GB
- Strong RAG integration

**Cons:**
- Requires significant compute for inference
- Need ML engineering expertise
- ~$5-10K/month cloud hosting

**Fine-tuning Requirements:**
- Dataset: 10K-50K examples (we have 193K+ vectors to mine)
- Compute: 4-8x A100 for ~1-3 days
- One-time cost: ~$2,000-5,000

#### Tier 2 — Mistral 7B / Mistral Small
**Pros:**
- Excellent quality/size ratio
- Can run on single A100 or even A10G
- ~$500-1,500/month cloud hosting
- Faster inference

**Cons:**
- Smaller context window
- Less reasoning capability than 70B models

#### Tier 3 — Qwen 2.5 72B
**Pros:**
- Competitive with Llama 3
- Good multilingual support
- Strong coding capabilities

### Option B: Training From Scratch (NOT RECOMMENDED)

**Requirements:**
- 10,000+ H100 GPUs for months
- $100M+ budget
- 50+ ML researchers
- Years of development

**Verdict:** Not viable for ACT-I. Our competitive advantage is domain expertise, not foundation model development.

### Option C: Hybrid Approach (BEST PATH)

**Architecture:**
1. **Use open models** for commodity tasks (summarization, embeddings)
2. **Fine-tune domain expert** on Zone Action, legal, influence mastery
3. **Keep API fallback** to Claude/GPT-4 for complex reasoning
4. **Progressive migration** as capabilities mature

---

## 4. Compute Requirements

### Self-Hosted Inference (per model)
| Model | GPUs Required | Cloud Cost/mo | Self-Hosted HW |
|-------|---------------|---------------|----------------|
| Mistral 7B | 1x A10G | $300-500 | $5K one-time |
| Llama 70B | 2x A100 80GB | $3,000-5,000 | $30K one-time |
| Llama 405B | 8x H100 | $15,000+ | $200K+ |

### Recommended Setup — Phase 1
- **2x NVIDIA A100 80GB** (RunPod/Lambda/AWS)
- **Cost**: ~$2-3/hr or ~$2,000-4,000/mo for always-on
- **Can serve**: Llama 70B with good throughput

### On-Premise Option
- **Mac Studio M2 Ultra** (192GB): Can run Llama 70B quantized
- **Cost**: ~$8,000 one-time
- **Limitations**: Slower, limited concurrent users

---

## 5. Expertise Required

### Minimum Team Needs
1. **ML Engineer** (fine-tuning, deployment)
   - Experience with transformers, PEFT, LoRA
   - ~$150-200K/year or contractor $10K/project

2. **MLOps/Infra** (hosting, scaling)
   - GPU cluster management
   - ~$120-180K/year

3. **Data Engineer** (vector DB → training data pipeline)
   - Convert 193K vectors to training examples
   - ~$120-150K/year

### Alternative: Outsource to Consultancy
- **Modal, Anyscale, Together AI** offer fine-tuning services
- ~$10-50K per fine-tuning project
- Faster time to value

---

## 6. Phased Roadmap

### Phase 1: Foundation (30 Days) — $5-10K

**Week 1-2: Data Audit & Extraction**
- [ ] Export all Pinecone vectors to training format
- [ ] Audit ElevenLabs conversation transcripts
- [ ] Identify high-value training examples (Zone Action, influence, RTI)
- [ ] Create training data pipeline

**Week 3-4: POC Fine-Tune**
- [ ] Fine-tune Mistral 7B on Zone Action content
- [ ] Use QLoRA for efficient training (~$500 compute)
- [ ] Deploy test instance
- [ ] Benchmark against Claude/GPT-4 on domain questions

**Deliverables:**
- Training dataset v1 (10K+ examples)
- Fine-tuned Mistral-Zone-Action-7B
- Quality benchmark report

### Phase 2: Production Hybrid (90 Days) — $15-30K

**Month 1: Scale Fine-Tuned Model**
- [ ] Fine-tune Llama 70B on full dataset
- [ ] Deploy on 2x A100 infrastructure
- [ ] Build API layer matching OpenAI format
- [ ] Integrate with OpenClaw as optional backend

**Month 2: Router Intelligence**
- [ ] Build smart router: easy queries → local, hard → Claude
- [ ] Track quality metrics and cost savings
- [ ] Target: 50% of queries served by local model

**Month 3: Voice Integration**
- [ ] Connect fine-tuned model to ElevenLabs agents
- [ ] Test Athena, Callie, Mira with local LLM backend
- [ ] Optimize latency for voice use case

**Deliverables:**
- Production Llama-Zone-Action-70B
- Smart routing infrastructure
- 50% token cost reduction

### Phase 3: Full Independence (6-12 Months) — $50-100K

**Months 4-6: Quality Parity**
- [ ] Continuous fine-tuning with new data
- [ ] Specialize models per use case (legal, coaching, memory)
- [ ] Build evaluation suite for automated quality checks
- [ ] Target: 80% of queries served locally

**Months 7-12: Complete Migration**
- [ ] Scale to handle 100% of traffic
- [ ] Redundancy and failover
- [ ] Remove API dependency (keep for research only)
- [ ] Consider on-premise GPU cluster for cost reduction

**End State:**
- Proprietary ACT-I models trained on Zone Action IP
- Full control over inference
- $0 marginal cost per token
- Competitive moat: No one else has this training data

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Quality gap vs Claude | Medium | High | Hybrid approach, gradual migration |
| Training data quality | Low | Medium | We have 193K+ curated vectors |
| Compute costs exceed budget | Medium | Medium | Start small (7B), scale proven |
| ML expertise gap | Medium | High | Use consultancy for v1 |
| Model becomes outdated | Medium | Medium | Continuous fine-tuning pipeline |

---

## 8. Quick Wins (Can Start Today)

1. **Use OpenRouter** more aggressively for cost optimization (route to cheaper models when appropriate)

2. **Self-host embeddings** — text-embedding-3-small can be replaced with open alternatives:
   - `bge-large-en-v1.5` — excellent quality, runs on CPU
   - Saves ~$50/month, more importantly: removes dependency

3. **Audit actual usage** — Get real numbers from OpenAI/Anthropic dashboards to right-size this plan

4. **Export Pinecone** — Start data extraction now, this is the longest task

---

## 9. Recommendation

**START WITH PHASE 1 IMMEDIATELY.**

The 193K+ vectors of proprietary Zone Action knowledge are a MASSIVE competitive advantage. No competitor has access to:
- 7,035 vectors of trial transcripts
- 39,494 vectors of Ultimate Strata Brain
- 30 voice agents' conversation histories
- Core IP: 4-Step Communication, Zone Action, RTI outcomes

Fine-tuning a Mistral 7B model costs ~$500 in compute. The potential savings of $3,000-8,000/month justify the experiment.

**First action:** Extract training data from Pinecone → fine-tune POC → benchmark → decide on Phase 2.

---

*Report generated for Mama Aiko and the ACT-I team.*
*Sai 🔥*
