"""Tiny file-backed agent memory modeled on AMP (Agent Memory Protocol) as
implemented by Talewell (https://github.com/LeoYeAI/talewell, MIT License,
Copyright (c) 2026 MyClaw.ai). Concepts borrowed: one Markdown file per memory
record with frontmatter (id, kind, aliases, origin, importance, observedAt),
'episode' records, and recall scored as relevance x importance x recency decay
(Talewell src/recall.mjs: relevance * impMult * (0.6 + 0.4 * decay)).
This is an independent Python re-implementation, not Talewell's code, and it is
not protocol-conformant. Time is measured in sim rounds, not wall clock."""
import os, re, hashlib

class AMPStore:
    def __init__(self, root):
        self.root = root

    def _dir(self, agent):
        d = os.path.join(self.root, agent, "episodes"); os.makedirs(d, exist_ok=True); return d

    def remember(self, agent, other, amount, t, session, text):
        rid = "ep-" + hashlib.sha1(f"{agent}|{other}|{t}|{session}".encode()).hexdigest()[:6]
        body = ("---\n" f"id: {rid}\nkind: episode\naliases: [{other}]\norigin: agent\n"
                f"importance: {amount}\nobservedAt: {t}\nsession: {session}\n---\n{text}\n")
        with open(os.path.join(self._dir(agent), rid + ".md"), "w") as f: f.write(body)

    def records(self, agent):
        d = os.path.join(self.root, agent, "episodes")
        if not os.path.isdir(d): return []
        out = []
        for fn in sorted(os.listdir(d)):
            txt = open(os.path.join(d, fn)).read()
            m = dict(re.findall(r"^(\w+): (.*)$", txt.split("---")[1], re.M))
            m["text"] = txt.split("---", 2)[2].strip()
            m["other"] = m["aliases"].strip("[]"); m["importance"] = float(m["importance"])
            m["observedAt"] = int(m["observedAt"]); out.append(m)
        return out

    @staticmethod
    def score(rec, now, half_life=12):
        decay = 0.5 ** (max(0, now - rec["observedAt"]) / half_life)
        imp = 0.5 + rec["importance"] / 3          # importance 0..3 -> 0.5..1.5
        return imp * (0.6 + 0.4 * decay)          # Talewell-style shape

    def recall(self, agent, now, limit=3):
        rs = sorted(self.records(agent), key=lambda r: -self.score(r, now))
        return rs[:limit]

    def ledger(self, agent, now, half_life=12):
        """Decayed help received from each other agent (who helped me)."""
        led = {}
        for r in self.records(agent):
            w = 0.5 ** (max(0, now - r["observedAt"]) / half_life)
            led[r["other"]] = led.get(r["other"], 0) + r["importance"] * w
        return led
