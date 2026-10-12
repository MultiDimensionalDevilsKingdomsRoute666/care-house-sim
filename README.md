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
