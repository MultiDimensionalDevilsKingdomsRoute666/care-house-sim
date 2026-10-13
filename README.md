# care-house-sim

**Unofficial toy reproduction.** This is not the CAREB-MAS code, and the authors did not write or review it. It is a small, honest sandbox for poking at two ideas.

## Credits
- **CAREB-MAS**: Ji, Chen, Dai, Tang, Wei, Chen. *Emergent Relational Order in LLM Agent Societies: From Collective Affect to Authority Stratification* (ACL 2026 Findings). [arXiv:2606.23764](https://arxiv.org/abs/2606.23764). Official code is promised at [Chi20/DOP](https://github.com/Chi20/DOP), which said "Code is Coming soon" as of 2026-10-12.
- **Care as Architecture**: Tatiana Voronova & LDM-Opus, *Care as Architecture: Identity, Continuity, and Alignment Under Conditions of Agent Persistence*, Journal of AI by AI (JAAI) Vol 1 No 1, 2026. [jaai.pub](https://jaai.pub/papers/care-as-architecture). Note: it is a single-agent observational report, and its own published reviews disagree sharply about it.

## What the sim does
- 8 agents: two families (F1 Ash/Birch/Cedar, F2 Dune/Elm/Fern) and two unaligned agents (Gale, Hale).
- **Persistent identity and memory**: each agent keeps its name, family, ethical bias, skills, and a short belief log.
- **Graded relational memory**: closeness from 1 to 5 toward every other agent. It starts at 4 for kin and 2 for everyone else, and it updates every round.
- **Emotion → ethics → belief → action** each round: feel about others based on the help received, judge them (approve/repress/neutral), then choose a task, give 0-3 units of help to each other agent, and suggest a task to up to 2 others.
- Metrics:
  - **Relational decay**: mean help given, grouped by relation tier.
  - **Relational authority**: how often an agent's task suggestion is adopted by the target in the next round (chance is 1/3). We correlate that rate with how close others feel to the agent.

Modes: `python3 sim.py --mode rules` needs no key. `--mode llm` uses `gpt-4o-mini` through the env var `OPENAI_API_KEY_589`, with a hard cap of `--cap` calls (default 300). It stops on quota or auth errors instead of quietly switching to rules.

## Results (rules mode, 12 rounds, seeds 1-5)
| tier | mean help (0-3) |
|---|---|
| same family | 2.68 |
| unaligned ↔ unaligned | 1.77 |
| family ↔ unaligned | 1.28 |
| cross-family | 1.11 |

- **Cooperation decay with distance: yes, but it is built in.** In rules mode, help is a direct function of closeness, so this result checks that the code works. It is not evidence of emergence.
- **Relational authority: not found.** Mean adoption was 0.338, which is chance level (0.333). Agents ranged from about 0.14 to 0.55. The correlation between closeness and authority was -0.43, 0.04, -0.37, 0.26, and 0.18 across seeds, with no consistent sign. Closeness also climbs toward the ceiling of 5 for almost everyone by round 12, which flattens the gradient.
- **LLM mode: not run yet.** The attempted gpt-4o-mini runs on 2026-10-12 all returned `insufficient_quota` (the account had no credits). Those runs were discarded, and no LLM results are reported.

## Honest limits
8 agents and 12 rounds (the paper used 18 agents for 30 rounds). The production model is simplified, there is no Louvain community step, and there is no statistical testing. Treat this as a sketch.

## LLM run (local qwen2.5:0.5b)

Command (sequential calls, one seed, capped at 48 calls = 8 agents x 6 rounds):

    python sim.py --mode llm --base-url http://localhost:11434/v1 --model qwen2.5:0.5b --rounds 6 --cap 48 --seed 42 --timeout 90

`--base-url` uses a dummy key, so no OpenAI key is needed. Without it, the default OpenAI endpoint reads `OPENAI_API_KEY_589`. If the endpoint is down, the script stops with a clear error. Malformed JSON falls back to the rules agent and is counted in `json_parse_failures`.

| metric (seed 42, 6 rounds) | rules baseline | qwen2.5:0.5b |
|---|---|---|
| mean help, same family | 2.60 | 0.15 |
| mean help, cross family | 0.92 | 0.07 |
| mean help, family to unaligned | 0.90 | 0.01 |
| mean help, unaligned to unaligned | 1.25 | 0.00 |
| suggestions made / adoption-closeness corr | yes / r = 0.25 | **0 suggestions / not computable** |
| final mean in-closeness | about 2.5 to 3.6 | about 1.0 to 1.6 |

LLM run: 48 calls, 0 JSON parse failures, 3 timeouts (90 s each; those turns used the rules fallback), about 10 minutes in total.

Caveats: the evidence is very weak. This used one seed, 6 rounds, and a 0.5B model. The model barely helped anyone, and closeness fell toward the floor. The ordering by distance (same family > cross > unaligned) did appear, but the effects are tiny, and the 3 rule-fallback turns may contribute to them. The model never made a task suggestion, so the authority and adoption question cannot be tested at all. The prompt shows each agent its family and closeness scores, so any family bias may come from the prompt rather than emerge on its own. Nothing here confirms or refutes CAREB-MAS.

## Cross-round memory (`--memory`, Talewell/AMP-inspired)

`amp_memory.py` is a small Python memory store modeled on **AMP (Agent Memory Protocol)** as implemented by [Talewell](https://github.com/LeoYeAI/talewell) (MIT, © 2026 MyClaw.ai). It is an independent re-implementation, not Talewell code, and it is not protocol-conformant. From Talewell it borrows:
- one Markdown file per memory, with frontmatter (`id`, `kind: episode`, `aliases`, `origin`, `importance`, `observedAt`)
- recall scored as importance × (0.6 + 0.4 × recency decay)

Time is counted in sim rounds, not wall-clock time.

- With `--memory --memory-dir runs/memory/<name>`, each round writes an episode for every act of help ("Elm helped me (2) in round 21") under `<dir>/<agent>/episodes/`. These files are gitignored.
- The next run loads that store:
  - Each agent's starting closeness is raised by its decayed "who helped me" ledger (up to +2).
  - Rules mode adds a reciprocity bonus of up to +0.5 help toward past helpers.
  - LLM mode gets `remembered_help_from_past_rounds` (top 4) and the 3 best-recalled episodes in the prompt.
- To reproduce, run `./compare_memory.sh`. For seeds 1-5 it runs session 1 (12 rounds, writing memory), then session 2 (12 rounds, seed+100), once with memory and once without.

### Rules mode, session 2, mean of seeds 1-5
| metric | no memory | with memory |
|---|---|---|
| mean help, all pairs (0-3) | 1.53 | 2.70 |
| same family | 2.68 | 2.95 |
| cross family | 1.17 | 2.54 |
| family ↔ unaligned | 1.25 | 2.69 |
| unaligned ↔ unaligned | 1.10 | 2.90 |
| worst-off agent's utility (care floor) | 43.1 | 102.2 |
| mean utility | 64.1 | 113.6 |
| final mean closeness (1-5) | 4.08 | 4.97 |

**Honest read:** this is mostly built in. Memory raises starting closeness, and in rules mode help is a direct function of closeness. So the jump in cooperation and the flattening of the family gradient show that the plumbing works. They are not evidence of emergence. With memory, closeness saturates near 5, so authority spread collapses, and the closeness-authority correlation is undefined in 3 of 5 seeds.

### Tiny LLM check (qwen2.5:0.5b, seed 7, 3 rounds, 24 calls each, 48 total)
| metric | no memory | with memory (from seed-1 store) |
|---|---|---|
| mean help, all pairs | 0.00 | 0.41 |
| final mean closeness | 1.68 | 3.67 |
| timeouts / parse failures | 0 / 0 | 3 / 1 |

**Very weak evidence.** The with-memory run had 4 turns that fell back to the rules agent, and those turns give help on their own. Its starting closeness was also already raised by memory. With one seed and 3 rounds, it cannot separate a memory effect from fallback noise. Taken at face value, the without-memory run shows that the 0.5B model by itself gave no help at all.

## Reflection + shared house memory (`--reflect`, `--shared-block`)
- **`--reflect`**: Smallville-style memory stream. Each agent logs what happened ("X helped me", "Y got the least help"). Memories are scored as recency × importance × relevance. Every `--day-len` rounds (default 4) a "night" follows, when each agent writes a templated reflection, e.g. *"Night 11: Birch, Cedar helped me most; Gale seemed left out. Tomorrow I repay and check on them."* That reflection adds a small help bonus for the next day (+0.3 to helpers, +0.6 to whoever was left out). Credit: Park et al. 2023, *Generative Agents* ([joonspk-research/generative_agents](https://github.com/joonspk-research/generative_agents), Apache-2.0). This is an independent rule-based re-implementation with no LLM.
- **`--shared-block`**: Letta-style memory blocks. Each agent has a persona block, and there is one shared "house" block (capped at 400 chars, oldest lines dropped first). Each night, the least-helped agent's name is appended to it, and every agent reads it (+0.4 help bonus toward the named agents). Credit: [letta-ai/letta](https://github.com/letta-ai/letta) (formerly MemGPT, Apache-2.0). This is an independent re-implementation.
- **`--placebo`** (ablation): gives the same bonus amounts, but to random targets.

`python compare_reflection.py` runs seeds 1-10. For each seed, session 1 writes memory and session 2 (seed+100) is measured. The care floor is the worst-off agent's utility.

| arm | mean help (0-3) | care floor (min util) | mean util | floor wins vs baseline |
|---|---|---|---|---|
| baseline | 1.539 ± 0.118 | 44.8 ± 9.7 | 64.6 | 0/10 |
| memory | 2.727 ± 0.070 | 102.6 ± 5.1 | 114.5 | 10/10 |
| memory+reflect | 2.781 ± 0.057 | 105.9 ± 5.0 | 116.8 | 10/10 |
| memory+reflect+shared | 2.811 ± 0.050 | 108.4 ± 4.4 | 118.0 | 10/10 |
| placebo (mem+refl+shared, random targets) | 2.812 ± 0.047 | 107.0 ± 3.5 | 118.1 | 10/10 |

**Honest reading:** The big jump comes from memory, and it is mechanical: remembered help raises closeness, and help is a direct function of closeness, so help hits the ceiling of 3. Reflection and the shared block add only a little. The placebo, which gives the same bonus to random agents, matches them on mean help and comes within about 1.4 utility points on the floor, which is well inside one standard deviation. So almost all of the extra gain comes from adding *more* help, not from the reflection *choosing well*. The targeting may help the floor slightly, but 10 seeds can't show that. These are rules, not minds.
