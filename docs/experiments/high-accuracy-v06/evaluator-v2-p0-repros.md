# Evaluator v2 independent P0 reproductions

Evaluator commit: `b7c57c88b80f15313f42d1dd28c08b7311955de8`  
Working directory: `/private/tmp/aletheia-exp-accuracy-eval-v2`

These five adversarial cases extend rather than duplicate the original 24-case suite. They are why
the original frozen evaluator remained NO-GO despite 169 passing tests. All five executable cases now
pass on experimental v2.1 (`a80a387`, 183 tests), but the broader provenance limitations remain.

## 1. Hash-correct but incomplete scope audit passes

Invariant violated: every final-answer claim must map exactly once to a final verdict, and scope
attestation must be independently authenticated. `kd-22` covers a missing audit, not a forged,
hash-correct audit with mismatched claim/verdict cardinality.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib,json,os,sys,tempfile
sys.path.insert(0,os.path.join(os.getcwd(),"scripts/eval")); import evaluator_v2
with tempfile.TemporaryDirectory() as d:
 def put(n,x):
  p=os.path.join(d,n)
  with open(p,"w") as f:
   if isinstance(x,list):
    for r in x:f.write(json.dumps(r)+"\n")
   else:f.write(x)
 put("run.json",json.dumps({"version":"aletheia-research 0.5.0"}))
 put("brief.md","Claim A. Claim B.\n")
 put("claims.jsonl",[{"claim":"A","url":"u:a"},{"claim":"B","url":"u:b"}])
 put("verify.jsonl",[{"claim":"A","url":"u:a","verdict":"supported"}])
 sha=lambda n:hashlib.sha256(open(os.path.join(d,n),"rb").read()).hexdigest()
 put("claim_audit.json",json.dumps({"status":"complete","auditor":"arbitrary-string",
  "claim_count":2,"brief_sha256":sha("brief.md"),"claims_sha256":sha("claims.jsonl"),
  "verify_sha256":sha("verify.jsonl")}))
 r=evaluator_v2.score_run(d); print(r["citation_accuracy"],r["citation_denominator"],r["scope_gate_passed"])
PY
```

Observed: `1.0 1 True`.

## 2. Catastrophically inverted probabilities are trusted

Invariant violated: release calibration needs preregistered quality thresholds and authenticated
labels, not sample size plus a caller Boolean.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import os,sys
sys.path.insert(0,os.path.join(os.getcwd(),"scripts/eval")); import calibration_score as c
y=[1]*15+[0]*15; p=[.01]*15+[.99]*15
r=c.score_batch({"release_attested":True,"outcomes":y,"systems":{"wrong":p}}); m=r["systems"]["wrong"]
print(r["release_trusted"],m["brier"],m["ece_exact_bins"],m["auroc"])
PY
```

Observed: `True 0.9801 0.99 0.0`.

## 3. Equal-confidence AURC depends on row order

Invariant violated: metrics must be permutation-invariant within equal-confidence groups.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import os,sys
sys.path.insert(0,os.path.join(os.getcwd(),"scripts/eval")); import calibration_score as c
for y in ([1]*15+[0]*15,[0]*15+[1]*15):
 r=c.score_selective_risk(y,[.5]*30,release_attested=True)
 print(r["aurc_discrete"],r["valid_for_release_claim"])
PY
```

Observed: `0.161621 True` and `0.838379 True`.

## 4. One hundred ties disappear from release inference

Invariant violated: release inference must include all randomized topics or enforce a minimum
decisive rate.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import os,sys
sys.path.insert(0,os.path.join(os.getcwd(),"scripts/eval")); import judge_score as j
pw=[]; human=[]
for i,w in enumerate(["candidate"]*25+["baseline"]*5+["tie"]*100):
 t=f"t{i}"; s={"candidate":("A","B"),"baseline":("B","A"),"tie":("tie","tie")}[w]
 pw += [{"topic":t,"pair_id":"p","order":{"A":"candidate","B":"baseline"},"winner_shown":s[0]},
        {"topic":t,"pair_id":"p","order":{"A":"baseline","B":"candidate"},"winner_shown":s[1]}]
 human.append({"topic":t,"winner":w})
r=j.summarize({"pairwise":pw,"human":human})
print(r["wins"],r["losses"],r["ties"],r["win_rate_over_decisive"],r["verdict"])
PY
```

Observed: 25 wins, 5 losses, 100 ties, yet `candidate BETTER`.

## 5. Persisted blind input can differ from canonical output and omit topics

Invariant violated: orchestration must copy/hash canonical briefs and require the exact declared
topic/version matrix.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib,os,sys,tempfile
sys.path.insert(0,os.path.join(os.getcwd(),"scripts/eval")); import persist_judges as p
with tempfile.TemporaryDirectory() as d:
 b=os.path.join(d,"blind-inputs","only"); os.makedirs(b)
 a,z=os.path.join(b,"input-1.md"),os.path.join(b,"input-2.md"); original=os.path.join(d,"canonical.md")
 open(a,"w").write("altered"); open(z,"w").write("baseline"); open(original,"w").write("canonical")
 rows=[{"topic":"only","pair_id":"p","judge_id":"j1","judge_model":"m",
  "order":{"A":"candidate","B":"baseline"},"winner_shown":"A","A_path":a,"B_path":z,
  "prompt":f"Read {a} and {z}"},{"topic":"only","pair_id":"p","judge_id":"j2","judge_model":"m",
  "order":{"A":"baseline","B":"candidate"},"winner_shown":"B","A_path":z,"B_path":a,
  "prompt":f"Read {z} and {a}"}]
 m=p.persist({"judge_artifacts":rows,"anchor":[{"topic":"only","A":a,"B":z,"_cand_is":"A"}]},d)
 h=lambda x:hashlib.sha256(open(x,"rb").read()).hexdigest()
 print(m["paired_schema_valid"],h(a)==h(original),m.get("expected_topic_count"))
PY
```

Observed: `True False None`.

## Required next changes

Add all five cases to a new defect suite before code changes. Require externally authenticated scope
labels/cardinality; preregister calibration thresholds; compute grouped/permutation-invariant
selective risk; set a minimum decisive-topic rate and include ties in inference; and persist an
immutable manifest binding canonical run hashes, expected topic IDs, blind copies, prompts, raw judge
outputs, and aggregation code. Re-run the old and v2 evaluators after each change.
