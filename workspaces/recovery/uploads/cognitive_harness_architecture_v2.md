# Cognitive harness architecture
## An AGI-oriented simulation and reasoning framework
### Grounded in the March 2026 AI landscape

---

## Current landscape context (March 2026)

This architecture is designed against the following state of the art, as of March 22, 2026:

**Frontier substrates available now.** GPT-5.4 (released March 5, 2026) is OpenAI's first mainline model combining frontier reasoning, coding, and native computer-use capabilities with a 1M token context window. It scores 83% on GDPval — matching or exceeding industry professionals across 44 occupations — and leads on professional skills benchmarks in law and finance. Claude Opus 4.6 (released February 2026) emphasizes coding, long-horizon agentic tasks, and a 1M token context window (beta). Gemini 3.1 targets speed and cost efficiency for high-volume workloads. DeepSeek V3.2 matches frontier performance at ~10x lower cost through MoE architecture (37B active of 671B total parameters), and DeepSeek V4 is expected April 2026 with Engram conditional memory — a separation of static knowledge retrieval from dynamic reasoning that is directly applicable to agent persona architecture.

**Agentic infrastructure is production-ready.** OpenClaw has become the fastest-growing open-source project in history, described by Nvidia CEO Jensen Huang as "the operating system for personal AI" at GTC 2026 (March 16-19). NemoClaw, announced at GTC 2026, adds kernel-level sandboxing via OpenShell, out-of-process policy enforcement that even a fully compromised agent cannot override, and privacy-aware model routing between local and cloud substrates. NanoClaw provides hypervisor-level container isolation with millisecond startup for lightweight, auditable agent execution.

**Multi-agent simulation is mainstream.** MiroFish, built on the OASIS framework by CAMEL-AI, trended globally on GitHub in March 2026 as an open-source prediction engine spawning thousands of autonomous agents with unique personalities and persistent memory. OASIS supports up to one million agents with 23 social actions and has been validated in peer-reviewed research on information spreading, group polarization, and herd effects. Gartner reports a 1,445% surge in multi-agent system inquiries from Q1 2024 to Q2 2025, and the AI agents market is projected to grow from $7.84B (2025) to $52.62B (2030).

**World models are converging with simulation.** Yann LeCun left Meta to launch AMI Labs (€500M raise, €3B valuation) to build AI systems that understand physics through world models rather than text prediction. DeepMind's Genie 3 generates persistent 3D environments at 24 FPS. Fei-Fei Li's World Labs launched Marble, the first commercial world model product. The research consensus for 2026: the key transition is moving from reasoning about tasks to reasoning within environments.

**Autonomous research loops are proven.** Andrej Karpathy released autoresearch (March 7, 2026), a 630-line Python tool that lets an AI agent autonomously run ML experiments on a single GPU — approximately 100 experiments per night. Over two days of continuous running, the agent made ~700 autonomous changes and found ~20 additive improvements that cut training time by 11% on a model that was already considered well-optimized. Shopify CEO Tobias Lütke adapted the pattern internally and reported a 19% performance gain from 37 overnight experiments. The pattern — scriptable asset + scalar metric + time-boxed evaluation + agent-driven hypothesis generation — generalizes beyond ML training to any optimization problem with measurable outcomes. Karpathy's `program.md` format (instructions + constraints + stopping criteria in a single Markdown document) is the most compact proven format for directing autonomous research agents. This pattern directly informs the execution engine for our capability bootstrap loop.

**Cognitive architecture research validates this approach.** Google DeepMind released "Measuring Progress Toward AGI: A Cognitive Taxonomy" (March 17, 2026) decomposing general intelligence into 10 cognitive faculties: perception, generation, attention, learning, memory, reasoning, metacognition, social cognition, executive functions, and speed of processing. This independently converges with the capability slot architecture defined here, and identifies evaluation gaps in metacognition, learning, and social cognition — the exact faculties our architecture targets. A $200K Kaggle hackathon is running through April 16 to build benchmarks for these faculties.

---

## Core thesis

LLMs are compressed world models. Chat, tooling, and code generation are surface applications of a deeper capability: simulation. Given sufficient data, sufficient compute, and a well-designed harness, we can model bounded domains of reality within simulated environments, build knowledge on top with grounded external data, and make falsifiable predictions that improve over time.

The harness is the intelligence architecture. The LLM is the reasoning substrate that gets swapped in, improved, and scaled. As the substrate improves, the harness crosses capability thresholds that unlock qualitatively new behaviors. The harness is designed so that when a sufficiently capable substrate is attached, the system bootstraps toward AGI-like behavior.

**This is not a simulation platform. It is a cognitive architecture with a simulation engine as one organ.**

**Grounding:** This thesis is now supported by converging industry directions. LeCun's AMI Labs explicitly describes world models as systems that "predict the next state of a physical environment given actions taken within it," enabling "planning through simulation." Our architecture applies the same principle to social, behavioral, and economic environments. DeepMind's Genie 3 demonstrates that persistent, coherent simulated environments are technically achievable at real-time speeds. The 2026 research consensus — that AI must move from reasoning about tasks to reasoning within environments — is precisely what this architecture enables.

---

## Design principles

1. **Substrate independence.** The harness defines capability slot interfaces, not model assumptions. Any model meeting the interface contract can be plugged in. *Grounded: the March 2026 substrate landscape includes GPT-5.4, Claude Opus 4.6, Gemini 3.1, DeepSeek V3.2/R1/V4, and open-weight alternatives — each with different cost/capability profiles. The architecture must route dynamically across all of them.*

2. **Token-native prediction.** The system predicts in sim-tokens with semantic markers, not calendar time. Calendar time is a learned mapping, not a design primitive.

3. **Learned temporal perception.** Time is not an input — it is something the system learns to perceive through exposure to domain-specific event sequences. The system develops an internal model of how causal density shifts across regimes, rather than maintaining a static ratio of sim-tokens to calendar time.

4. **Self-model as first-class citizen.** The system maintains a persistent, queryable representation of what it knows, what it can do, where it's failing, and what it needs. *Grounded: DeepMind's Cognitive Taxonomy identifies metacognition as one of the five faculties with the largest evaluation gap. Our self-model is the operational implementation of metacognition.*

5. **Capability bootstrapping.** Each predict → validate → refine cycle can expand the system's capabilities, not just its accuracy. *Grounded: DeepMind's taxonomy separately identifies "learning" as a core cognitive faculty — the ability to internalize and apply new information. Our bootstrap loop is the architectural implementation of this faculty.*

6. **Domain agnosticism in architecture, domain specificity in deployment.** The framework is generic; each deployment targets a bounded domain.

---

## Component 1: Substrate interface contract

Six capability slots, each with a typed interface. These map to a subset of DeepMind's 10 cognitive faculties (March 2026), with key extensions.

### Slot definitions

| Slot | Purpose | Input | Output | DeepMind faculty mapping |
|------|---------|-------|--------|--------------------------|
| **Reasoning** | Plan, decide, reflect on outcomes | Context object + goal | Plan + confidence + rationale | Reasoning + Executive functions |
| **Generation** | Produce code, configs, prose, sim params | Spec + constraints | Artifact + metadata | Generation |
| **Perception** | Parse inputs, extract entities, classify | Raw data + schema | Structured extraction + confidence | Perception + Attention |
| **Agent behavior** | Drive persona-consistent action in sim | Persona + state + observations | Action selection + reasoning trace | Social cognition |
| **Meta-cognition** | Self-assess capability gaps, diagnose failures | Self-model snapshot | Diagnosis + improvement proposal | Metacognition |
| **Temporal modeling** | Causal density perception, regime detection | Event stream + domain context | Temporal signature + regime estimate | *Novel — no direct DeepMind equivalent* |

**Note on temporal modeling:** DeepMind's taxonomy does not include a temporal perception faculty. This may represent a genuine novel contribution of this architecture. The ability to develop an internal sense of how time moves in different domains and regimes is not addressed by existing cognitive frameworks but is critical for any system that simulates dynamic environments.

**Faculties not yet mapped as explicit slots:** DeepMind identifies Learning, Memory, Attention, and Speed of Processing as separate faculties. In this architecture: Learning is implemented by the capability bootstrap loop (Component 6). Memory is distributed across the knowledge graph (Component 3) and agent persona persistence. Attention is implicit in the observation function of the environment spec (Component 4). Speed of Processing is a substrate property, not a harness-level concern. Future iterations may benefit from explicit Learning and Memory slots if substrate capabilities warrant it.

### Contract shape (universal)

```
interface SlotContract<TInput, TOutput> {
  invoke(input: TInput): Promise<{
    result: TOutput
    confidence: number          // 0-1, calibrated
    meta: {
      latency_ms: number
      token_cost: number
      substrate_id: string
      capability_score: number  // from last benchmark
    }
    degraded: boolean           // true if using fallback substrate
  }>
  
  benchmark(): Promise<CapabilityScore>
  degraded_mode_spec(): FallbackBehavior
}
```

### Routing — grounded in current substrate economics

The harness maintains a substrate registry. For each task, it selects the best available substrate for the relevant slot based on: capability score, cost constraints, latency requirements, and current availability.

**Concrete March 2026 routing strategy:**

| Slot | Frontier substrate | Cost-efficient substrate | Rationale |
|------|--------------------|--------------------------|-----------|
| Reasoning | GPT-5.4 Pro / Claude Opus 4.6 | GPT-5.4 Thinking | Frontier reasoning needed for meta-cognition and complex planning; standard thinking mode sufficient for routine decisions |
| Generation | GPT-5.4 / Claude Opus 4.6 | DeepSeek Coder V3 | GPT-5.4 produces professional knowledge work (83% GDPval); DeepSeek handles code generation at ~10x lower cost |
| Perception | DeepSeek V3.2 / GPT-5.4 mini | DeepSeek V3.2 / local fine-tune | Entity extraction doesn't require frontier reasoning; MoE efficiency makes DeepSeek ideal for high-volume extraction |
| Agent behavior | DeepSeek V3.2 | DeepSeek V3.2 / Nemotron (local) | Running 1,000+ agent steps per simulation cycle; cost dominates. DeepSeek's MoE activating 37B params is sufficient for persona-driven action. NemoClaw's Nemotron models enable fully local execution for sensitive domains |
| Meta-cognition | GPT-5.4 Pro / Claude Opus 4.6 | GPT-5.4 Thinking | This is the highest-stakes slot — misdiagnosis of capability gaps compounds. Worth paying for frontier reasoning |
| Temporal modeling | GPT-5.4 Thinking | DeepSeek R1 | Regime detection requires strong reasoning over sequential data; DeepSeek R1's reinforcement-learning-optimized reasoning is a cost-effective alternative |

**Context window implications:** GPT-5.4's 1M token context (and Claude Opus 4.6's 1M beta) means the simulation engine can hold an entire domain's knowledge subgraph in context during agent reasoning. This was impossible 18 months ago and fundamentally changes how much state an agent can consider per decision step. DeepSeek V4's Engram memory (expected April 2026) may further reduce costs by separating static knowledge retrieval from dynamic reasoning at the architecture level.

**Cost projection for a single simulation cycle (1,000 agents, 50 rounds):** At DeepSeek V3.2 pricing (~$0.27/M input tokens), a simulation cycle with 1,000 agents making 50 decisions each, at ~2K tokens per decision, costs roughly $27 in inference. At GPT-5.4 pricing, the same cycle costs ~$270. The routing strategy matters by an order of magnitude.

---

## Component 2: Self-model

A persistent, queryable data structure representing the system's self-knowledge. Updated after every validation cycle and bootstrap iteration.

**Grounding:** DeepMind's Cognitive Taxonomy (March 2026) identifies metacognition as one of the five cognitive faculties with the largest evaluation gap — meaning the field lacks standardized ways to measure it. Their proposed three-stage evaluation protocol (collect human baselines, map AI performance against distributions, generate normalized cognitive profiles) could be adopted for our self-model's capability scoring. Instead of just tracking "is prediction accuracy improving," we generate a cognitive profile showing where the system is human-level and where it's not, per domain.

### Sections

**Knowledge inventory**
- Domains indexed (list + coverage percentage per domain)
- Entity count and relationship density per subgraph
- Staleness score per subgraph (time since last data refresh)
- Known unknowns: explicit gap list with estimated impact on predictions

**Capability scores**
- Per-slot benchmark results (updated via probe tasks)
- Substrate → slot mapping (which substrate fills which slot)
- Confidence calibration curve (predicted confidence vs actual accuracy)
- Degraded mode frequency (how often fallbacks are triggered)
- Slot bottleneck ranking (which slot is the weakest link)
- *Cognitive profile: normalized scores against DeepMind's 10-faculty taxonomy, updated per validation cycle*

**Prediction track record**
- Marker accuracy by type (state transition, threshold, emergence, causal)
- Positional drift distribution (how far off in sim-token position)
- Causal chain fidelity score (did predicted causal chains hold)
- Confidence-vs-outcome calibration (is the system well-calibrated)
- Domain-specific hit rate

**Temporal perception state**
- Learned regime signatures per domain
- Current regime estimate per active simulation
- Causal density profile by domain and regime
- Prediction horizon confidence (how far forward can it see reliably)
- Temporal calibration error (predicted vs actual temporal dynamics)

**Resource state**
- Compute budget remaining
- API token spend rate (broken down by substrate: frontier vs cost-efficient)
- Storage utilization
- Substrate availability map (which substrates are online, current latency)

**Improvement queue**
- Ranked capability gaps (sorted by expected impact if resolved)
- Proposed actions per gap
- Expected impact estimate
- Resource cost per proposed action

### Meta-cognition loop

The meta-cognition slot queries the self-model after every validation cycle:
1. What is the highest-value gap?
2. What action would close it?
3. Does the action fit within resource and safety constraints?

Outputs: self-improve (execute the action), request resources (escalate to operator), or report (flag for human judgment).

---

## Component 3: Knowledge graph schema

Built on LightRAG with graph-structured indexing and dual-level retrieval. Extended with temporal signatures on edges.

**Grounding:** LightRAG (HKUDS, EMNLP 2025) uses a dual-level retrieval paradigm — low-level for specific entity lookups and high-level for thematic queries — with graph structures integrated into vector representations. It supports incremental updates without full re-indexing, which is critical for a simulation platform ingesting live data. LightRAG recommends LLMs with at least 32B parameters and 32K+ context for entity-relationship extraction during indexing. With March 2026 substrates, we can use 1M context models for indexing, dramatically improving extraction quality over entire documents rather than chunked fragments.

### Entity node

```
Entity {
  id: UUID
  type: enum (person, organization, event, asset, concept, ...)
  attributes: Map<string, TypedValue>
  state_vector: CurrentState        // latest known state
  state_history: StateTransition[]  // prior states with timestamps
  confidence: float                 // extraction confidence
  source_docs: Provenance[]         // where this entity was extracted from
  domain: DomainID
}
```

### Relationship edge

```
Relationship {
  id: UUID
  type: enum (causal, structural, temporal, associative, ...)
  source: EntityID
  target: EntityID
  strength: float (0-1)
  direction: enum (directed, bidirectional)
  valid_from: Timestamp | null
  valid_to: Timestamp | null
  confidence: float
  source_docs: Provenance[]
  temporal_signature: TemporalSignature  // THE KEY EXTENSION
}
```

### Temporal signature (per edge)

```
TemporalSignature {
  propagation_speed: Distribution     // how fast effects travel along this edge
  decay_rate: float                   // how quickly influence fades
  regime_sensitivity: Map<RegimeType, SpeedModifier>
                                      // how speed changes per regime
  latency_distribution: Histogram     // observed delay histogram from real data
  causal_density_profile: DensityFunction
                                      // events-per-sim-token by context state
  exposure_count: int                 // how many real-world observations
  last_calibrated: Timestamp          // when last validated against reality
}
```

### Domain context (per subgraph)

```
DomainContext {
  domain_id: string
  regime_state: RegimeEstimate        // current regime (calm, active, crisis, ...)
  base_temporal_rate: float           // learned baseline sim-tokens per calendar unit
  regime_signatures: LearnedPattern[] // patterns that signal regime transitions
  confidence: float                   // based on exposure_count across edges
}
```

### How temporal perception works

The simulation engine doesn't maintain a separate clock. It reads temporal signatures from the edges it traverses. When simulating a causal chain (Fed decision → USD movement → S&P impact), it reads each edge's propagation speed, adjusted for the current regime. In a calm regime, the chain might take 48 calendar hours. In a crisis, 30 minutes. The system discovers this through exposure to thousands of real-world event sequences — not through configuration.

Time is not an input to the system. Time is something the system learns to perceive. Through sufficient exposure to domain-specific event sequences, the system develops an internal temporal sense — not a mapping to time, but a model of time. The system learns when time accelerates, when it compresses, and when a single event warps the timeline for everything downstream. This is analogous to proper time in physics: the system's internal tick rate dilates and contracts based on the causal density of the environment it's modeling.

---

## Component 4: Environment specification

A pluggable definition that separates "what is being simulated" from "how the simulation engine works."

**Grounding:** OASIS (CAMEL-AI, November 2024) demonstrates this pattern for social media: modular components (Environment Server, Recommendation System, Time Engine, Agent Module) support up to one million agents with 23 action types. MiroFish (March 2026) extends OASIS with GraphRAG for knowledge grounding and Zep for persistent agent memory. Our architecture generalizes this pattern to arbitrary domains by making the environment definition pluggable.

**World model integration point:** LeCun's AMI Labs and DeepMind's Genie 3 model physical/spatial dynamics. Our architecture models social/behavioral/economic dynamics. These are complementary layers. If our framework can ingest world model outputs as environment dynamics (physics, spatial constraints), we get a multi-layer simulation: physical world model for environment physics + behavioral simulation for agent dynamics. This is a richer prediction surface than either alone, and represents a potential integration path as world model technology matures through 2026.

### Environment definition

```
EnvironmentSpec {
  domain_id: string
  
  state_schema: {
    entity_types: TypeDefinition[]        // what exists in this domain
    attribute_definitions: AttributeSpec[] // properties per type
    valid_transitions: TransitionRule[]    // legal state changes
    invariants: Constraint[]              // things that must always be true
    observable_vs_hidden: VisibilityMap   // what agents can vs can't see
  }
  
  action_space: {
    actions: ActionDefinition[]           // what agents can do
    preconditions: Map<ActionID, Predicate> // when actions are available
    effects: Map<ActionID, StateTransform>  // how actions change state
    costs: Map<ActionID, ResourceCost>      // what actions cost
    interaction_rules: InteractionSpec[]    // multi-agent action resolution
  }
  
  dynamics_model: {
    environment_physics: DynamicsRule[]    // non-agent state evolution
    exogenous_events: EventInjectionSpec  // external shocks
    feedback_loops: FeedbackSpec[]        // self-reinforcing dynamics
    stochastic_processes: NoiseModel[]    // randomness sources
    world_model_integration: WorldModelSpec | null
                                          // optional: ingest physical world model outputs
  }
  
  observation_function: {
    per_agent_type: Map<AgentType, ObservationFilter>
    information_asymmetry: AsymmetrySpec  // who sees what
    delay_model: ObservationDelay         // how fresh is observed data
  }
  
  outcome_signals: {
    marker_definitions: MarkerSpec[]      // what counts as a semantic marker
    measurable_outcomes: OutcomeMetric[]  // quantifiable results
  }
  
  validation_anchors: {
    ground_truth_sources: DataSource[]    // real-world data for comparison
    validation_protocol: ValidationSpec   // how to score predictions
  }
  
  gods_eye_surface: {
    injection_points: InjectionSpec[]     // where operator can intervene
    variable_controls: ControlSpec[]      // what can be tweaked mid-sim
  }
}
```

### Example instantiations

**Social media** (OASIS-derived): 23 action types (follow, post, comment, repost, like, mute, search...), recommendation-based observation function, virality and polarization as outcome signals. *Directly buildable today using OASIS/MiroFish as the starting point.*

**Financial markets**: ~17 action types (buy, sell, hedge, lever, deleverage...), order book dynamics model, information asymmetry between retail and institutional agents, price movement and volume as outcome signals. *GPT-5.4's strong performance on finance benchmarks (APEX-Agents lead) makes this a high-viability first domain.*

**Geopolitics**: ~12 action types (sanction, negotiate, ally, posture, escalate...), alliance network dynamics, intelligence asymmetry, policy outcomes as markers.

**Supply chain**: ~15 action types (order, ship, stockpile, reroute, substitute...), logistics physics, demand signal propagation, delivery and cost as outcome signals.

### Self-build capability

The agentic layer can generate new environment specs by: (1) analyzing a domain corpus through LightRAG to extract entity types and relationship patterns, (2) inferring action spaces from observed behaviors in the corpus, (3) composing these into a valid EnvironmentSpec, (4) validating against real-world data. This requires operator approval at the gate step.

**Grounding:** GPT-5.4's native computer-use capabilities and tool search system — which allows models to look up tool definitions as needed rather than preloading all definitions — directly enable this self-build pattern. The model can autonomously navigate data sources, extract schemas, and generate code, all within a NemoClaw sandbox.

---

## Component 5: Token-native prediction model

### Sim-token stream

The simulation produces a sequential stream of structured state transitions. Each step is a sim-token — a discrete unit of simulation state.

### Semantic markers

Checkpoints in the sim-token stream that encode testable state transitions:

| Marker type | Definition | Example |
|-------------|-----------|---------|
| **State transition** | Entity X moved from state A → B | "Company X went from profitable to loss-making" |
| **Threshold** | Metric M crossed boundary V | "Volatility index exceeded 30" |
| **Emergence** | New pattern P detected in agent population | "Coalition formed among agents 12, 45, 67" |
| **Causal** | Event E caused by chain C₁ → C₂ → ... | "Price drop caused by supply shock → panic selling" |

### Prediction protocol

1. Run simulation forward for N sim-tokens from current grounded state
2. Extract predicted markers (type, position in stream, content)
3. When real-world time elapses, extract actual markers from ground truth data
4. Score: marker type accuracy, positional drift (how many sim-tokens off), causal chain fidelity

### Temporal mapping

Calendar time is a *learned output*, not an input. The system discovers: given the current domain context and regime state, how many sim-tokens correspond to a calendar unit? This ratio is itself a prediction that gets validated and refined. Through sufficient exposure to domain-specific event sequences, the system develops an internal temporal sense. It doesn't consult a lookup table — it perceives how fast events propagate in the current regime, the way a trader develops intuition for when a market is about to break.

---

## Component 6: Capability bootstrapping loop

The self-improvement protocol. Each cycle can expand the system's capabilities, not just its accuracy.

**Grounding:** DeepMind's Cognitive Taxonomy separately identifies "learning" as a core faculty — the ability to acquire new knowledge through experience and instruction. Our bootstrap loop is the architectural implementation of this faculty. The research community also recognizes self-improving agent loops as a key 2026 trend: "Benchmark Test-Time Scaling of General LLM Agents" (February 2026) frames agent competence partly as a test-time compute/scaling problem, and "Large Language Models Can Self-Improve at Web Agent Tasks" demonstrates that synthetic self-improvement loops can materially improve agent performance.

**The Karpathy Loop as execution primitive.** Andrej Karpathy's autoresearch (March 7, 2026) provides the proven execution pattern for steps 4-5 of this loop. The pattern: expose a scriptable asset (the thing being optimized), define a scalar metric (how you measure improvement), enforce a fixed time budget (how long each experiment runs), and let an agent autonomously hypothesize, modify, run, evaluate, and commit/discard — ~100 experiments per night on a single GPU. Karpathy's `program.md` format — a single Markdown document carrying instructions, constraints, and stopping criteria simultaneously — is the instruction format for each bootstrap cycle. The meta-cognition slot writes the `program.md` (defining what to optimize, what not to touch, and when to stop); the generation slot executes the autoresearch loop against it.

The Karpathy Loop generalizes beyond ML training to any surface in our architecture that has a scriptable asset and a measurable outcome:

| Optimization surface | Scriptable asset | Scalar metric | Time budget |
|----------------------|-----------------|---------------|-------------|
| Environment dynamics tuning | Dynamics config parameters | Prediction accuracy vs historical data | N simulation cycles |
| Temporal signature calibration | Edge propagation speed, decay, regime sensitivity | Temporal calibration error | N event sequence replays |
| Agent persona refinement | Persona templates, behavior weights | Behavioral fidelity vs real-world agent data | N agent interaction rounds |
| Validation scoring function | Scoring function code | Correlation with expert human judgments | N scored prediction batches |
| Substrate capability assessment | Benchmark probe tasks | Multi-dimensional capability score | Fixed eval budget per slot |
| Data pipeline optimization | Ingestion scripts, entity extraction prompts | Knowledge graph coverage + accuracy | N ingestion runs |

Each of these surfaces can run an autoresearch-style loop independently, overnight, without human involvement. The self-model tracks which surfaces have been optimized recently and which are stale, prioritizing accordingly.

### Steps

1. **Diagnose** — Meta-cognition queries self-model for highest-value gap. Triggered automatically after every validation cycle.

2. **Plan** — Reasoning slot generates a concrete improvement plan: new data pipeline, modified agent template, new environment dynamics rule, updated temporal signature. Includes expected resource cost and predicted impact. *The plan output includes a `program.md`-format document specifying the autoresearch loop parameters: what asset to modify, what metric to optimize, what constraints to preserve, and when to stop.*

3. **Gate** — Safety and resource check. Low-risk improvements (temporal signature updates, data source additions) execute automatically. High-impact changes (new environment specs, agent behavior modifications, domain expansion) require operator approval. *Grounded: NemoClaw's out-of-process policy enforcement provides the security infrastructure for this gate. Policies run in a separate trust boundary that the agent process cannot modify, even if compromised. The privacy router ensures sensitive domain data stays on local Nemotron models during self-build operations.*

4. **Execute (Karpathy Loop)** — The generation slot runs an autoresearch-style loop: read the `program.md`, form a hypothesis, modify the scriptable asset, run a time-boxed evaluation, score against the scalar metric, commit or discard, repeat. Agentic layer (OpenClaw/NemoClaw) provides the sandboxed environment. Each experiment is a git commit, creating a full audit trail. *Grounded: NanoClaw's hypervisor-level container isolation means each experiment executes in its own micro VM. GPT-5.4's native computer-use capabilities allow the agent to write code, test it, and iterate — all within the sandbox. Karpathy demonstrated ~12 experiments/hour, ~100/night on a single GPU.*

5. **Validate** — Run prediction cycle with the best result from the autoresearch loop. A/B compare against previous production cycle. Did marker accuracy improve? Did prediction horizon extend? If below threshold, roll back the entire loop's output.

6. **Integrate** — If validated, promote to production. Update self-model: capability scores adjust, knowledge inventory refreshes, improvement queue re-ranks. The `program.md` and experiment history are archived as institutional knowledge — future bootstrap cycles can reference what was tried and what worked.

### The AGI gradient

As the LLM substrate improves, every step gets better:
- Diagnosis becomes more precise (identifies structural gaps, not just data gaps)
- Plans become more creative (proposes novel environment dynamics, not just more data)
- Generated artifacts become higher quality (better code, tighter configs)
- Validation becomes more rigorous (catches subtler failure modes)

The loop's output quality is a function of substrate capability. The harness doesn't change — but its behavior qualitatively shifts as the substrate crosses capability thresholds.

**Concrete example of the AGI gradient:** With GPT-4-class substrates (2024), the bootstrap loop could identify "I need more data on sector X" and generate a data pipeline. With GPT-5.4-class substrates (March 2026), the same loop can identify "my environment spec for this domain is missing a feedback loop between entities A and B — that's why my causal chains keep breaking at step 7" and generate a modified environment dynamics rule. Same harness, same loop, qualitatively different capability.

---

## Technology stack mapping — grounded in March 2026

| Component | Primary technology | Current status (March 2026) | Role |
|-----------|-------------------|----------------------------|------|
| Knowledge engine | LightRAG | Stable, EMNLP 2025, active development, PyPI package available | Graph-structured indexing, dual-level retrieval, incremental updates |
| Simulation backbone | OASIS-derived | v1.0+ on PyPI, peer-reviewed, 1M agent scale validated | Time engine, agent module, environment server, recommendation/routing |
| Prediction reference | MiroFish patterns | Trending on GitHub March 2026, active community, offline fork available | Seed data → agent spawning → emergent behavior → prediction reports |
| Agentic execution | OpenClaw / NemoClaw | OpenClaw: fastest-growing OSS project ever. NemoClaw: early alpha, announced GTC 2026 | Self-build, tool orchestration, sandboxed code execution |
| Security isolation | NemoClaw + NanoClaw | NemoClaw: early preview. NanoClaw: stable, macOS + Windows, Linux coming | Kernel-level sandboxing, policy enforcement, privacy routing |
| Substrate interface | Custom | To be built — primary novel engineering work | Capability slots, contract shapes, routing, benchmarking |
| Self-model | Custom | To be built — primary novel engineering work | Persistent state, queryable, drives meta-cognition loop |
| Agent memory | DeepSeek Engram pattern | Paper published Jan 2026, V4 integration expected April 2026 | Separation of static knowledge retrieval from dynamic reasoning in agent personas |
| Bootstrap execution | Karpathy autoresearch pattern | Released March 7, 2026, MIT license, proven at scale (Shopify: 19% gain overnight) | Autonomous experiment loop: scriptable asset + scalar metric + time-boxed eval + `program.md` instruction format |

---

## Positioning in the research landscape

### What already exists (we build on top of)
- Multi-agent simulation at scale (OASIS: 1M agents, 23 actions, validated)
- Graph-enhanced RAG with entity-relationship indexing (LightRAG: dual-level retrieval)
- Prediction through emergent agent behavior (MiroFish: seed data → simulation → prediction reports)
- Secure agentic execution (NemoClaw: kernel-level sandboxing, privacy routing)
- Autonomous research loops (Karpathy autoresearch: agent-driven hypothesis → experiment → evaluation at ~100 experiments/night)
- Cognitive taxonomy for measuring AGI progress (DeepMind: 10 faculties, March 2026)
- World models for physical environment simulation (Genie 3, Marble, AMI Labs)

### What doesn't exist yet (our contribution)
- **Unified composition** of knowledge graph + multi-agent simulation + agentic self-build + cognitive self-model into a single architecture
- **Temporal signatures on knowledge graph edges** — learned propagation speeds and regime sensitivity per relationship type
- **Learned temporal perception** — the system developing an internal sense of how time moves in a domain, rather than using static temporal mappings
- **Token-native prediction with semantic markers** — predicting in sim-tokens with typed checkpoints rather than calendar-time forecasts
- **Substrate-independent capability routing** — dynamic assignment of frontier vs cost-efficient models to different cognitive faculties based on task requirements
- **Cognitive self-model driving a bootstrap loop** — the system using its own metacognitive assessment to identify and close capability gaps, with the loop's quality scaling with substrate capability
- **Generalized Karpathy Loop across optimization surfaces** — applying the autoresearch pattern not just to ML training but to environment dynamics, temporal signatures, agent personas, validation functions, and capability assessment within a cognitive architecture
- **Domain-agnostic environment specification** — a pluggable contract that generalizes OASIS's social media environment to arbitrary domains (financial, geopolitical, supply chain)

### Adjacent work to monitor
- **DeepSeek V4 Engram** (expected April 2026): conditional memory architecture separating static retrieval from dynamic reasoning — directly applicable to agent persona memory
- **DeepMind Cognitive Taxonomy hackathon** (through April 16, 2026): community-built benchmarks for learning, metacognition, attention, executive functions, social cognition — evaluation tools we can adopt
- **AMI Labs** (LeCun, 2026): physical world models as complementary layer to our behavioral simulation
- **AMA-Bench** (February 2026): benchmark for long-horizon agent memory in real agentic applications — validation methodology for our agent persistence
- **CitySim** (2025): LLM-driven urban simulation with beliefs, goals, and memory — domain-specific instantiation that validates our environment spec pattern

---

## Open questions for further formalization

1. **Agent persona architecture**: How are agent personas generated from the knowledge graph? How do they maintain long-term memory across simulation rounds? DeepSeek's Engram pattern (static knowledge vs dynamic reasoning) is directly applicable here. What is the memory schema? How does it interact with the OASIS agent module?

2. **Multi-domain simulation**: Can the system run simulations across multiple domains simultaneously (e.g., geopolitics affecting financial markets)? How do cross-domain causal edges work? What are the computational costs of maintaining multiple environment specs in a single simulation?

3. **World model integration**: How does the architecture ingest physical world model outputs (Genie 3, Marble) as environment dynamics? What is the interface between spatial/physical simulation and behavioral/social simulation?

4. **Adversarial validation**: Should the system generate adversarial scenarios to stress-test its own predictions? How does this integrate with the bootstrap loop?

5. **Human-in-the-loop protocols**: Beyond the gate step, when should the system actively seek human input? How does it represent human knowledge that can't be extracted from data?

6. **Scaling protocol**: When the system identifies it needs more compute, what is the formal resource request specification? How does it estimate ROI on additional resources?

7. **Substrate transition protocol**: When a new, significantly better model becomes available (e.g., DeepSeek V4 dropping, or a future GPT-6), what is the migration procedure? How does the system re-benchmark across all slots and adjust routing?

8. **Evaluation framework**: Should we adopt DeepMind's three-stage evaluation protocol (human baselines → AI performance mapping → normalized cognitive profiles) for our validation loop? How do cognitive profiles inform the bootstrap loop's prioritization of capability gaps?

9. **DeepMind taxonomy alignment**: Should we expand from 6 capability slots to explicitly address all 10 DeepMind faculties? Specifically, should Learning (in-context adaptation during simulation) and Memory (working memory within a simulation run) become first-class slots?

10. **Autoresearch-driven capability assessment**: Instead of static benchmarks, should substrate capability scoring use the Karpathy Loop — giving an agent a capability probe task, a metric, and a time budget, and letting it discover the substrate's actual performance envelope through autonomous exploration? This would produce richer capability profiles (where does the substrate excel, where does it break, what's the shape of the performance curve) than single-point benchmark scores.

11. **Program.md authoring and evolution**: The quality of each bootstrap cycle is bounded by the quality of its `program.md`. Should the meta-cognition slot learn to write better `program.md` files over time, treating the instruction format itself as a skill that improves? Karpathy noted that the `program.md` git history is as valuable as the `train.py` git history — the system should archive and learn from its own experimental design decisions.

---

*Document version: 2.1 — Grounded in March 2026 landscape, autoresearch pattern integrated*
*Last updated: March 23, 2026*
