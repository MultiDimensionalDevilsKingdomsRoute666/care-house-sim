#!/bin/sh
# Rules mode: session 1 (memory being written), then session 2 with vs without memory. Seeds 1-5, 12 rounds each.
set -e; mkdir -p runs/compare; rm -rf runs/memory/cmp_*
for s in 1 2 3 4 5; do
  python3 sim.py --seed $s --memory --memory-dir runs/memory/cmp_$s --out runs/compare/s1_seed$s.json >/dev/null
  python3 sim.py --seed $((s+100)) --memory --memory-dir runs/memory/cmp_$s --out runs/compare/s2_mem_seed$s.json >/dev/null
  python3 sim.py --seed $((s+100)) --out runs/compare/s2_nomem_seed$s.json >/dev/null
done
python3 - <<'P'
import json,statistics as st
K=["mean_help_all","min_util","mean_util","final_mean_closeness"]; T=["same_family","cross_family","family_unaligned","unaligned_unaligned"]
for v in ["nomem","mem"]:
  R=[json.load(open(f"runs/compare/s2_{v}_seed{s}.json")) for s in range(1,6)]
  print(v,{k:round(st.mean(r[k] for r in R),3) for k in K},{t:round(st.mean(r["mean_help_by_tier"][t] for r in R),3) for t in T},
    "corr",[r.get("corr_closeness_authority") for r in R])
P
