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
