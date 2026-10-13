"""Compare baseline / memory / memory+reflect / memory+reflect+shared (+ placebo ablation).
Per seed: session 1 writes AMP memory, session 2 (seed+100) is measured. Same seed across arms."""
import json, os, shutil, statistics as st, subprocess, sys
SEEDS = range(1, 11)
ARMS = {"baseline": [], "memory": ["--memory"], "memory+reflect": ["--memory","--reflect"],
        "memory+reflect+shared": ["--memory","--reflect","--shared-block"],
        "placebo(mem+refl+shared, random targets)": ["--memory","--reflect","--shared-block","--placebo"]}
def run(args):
    out = subprocess.run([sys.executable, "sim.py", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out)
rows = {}
for arm, flags in ARMS.items():
    R = []
    for s in SEEDS:
        md = f"runs/memory/refl_{s}_{abs(hash(arm))%10**6}"; shutil.rmtree(md, ignore_errors=True)
        extra = ["--memory-dir", md] if "--memory" in flags else []
        if "--memory" in flags: run(["--seed", str(s), *flags, *extra])  # session 1 writes memory
        R.append(run(["--seed", str(s+100), *flags, *extra]))
        shutil.rmtree(md, ignore_errors=True)
    rows[arm] = R
base = {r["seed"]: r for r in rows["baseline"]}
print("| arm | mean help (0-3) | care floor (min util) | mean util | floor wins vs baseline |")
print("|---|---|---|---|---|")
for arm, R in rows.items():
    h=[r["mean_help_all"] for r in R]; f=[r["min_util"] for r in R]; u=[r["mean_util"] for r in R]
    wins=sum(r["min_util"]>base[r["seed"]]["min_util"] for r in R)
    print(f"| {arm} | {st.mean(h):.3f} ± {st.stdev(h):.3f} | {st.mean(f):.1f} ± {st.stdev(f):.1f} | {st.mean(u):.1f} | {wins}/{len(R)} |")
json.dump(rows, open("runs/compare_reflection.json","w"), indent=1)
