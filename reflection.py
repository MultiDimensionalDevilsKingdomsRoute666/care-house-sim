"""Rule-based reflection + shared house memory for care-house-sim. No LLM calls.

1) Smallville-style memory stream and nightly reflection. Inspired by Park et al.
   2023, "Generative Agents: Interactive Simulacra of Human Behavior"
   (joonspk-research/generative_agents, Apache-2.0). Retrieval score =
   recency x importance x relevance; at each sim 'night' the top memories are
   turned into a short templated reflection that biases the next day's help.
   Independent re-implementation of the idea, not their code; reflections are
   templates, not LLM output.
2) Letta-style memory blocks. Inspired by letta-ai/letta (formerly MemGPT,
   Apache-2.0): a size-capped shared 'house' block every agent can read and
   append to, plus a per-agent 'persona' block. Independent re-implementation.
"""
import random

class MemoryStream:
    def __init__(self, decay=0.9):
        self.items, self.decay = [], decay       # each: dict(t, kind, about, importance, text)

    def add(self, t, kind, about, importance, text):
        self.items.append(dict(t=t, kind=kind, about=about, importance=importance, text=text))

    def score(self, m, now, query):
        recency = self.decay ** max(0, now - m["t"])
        importance = m["importance"] / 3.0
        relevance = 1.0 if m["kind"] in query else 0.3   # keyword relevance to the night's question
        return recency * importance * relevance

    def retrieve(self, now, query, k=4):
        return sorted(self.items, key=lambda m: -self.score(m, now, query))[:k]

class Block:
    """Letta-style labelled text block with a hard character cap (oldest lines drop first)."""
    def __init__(self, label, limit):
        self.label, self.limit, self.lines = label, limit, []
    def append(self, line):
        self.lines.append(line)
        while len(self.value()) > self.limit and len(self.lines) > 1: self.lines.pop(0)
    def value(self): return "\n".join(self.lines)

def persona_block(a):
    b = Block("persona", 200)
    b.append(f"I am {a['name']}, family {a['fam'] or 'none'}. I try to repay help and notice who is left out.")
    return b

def night(ags, day_received, now, reflect=True, shared=None, placebo_rng=None):
    """Run one 'night'. day_received[n] = total help n received today.
    Writes reflections, sets a['bias_next'] (help bonus per other agent for tomorrow)."""
    needy = min(day_received, key=lambda n: (day_received[n], n))
    if shared is not None:   # appended by the first agent (alphabetical) who noticed; all agents then read it
        shared.append(f"{sorted(ags)[0]} noted night {now} least-helped: {needy} (got {day_received[needy]})")
    for n, a in ags.items():
        a["bias_next"] = {}
        if reflect:
            top = a["stream"].retrieve(now, query=("received", "low_help"), k=6)
            helpers = [m["about"] for m in top if m["kind"] == "received"][:2]
            lows = [m["about"] for m in top if m["kind"] == "low_help" and m["about"] != n][:1]
            text = (f"Night {now}: {', '.join(helpers) or 'no one'} helped me most; "
                    f"{', '.join(lows) or 'no one'} seemed left out. Tomorrow I repay and check on them.")
            a["reflections"].append(text)
            a["stream"].add(now, "reflection", None, 2, text)
            for o in helpers: a["bias_next"][o] = a["bias_next"].get(o, 0) + 0.3
            for o in lows: a["bias_next"][o] = a["bias_next"].get(o, 0) + 0.6
        if shared is not None:
            for line in shared.lines:          # every agent reads the shared house block
                o = line.split(":", 1)[1].split()[0] if ":" in line else None
                if o in a["close"]: a["bias_next"][o] = a["bias_next"].get(o, 0) + 0.4
        if placebo_rng is not None and a["bias_next"]:   # ablation: same total bonus, random targets
            tot = list(a["bias_next"].values()); others = list(a["close"])
            a["bias_next"] = {}
            for v in tot:
                o = placebo_rng.choice(others); a["bias_next"][o] = a["bias_next"].get(o, 0) + v
