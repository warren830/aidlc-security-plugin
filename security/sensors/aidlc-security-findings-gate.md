---
id: security-findings-gate
kind: deterministic
command: bun {{HARNESS_DIR}}/tools/aidlc-sensor-security-findings-gate.ts
default_severity: blocking
description: Holds the Code Generation gate while a unit's AWS Security Agent diff scan record has an open finding at or above HIGH, and checks that the record gives evidence for each threat at or above HIGH in the threat model (security plugin)
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
  override_mode: string
  overrides: string[]
  coverage_mode: string
  coverage_gaps: string[]
timeout_seconds: 60
---

# security-findings-gate sensor (security plugin)

BLOCKING, at the Code Generation gate. The gate fires it on each unit's
`security-scan-result.md` and `code-generation-plan.md`. It reads only the scan
record that Code Generation's Step 4b writes, the Inception threat model, and
the project's `.aidlc-security.json`, never the network.

Fired on `security-scan-result.md`, it reads the file's one `json` block and
fails when:

- the block is missing, appears twice, is not JSON, or does not match the
  record's schema (`schema_version` 1 or 2);
- the record says no scan ran (`not_run`), or the scan's `status` is not
  `COMPLETED`;
- a finding whose `risk_level` is HIGH or CRITICAL is not `RESOLVED`, unless
  the override mode is lenient and the finding carries a valid `override` (a
  non-empty `by` and `reason`, and an ISO-8601 `at`). A finding the service
  rated `UNKNOWN` blocks the same way at every threshold.

Fired on `code-generation-plan.md`, it fails when no `security-scan-result.md`
sits beside the plan, so a unit that skipped the scan still stops the gate.

## Threat coverage

Fired on a record that holds a scan, the check also compares the record with
the threat model, unless the coverage mode is `off`. The record sits in
`<record>/construction/<unit>/code-generation/`, or in
`<record>/construction/code-generation/` when the plan has no units, and the
threat model is `<record>/inception/security-threat-model/security-threat-model.md`.
When that file does not exist, the plan skipped the threat model and nothing
needs evidence.

Each threat whose `severity` ranks at or above the threshold needs one entry
in the record's `threat_coverage`, under the `threat_model_scan_id` that
matches the threat model's `scan.scan_id`. A severity the check does not know
counts as required. An entry is one of:

- `MITIGATED`, with at least one `evidence` item: `code` or `test` with a
  `file_path` relative to the repository root, or `finding` with the
  `finding_id` of a finding in the same record. The check never opens the
  files, because the unit's code can live in a Bolt worktree.
- `ACCEPTED`, with the person's `override`. It counts only in lenient override
  mode, and only when the `override` is valid, as for a finding.
- `NOT_APPLICABLE`, with a non-empty `reason`.

Each problem is one sentence in `coverage_gaps`: a required threat without an
entry that counts, an entry naming a threat the threat model does not list or
a threat named twice, and `threat_coverage` that does not match this shape.
When `threat_coverage` is missing, does not match the shape, or names another
threat model's `scan_id`, every required threat counts as uncovered. A threat
model the check cannot read is one gap. A `threat_coverage` in a version 1
record, or beside `not_run`, is a record error and fails the fire.

The coverage mode decides what a gap does:

| `coverage_mode` | A coverage gap |
| --- | --- |
| `off` | The check does not compare the record with the threat model. |
| `warn`, the default | Listed in `coverage_gaps`. `pass` and `findings` stay as they would be without the check. |
| `block` | Listed in `coverage_gaps` and in `findings`, and the fire fails. |

## Configuration

Both modes come from `.aidlc-security.json` at the project root, which is the
working directory the dispatcher gives the worker. The file holds
`override_mode` (`strict` or `lenient`) and `coverage_mode` (`off`, `warn` or
`block`). Without the file or a key, the modes are strict and warn. In strict
mode the gate ignores every `override` in the record. A person accepts a
blocking finding or threat only through the engine's **Override blocking
sensors** choice at the gate, which the engine never offers under Construction
autonomy. In lenient mode a valid `override` accepts its finding or threat.
Both fires fail when the file exists but cannot be read, is not valid JSON,
holds a key other than `override_mode` and `coverage_mode`, or sets a value
its key does not take.

## Verdict

Every verdict is one JSON line with `pass`, `findings` (one sentence per
problem), `findings_count`, `threshold`, `override_mode` (`strict` or
`lenient`, or `null` when `.aidlc-security.json` cannot be read),
`overrides`, the findings a valid override accepted in lenient mode, each with
who, when and why, `coverage_mode` (`off`, `warn` or `block`, or `null` when
`.aidlc-security.json` cannot be read) and `coverage_gaps`. The dispatcher
keeps that line in the detail file of a failed fire only, so a gap in warn
mode shows only when the agent runs the worker itself, as Code Generation's
Step 4c does. The override decisions themselves are recorded through
`engine log decision` and `engine log answer` when the person makes them.

The threshold is HIGH. The dispatcher passes the worker `--stage` and
`--output-path` only, so `--threshold <CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL>`
applies when you run the worker yourself, from the project root so it reads the
same `.aidlc-security.json`:

```bash
bun {{HARNESS_DIR}}/tools/aidlc-sensor-security-findings-gate.ts --output-path <record>/construction/<unit>/code-generation/security-scan-result.md --threshold CRITICAL
```
