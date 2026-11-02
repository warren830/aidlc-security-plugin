---
id: security-findings-gate
kind: deterministic
command: bun {{HARNESS_DIR}}/tools/aidlc-sensor-security-findings-gate.ts
default_severity: blocking
description: Holds the Code Generation gate while a unit's AWS Security Agent diff scan record has an open finding at or above HIGH (security plugin)
category: security
fire_on: gate
matches: "**/code-generation/{code-generation-plan,security-scan-result}.md"
input_schema:
  output_path: string
  stage_slug: string
output_schema:
  pass: boolean
  findings: string[]
  findings_count: integer
  threshold: string
  overrides: string[]
timeout_seconds: 60
---

# security-findings-gate sensor (security plugin)

BLOCKING, at the Code Generation gate. The gate fires it on each unit's
`security-scan-result.md` and `code-generation-plan.md`. It reads only the scan
record that Code Generation's Step 4b writes, never the network.

Fired on `security-scan-result.md`, it reads the file's one `json` block and
fails when:

- the block is missing, appears twice, is not JSON, or does not match the
  record's schema (`schema_version` 1);
- the record says no scan ran (`not_run`), or the scan's `status` is not
  `COMPLETED`;
- a finding whose `risk_level` is HIGH or CRITICAL is not `RESOLVED` and
  carries no valid `override` (a non-empty `by` and `reason`, and an ISO-8601
  `at`). A finding the service rated `UNKNOWN` blocks the same way at every
  threshold.

Fired on `code-generation-plan.md`, it fails when no `security-scan-result.md`
sits beside the plan, so a unit that skipped the scan still stops the gate.

Every verdict is one JSON line with `pass`, `findings` (one sentence per
problem), `findings_count`, `threshold` and `overrides`, the findings the
person accepted, each with who, when and why. The dispatcher keeps that line in
the detail file of a failed fire only. The override decisions themselves are
recorded through `engine log decision` and `engine log answer` when the person
makes them.

The threshold is HIGH. The dispatcher passes the worker `--stage` and
`--output-path` only, so `--threshold <CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL>`
applies when you run the worker yourself:

```bash
bun {{HARNESS_DIR}}/tools/aidlc-sensor-security-findings-gate.ts --output-path <record>/construction/<unit>/code-generation/security-scan-result.md --threshold CRITICAL
```
