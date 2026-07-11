# User prompt forward-test protocol

Candidate: `aletheia-research-accuracy 0.6.0-accuracy.1`  
Branch: `codex/high-accuracy-candidate-v06`

## Clean test procedure

1. Send the exact research prompt to the auditor before sharing the candidate answer. The auditor
   freezes a topic-specific must-cover, must-not-assert, decisive-source, temporal, and contradiction
   rubric without seeing the output.
2. Start a new Codex conversation and run:

   ```text
   Use $aletheia-research-accuracy with its default accuracy tier.
   <EXACT RESEARCH PROMPT>
   Return the complete answer and the required evaluation footer with the absolute run path.
   ```

3. Return the complete answer and absolute run path. The run path is authoritative; screenshots or
   answer prose alone cannot prove which runtime executed.
4. Preserve the run directory unchanged until grading finishes.

If the output is shown before the rubric is frozen, the audit remains useful but is labeled post-hoc
rather than a clean forward test.

## Grading

| Dimension | Weight | Evidence |
|---|---:|---|
| Real-world factual correctness | 25 | independent primary-source adjudication of atomic claims |
| Must-cover answer recall | 20 | frozen topic-specific information rubric |
| Citation/claim support | 15 | exact cited spans, polarity, magnitude, population/scope |
| Decisive-source and source-role quality | 10 | topic-relative primary/standard/regulator requirements |
| Contradiction, uncertainty, and temporal handling | 10 | known disputes, supersession checks, calibrated language |
| Accuracy architecture activation | 10 | `grade_accuracy_run.py`, runtime and claim-ledger traces |
| Decision usefulness | 5 | thresholds, alternatives, caveats, actionable bottom line |
| Cost/cap discipline | 5 | elapsed time, searches, attempted/manual reads, termination reason |

The structural grader is necessary but insufficient. Its score never substitutes for the first five
semantic dimensions. The audit reports claim-level errors, omitted requirements, source failures,
mechanism non-activation, cost, and the highest-value next architecture changes.

## Reproduction command

```bash
python3 scripts/eval/grade_accuracy_run.py --run <ABSOLUTE_RUN_PATH> \
  --output <ABSOLUTE_RUN_PATH>/accuracy-grade.json
```

