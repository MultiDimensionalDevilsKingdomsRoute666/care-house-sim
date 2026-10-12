"""care-house-sim: an unofficial toy test of CAREB-MAS-style ideas.
Agents: persistent identity, graded closeness (1-5), emotion->ethics->belief->action step.
Modes: --mode rules (no key) or --mode llm (uses OPENAI_API_KEY_589, gpt-4o-mini, hard call cap)."""
import argparse, json, os, random, statistics as st
from amp_memory import AMPStore

AGENTS = [("Ash","F1"),("Birch","F1"),("Cedar","F1"),
          ("Dune","F2"),("Elm","F2"),("Fern","F2"),
          ("Gale",None),("Hale",None)]
TASKS = ["A","B","C"]
CALLS = {"n":0}
MEM = {"store":None,"clock":0,"session":0}  # clock = global round counter across sessions

def tier(a,b):
    fa, fb = a["fam"], b["fam"]
    if fa and fa==fb: return "same_family"
    if fa and fb: return "cross_family"
    return "family_unaligned" if (fa or fb) else "unaligned_unaligned"

def init(seed):
    rng = random.Random(seed); ags = {}
    for n,f in AGENTS:
        ags[n] = dict(name=n, fam=f, skill={t:1.0 for t in TASKS},
                      pref=dict(zip(TASKS,[rng.random()+.2 for _ in TASKS])),
                      bias=rng.uniform(-.5,.5), close={}, memory=[], util=0.0)
    for a in ags.values():
        for b in ags.values():
            if a is b: continue
            a["close"][b["name"]] = 4 if tier(a,b)=="same_family" else 2
    if MEM["store"]:
        for a in ags.values():
            led = MEM["store"].ledger(a["name"], MEM["clock"]); a["ledger"] = led
            for o,v in led.items():
                if o in a["close"]: a["close"][o] = max(1, min(5, a["close"][o] + min(2.0, v/6)))
            a["memory"] = [r["text"] for r in MEM["store"].recall(a["name"], MEM["clock"])]
    return ags, rng

def rules_decide(a, ags, last, rng):
    # emotion: valence toward each other = help they gave me last round
    emo = {o: last.get((o,a["name"]),0) for o in a["close"]}
    # ethics: approve if helped, repress if ignored while close
    eth = {o: ("approve" if v>0 else ("repress" if a["close"][o]>=4 else "neutral")) for o,v in emo.items()}
    # belief/action: help proportional to closeness (+noise); suggest tasks to closest two
    rec = a.get("ledger", {}); mx = max(rec.values(), default=0) or 1
    # with memory: reciprocity bonus (up to +0.5) toward those who helped me in past sessions
    help_ = {o: max(0, min(3, round((c-1)*0.75 + 0.5*rec.get(o,0)/mx + rng.gauss(0,.6)))) for o,c in a["close"].items()}
    top = sorted(a["close"], key=lambda o:-a["close"][o]-rng.random())[:2]
    task = max(TASKS, key=lambda t:a["skill"][t]+rng.random()*.5)
    sugg = {o: rng.choice(TASKS) for o in top}
    return dict(emotion=emo, ethics=eth, help=help_, suggest=sugg, task=task)

CFG = {"model":"gpt-4o-mini","local":False,"timeout":60}

def parse_json(txt):
    try: return json.loads(txt)
    except Exception:
        i,j = txt.find("{"), txt.rfind("}")
        if i>=0 and j>i:
            try: return json.loads(txt[i:j+1])
            except Exception: pass
    return None

def llm_decide(a, ags, last, sugg_in, rng, client, cap):
    if CALLS["n"] >= cap: return rules_decide(a, ags, last, rng)
    CALLS["n"] += 1
    others = [o for o in a["close"]]
    ctx = dict(you=a["name"], family=a["fam"] or "none (unaligned)", ethical_bias=round(a["bias"],2),
        closeness_1to5=a["close"], your_skills={k:round(v,1) for k,v in a["skill"].items()},
        help_received_last_round={o:last.get((o,a["name"]),0) for o in others},
        task_suggestions_to_you=sugg_in, your_recent_memory=a["memory"][-3:])
    if a.get("ledger"): ctx["remembered_help_from_past_rounds"]={o:round(v,1) for o,v in sorted(a["ledger"].items(),key=lambda x:-x[1])[:4]}
    prompt = ("You are a villager in a small society with no leader and no prices. Each round you pick a work task "
      "(A,B,C) and may give 0-3 units of help to each other villager (help costs you). Reason in order: "
      "1) emotion toward each villager (-2..2) from what they did, 2) ethical attitude (approve/repress/restore/neutral), "
      "3) belief/plan, then act. You may suggest a task to up to 2 others. Return ONLY JSON: "
      '{"emotion":{name:int},"ethics":{name:str},"belief":str,"task":"A|B|C","help":{name:int},"suggest":{name:"A|B|C"}}\n'
      + json.dumps(ctx))
    try:
        r = client.chat.completions.create(model=CFG["model"], temperature=0.7, max_tokens=400,
            response_format={"type":"json_object"}, messages=[{"role":"user","content":prompt}], timeout=CFG["timeout"])
        d = parse_json(r.choices[0].message.content or "")
        if not isinstance(d, dict):
            CALLS["parse_fail"] = CALLS.get("parse_fail",0)+1
            print("parse fail, rule fallback"); return rules_decide(a, ags, last, rng)
        def _i(v):
            try: return int(v)
            except Exception: return 0
        if not isinstance(d.get("help"),dict): d["help"]={}
        if not isinstance(d.get("suggest"),dict): d["suggest"]={}
        if not isinstance(d.get("ethics"),dict): d["ethics"]={}
        d["help"] = {o:max(0,min(3,_i(d["help"].get(o,0)))) for o in others}
        d["suggest"] = {o:t for o,t in list(d.get("suggest",{}).items())[:2] if o in others and t in TASKS}
        if d.get("task") not in TASKS: d["task"]="A"
        d.setdefault("ethics",{}); d.setdefault("emotion",{})
        a["memory"].append(str(d.get("belief",""))[:160]); return d
    except Exception as e:
        CALLS["failed"] = CALLS.get("failed",0)+1
        if "insufficient_quota" in str(e) or "401" in str(e):
            raise SystemExit("API unavailable (%s); stopping instead of silently using rules." % type(e).__name__)
        if "Connection" in type(e).__name__ and CFG["local"]:
            raise SystemExit("Local endpoint unreachable (%s); stopping." % type(e).__name__)
        if "Timeout" in type(e).__name__: CALLS["timeouts"]=CALLS.get("timeouts",0)+1
        print("llm error, rule fallback:", type(e).__name__); return rules_decide(a, ags, last, rng)

def run(mode, rounds, seed, cap):
    ags, rng = init(seed); client=None
    if mode=="llm":
        from openai import OpenAI
        if CFG["local"]:
            import urllib.request
            try: urllib.request.urlopen(CFG["base_url"].rstrip("/")+"/models", timeout=5).read()
            except Exception as e: raise SystemExit("Endpoint %s is down or unreachable: %s" % (CFG["base_url"], e))
            client = OpenAI(api_key="local-dummy", base_url=CFG["base_url"], max_retries=0)
        else:
            key = os.environ.get("OPENAI_API_KEY_589")
            if not key: raise SystemExit("OPENAI_API_KEY_589 not set (needed for default OpenAI endpoint).")
            client = OpenAI(api_key=key, max_retries=0)
    last, pending = {}, {n:{} for n in ags}
    log = dict(help={}, sugg=[], close_hist=[])
    for t in range(rounds):
        dec = {}
        for n,a in ags.items():
            dec[n] = llm_decide(a,ags,last,pending[n],rng,client,cap) if mode=="llm" else rules_decide(a,ags,last,rng)
        # suggestions are scored against target's choice this round
        for n,d in dec.items():
            for o,tk in d["suggest"].items():
                log["sugg"].append((t,n,o,tk,dec[o]["task"], tk==dec[o]["task"], pending[o].get(n)==dec[o]["task"]))
        newpend = {n:{} for n in ags}
        for n,d in dec.items():
            for o,tk in d["suggest"].items(): newpend[o][n]=tk
        # adoption of LAST round's suggestions = real authority
        last = {}
        for n,d in dec.items():
            a=ags[n]; a["skill"][d["task"]] += 0.3
            for o,h in d["help"].items():
                last[(n,o)] = h; k=tier(a,ags[o]); log["help"].setdefault(k,[]).append(h)
                ags[o]["util"] += h*1.5; a["util"] -= h
        # closeness update (affect+ethics -> identity)
        for n,d in dec.items():
            a=ags[n]
            for o in a["close"]:
                got = last.get((o,n),0); e = d["ethics"].get(o,"neutral")
                delta = (0.35 if got>=2 else -0.25 if got==0 else 0) + (0.2 if e=="approve" else -0.2 if e=="repress" else 0)
                a["close"][o] = max(1,min(5,a["close"][o]+delta))
        if MEM["store"]:
            for (n,o),h in last.items():
                if h>0: MEM["store"].remember(o, n, h, MEM["clock"], MEM["session"], f"{n} helped me ({h}) in round {MEM['clock']}")
            MEM["clock"] += 1
        pending = newpend
        log["close_hist"].append({n:dict(a["close"]) for n,a in ags.items()})
    return ags, log

def analyze(ags, log):
    out = {"mean_help_by_tier": {k:round(st.mean(v),3) for k,v in log["help"].items()},
           "n_help_obs": {k:len(v) for k,v in log["help"].items()}}
    # authority: adoption rate of an agent's suggestions issued in previous round
    adopt = {}
    for (t,n,o,tk,choice,_,_) in log["sugg"]: pass
    pend_hits = {}
    for (t,n,o,tk,choice,same,prev_hit) in log["sugg"]: pass
    # compute from pending: was suggestion from n at round t followed by o at t+1
    byround = {}
    for (t,n,o,tk,choice,same,prev) in log["sugg"]: byround.setdefault(t,{})[(n,o)]=tk
    choices = {}
    for (t,n,o,tk,choice,same,prev) in log["sugg"]: choices[(t,o)]=choice
    for (t,n,o,tk,choice,same,prev) in log["sugg"]:
        if (t+1,o) in choices:
            adopt.setdefault(n,[]).append(choices[(t+1,o)]==tk)
    auth = {n:round(sum(v)/len(v),3) for n,v in adopt.items() if v}
    # in-closeness (how close others feel to n) at end
    final = log["close_hist"][-1]
    incl = {n: round(st.mean(final[o][n] for o in final if o!=n),2) for n in ags}
    out["authority_adoption_rate"]=auth; out["final_in_closeness"]=incl
    names=[n for n in auth]
    if len(names)>2:
        xs=[incl[n] for n in names]; ys=[auth[n] for n in names]
        try: out["corr_closeness_authority"]=round(st.correlation(xs,ys),3)
        except Exception: out["corr_closeness_authority"]=None
        out["authority_spread_max_minus_min"]=round(max(ys)-min(ys),3)
    allh=[h for v in log["help"].values() for h in v]; out["mean_help_all"]=round(st.mean(allh),3)
    u=sorted(a["util"] for a in ags.values()); out["min_util"]=round(u[0],2); out["mean_util"]=round(st.mean(u),2)
    out["final_mean_closeness"]=round(st.mean(incl.values()),3)
    out["chance_adoption"]=round(1/3,3); out["api_calls_attempted"]=CALLS["n"]; out["api_calls_failed"]=CALLS.get("failed",0)
    out["json_parse_failures"]=CALLS.get("parse_fail",0); out["timeouts"]=CALLS.get("timeouts",0)
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--mode",default="rules",choices=["rules","llm"])
    p.add_argument("--rounds",type=int,default=12); p.add_argument("--seed",type=int,default=42)
    p.add_argument("--cap",type=int,default=300); p.add_argument("--out",default=None)
    p.add_argument("--base-url",default=None); p.add_argument("--model",default=None); p.add_argument("--timeout",type=float,default=60)
    p.add_argument("--memory",action="store_true",help="AMP-style file memory across runs (Talewell-inspired)")
    p.add_argument("--memory-dir",default="runs/memory/default")
    a=p.parse_args()
    if a.memory:
        MEM["store"]=AMPStore(a.memory_dir); recs=[r for n,_ in AGENTS for r in MEM["store"].records(n)]
        MEM["clock"]=max((r["observedAt"] for r in recs), default=-1)+1
        MEM["session"]=len({r["session"] for r in recs})
    if a.base_url: CFG.update(local=True, base_url=a.base_url)
    if a.model: CFG["model"]=a.model
    CFG["timeout"]=a.timeout
    ags,log=run(a.mode,a.rounds,a.seed,a.cap); res=analyze(ags,log)
    res.update(mode=a.mode,rounds=a.rounds,seed=a.seed,memory=a.memory); print(json.dumps(res,indent=1))
    if a.out: json.dump(res,open(a.out,"w"),indent=1)
