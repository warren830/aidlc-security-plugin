// The security-findings-gate worker's verdicts over committed scan records.
// Every case runs the real worker twice, as the copy channel runs it (a Bun
// subprocess) and as a native install does (importing it and calling
// main(argv)), and both must print the same single JSON line. Both run in a
// project folder, because the dispatcher gives the worker the project root as
// its working directory and the worker reads .aidlc-security.json there. The
// threat coverage cases fire on records inside a record tree, because the
// worker finds the threat model from the record's place in it.
import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { PLUGIN_ROOT, REPO_ROOT } from "../scripts/upstream.ts";

const WORKER = join(PLUGIN_ROOT, "tools", "aidlc-sensor-security-findings-gate.ts");
const RECORDS = join(REPO_ROOT, "tests", "fixtures", "scan-records");
const TREES = join(REPO_ROOT, "tests", "fixtures", "records");
const PROJECTS = join(REPO_ROOT, "tests", "fixtures", "projects");
const NO_CONFIG = mkdtempSync(join(tmpdir(), "security-gate-project-"));
afterAll(() => rmSync(NO_CONFIG, { recursive: true, force: true }));
const CONFIG_SHAPE =
	'{"override_mode": "strict" or "lenient", "coverage_mode": "off" or "warn" or "block"}, with each key optional';

const { main } = (await import(WORKER)) as { main: (argv: string[]) => void };

interface Verdict {
	pass: boolean;
	findings: string[];
	findings_count: number;
	threshold: string;
	override_mode: "strict" | "lenient" | null;
	overrides: string[];
	coverage_mode: "off" | "warn" | "block" | null;
	coverage_gaps: string[];
}

function viaSubprocess(project: string, argv: string[]): string {
	const run = spawnSync(process.execPath, [WORKER, ...argv], { cwd: project, encoding: "utf-8" });
	expect(run.status, run.stderr).toBe(0);
	return run.stdout;
}

function viaMain(project: string, argv: string[]): string {
	const chunks: string[] = [];
	const write = process.stdout.write;
	const cwd = process.cwd();
	process.stdout.write = ((chunk: string | Uint8Array) => {
		chunks.push(String(chunk));
		return true;
	}) as typeof process.stdout.write;
	try {
		process.chdir(project);
		main(argv);
	} finally {
		process.chdir(cwd);
		process.stdout.write = write;
	}
	return chunks.join("");
}

function fireAt(project: string, outputPath: string, ...extra: string[]): Verdict {
	const argv = ["--stage", "code-generation", "--output-path", outputPath, ...extra];
	const printed = viaSubprocess(project, argv);
	expect(viaMain(project, argv)).toBe(printed);
	const lines = printed.split("\n").filter((line) => line !== "");
	expect(lines).toHaveLength(1);
	const verdict = JSON.parse(lines[0]) as Verdict;
	expect(verdict.findings_count).toBe(verdict.findings.length);
	return verdict;
}

function fireIn(project: string, fixture: string, file = "security-scan-result.md", ...extra: string[]): Verdict {
	return fireAt(project, join(RECORDS, fixture, file), ...extra);
}

function fire(fixture: string, file?: string, ...extra: string[]): Verdict {
	return fireIn(NO_CONFIG, fixture, file, ...extra);
}

describe("a completed scan passes", () => {
	test("with no findings", () => {
		expect(fire("clean")).toEqual({
			pass: true,
			findings: [],
			findings_count: 0,
			threshold: "HIGH",
			override_mode: "strict",
			overrides: [],
			coverage_mode: "warn",
			coverage_gaps: [],
		});
	});

	test("when every finding ranks below HIGH", () => {
		expect(fire("below-threshold").pass).toBe(true);
	});

	test("when a CRITICAL finding is RESOLVED", () => {
		expect(fire("resolved").pass).toBe(true);
	});
});

describe("open findings at or above the threshold block", () => {
	test("an ACTIVE HIGH and a FALSE_POSITIVE CRITICAL each block, the LOW does not", () => {
		const verdict = fire("open-high");
		expect(verdict.pass).toBe(false);
		expect(verdict.findings_count).toBe(2);
		expect(verdict.findings[0]).toContain("f-101 (HIGH) Hardcoded credential at src/config.ts:12");
		expect(verdict.findings[1]).toContain("f-102 (CRITICAL) Command built from request input at src/run.ts:30-34");
		expect(verdict.findings.join(" ")).not.toContain("f-103");
		expect(verdict.findings[0]).toContain("Override blocking sensors at the gate");
	});

	test("a finding the service could not rate blocks even at the CRITICAL threshold", () => {
		const verdict = fire("unknown-risk", "security-scan-result.md", "--threshold", "CRITICAL");
		expect(verdict.pass).toBe(false);
		expect(verdict.findings[0]).toContain("f-601 (UNKNOWN)");
	});

	test("--threshold CRITICAL lets an open HIGH through and still blocks the CRITICAL", () => {
		const verdict = fire("open-critical", "security-scan-result.md", "--threshold", "CRITICAL");
		expect(verdict.threshold).toBe("CRITICAL");
		expect(verdict.findings_count).toBe(1);
		expect(verdict.findings[0]).toContain("f-702 (CRITICAL)");
	});

	test("--threshold MEDIUM blocks the MEDIUM finding a HIGH gate lets through", () => {
		const verdict = fire("below-threshold", "security-scan-result.md", "--threshold", "MEDIUM");
		expect(verdict.findings_count).toBe(1);
		expect(verdict.findings[0]).toContain("f-201 (MEDIUM)");
	});

	test("a threshold that is not a risk level fails instead of guessing", () => {
		const verdict = fire("clean", "security-scan-result.md", "--threshold", "SEVERE");
		expect(verdict.pass).toBe(false);
		expect(verdict.findings[0]).toContain('"SEVERE" is not a risk level');
	});
});

describe("override modes", () => {
	const ACCEPTED =
		"f-401 (HIGH) Hardcoded credential at test/fixtures/keys.ts:3: accepted by Dana Lee at 2026-11-02T09:55:00Z. Reason: A fake key in a test fixture; it never reaches a deployment.";
	const config = (project: string) => join(PROJECTS, project, ".aidlc-security.json");

	test("without .aidlc-security.json the gate is strict: the record's override does not pass the finding", () => {
		const verdict = fire("override-accepted");
		expect(verdict.pass).toBe(false);
		expect(verdict.override_mode).toBe("strict");
		expect(verdict.overrides).toEqual([]);
		expect(verdict.findings).toHaveLength(1);
		expect(verdict.findings[0]).toContain("f-401 (HIGH)");
		expect(verdict.findings[0]).toContain("ignores its override in the record");
		expect(verdict.findings[0]).toContain("Override blocking sensors at the gate");
	});

	test("a strict .aidlc-security.json blocks the same finding", () => {
		const verdict = fireIn(join(PROJECTS, "strict"), "override-accepted");
		expect(verdict.pass).toBe(false);
		expect(verdict.override_mode).toBe("strict");
		expect(verdict.findings[0]).toContain("ignores its override in the record");
	});

	test("in lenient mode a finding the person accepted passes, and the output says who accepted it, when and why", () => {
		const verdict = fireIn(join(PROJECTS, "lenient"), "override-accepted");
		expect(verdict.pass).toBe(true);
		expect(verdict.override_mode).toBe("lenient");
		expect(verdict.coverage_mode).toBe("warn");
		expect(verdict.overrides).toEqual([ACCEPTED]);
	});

	test("in lenient mode an override with a blank reason, no one in by, or an unreadable time does not count", () => {
		const verdict = fireIn(join(PROJECTS, "lenient"), "override-invalid");
		expect(verdict.pass).toBe(false);
		expect(verdict.overrides).toEqual([]);
		expect(verdict.findings).toHaveLength(3);
		expect(verdict.findings[0]).toContain("f-501");
		expect(verdict.findings[0]).toContain("gives no `reason`");
		expect(verdict.findings[1]).toContain("f-502");
		expect(verdict.findings[1]).toContain("names no one in `by`");
		expect(verdict.findings[2]).toContain("f-503");
		expect(verdict.findings[2]).toContain('"last Tuesday"');
	});

	test("a .aidlc-security.json that is not JSON fails the gate, naming the file and every mode", () => {
		const verdict = fireIn(join(PROJECTS, "malformed"), "override-accepted");
		expect(verdict.pass).toBe(false);
		expect(verdict.override_mode).toBeNull();
		expect(verdict.coverage_mode).toBeNull();
		expect(verdict.overrides).toEqual([]);
		expect(verdict.findings).toHaveLength(1);
		expect(verdict.findings[0]).toContain(`${config("malformed")} is not valid JSON`);
		expect(verdict.findings[0]).toContain(CONFIG_SHAPE);
	});

	test("a mode that is neither strict nor lenient fails the gate", () => {
		const verdict = fireIn(join(PROJECTS, "unknown-mode"), "override-accepted");
		expect(verdict.pass).toBe(false);
		expect(verdict.override_mode).toBeNull();
		expect(verdict.findings).toHaveLength(1);
		expect(verdict.findings[0]).toContain(`${config("unknown-mode")} sets override_mode to "loose"`);
		expect(verdict.findings[0]).toContain(CONFIG_SHAPE);
	});

	test("a coverage mode that is not off, warn or block fails the gate the same way", () => {
		const verdict = fireIn(join(PROJECTS, "unknown-coverage-mode"), "clean");
		expect(verdict.pass).toBe(false);
		expect(verdict.override_mode).toBeNull();
		expect(verdict.coverage_mode).toBeNull();
		expect(verdict.coverage_gaps).toEqual([]);
		expect(verdict.findings).toEqual([
			`${config("unknown-coverage-mode")} sets coverage_mode to "strict". It must hold ${CONFIG_SHAPE}.`,
		]);
	});

	test("a misspelled key fails the gate, even on a clean scan, instead of falling back to strict", () => {
		const verdict = fireIn(join(PROJECTS, "unknown-key"), "clean");
		expect(verdict.pass).toBe(false);
		expect(verdict.override_mode).toBeNull();
		expect(verdict.findings[0]).toContain(`${config("unknown-key")} has keys the gate does not read ("overrideMode")`);
	});
});

describe("a record that is no evidence blocks", () => {
	test("a scan that is not COMPLETED", () => {
		const verdict = fire("in-progress");
		expect(verdict.pass).toBe(false);
		expect(verdict.findings[0]).toContain("scan-5e6f7a8b is IN_PROGRESS, not COMPLETED");
	});

	test("a record saying no scan ran, with the person's reason", () => {
		const verdict = fire("not-run");
		expect(verdict.pass).toBe(false);
		expect(verdict.findings[0]).toContain("No diff scan ran for this unit: The AWS account is not set up yet");
	});

	test("a record that does not match the schema, naming each problem", () => {
		const verdict = fire("wrong-schema");
		expect(verdict.pass).toBe(false);
		const problems = verdict.findings.join("\n");
		expect(problems).toContain("schema_version is 3");
		expect(problems).toContain("scan.scan_id must be a non-empty string");
		expect(problems).toContain('scan.status is "DONE"');
		expect(problems).toContain('findings[0].risk_level is "SEVERE"');
	});

	test("a record with two json blocks", () => {
		const verdict = fire("two-blocks");
		expect(verdict.pass).toBe(false);
		expect(verdict.findings[0]).toContain("holds 2 ```json blocks");
	});
});

describe("a missing record blocks", () => {
	test("fired on the unit's plan with no record beside it", () => {
		const verdict = fire("plan-only", "code-generation-plan.md");
		expect(verdict.pass).toBe(false);
		expect(verdict.findings[0]).toContain(join(RECORDS, "plan-only", "security-scan-result.md"));
		expect(verdict.findings[0]).toContain("Code Generation's security step writes it");
	});

	test("fired on a record path that does not exist", () => {
		expect(fire("does-not-exist").pass).toBe(false);
	});

	test("fired on the plan with a record beside it, the plan's fire passes and leaves the record to its own fire", () => {
		expect(fire("plan-with-record", "code-generation-plan.md").pass).toBe(true);
	});
});

describe("threat coverage", () => {
	const unit = (name: string, file = "security-scan-result.md") =>
		join(TREES, "threat-model", "construction", name, "code-generation", file);
	const brokenModel = join(TREES, "broken-threat-model", "construction", "unit-a", "code-generation", "security-scan-result.md");
	const project = (name: string) => join(PROJECTS, name);
	const T001 = "T-001 (CRITICAL) A token whose header says alg none is accepted without a signature";
	const T002 = "T-002 (HIGH) An expired token, or one issued for another service, is still accepted";
	const T003 = "T-003 (HIGH) Session tokens are written to the access log";
	const NO_EVIDENCE =
		"no evidence in threat_coverage. Record the code or test that mitigates it, or why it does not apply to this unit.";
	const uncovered = (...threats: string[]) => threats.map((threat) => `${threat}: ${NO_EVIDENCE}`);

	test("without coverage_mode the mode is warn: a HIGH threat with no entry passes the gate and is listed", () => {
		const verdict = fireAt(NO_CONFIG, unit("missing-entry"));
		expect(verdict).toMatchObject({ pass: true, findings: [], coverage_mode: "warn" });
		expect(verdict.coverage_gaps).toEqual(uncovered(T003));
	});

	test("warn set in .aidlc-security.json lists the same gap and passes", () => {
		const verdict = fireAt(project("coverage-warn"), unit("missing-entry"));
		expect(verdict).toMatchObject({ pass: true, findings: [], coverage_mode: "warn" });
		expect(verdict.coverage_gaps).toEqual(uncovered(T003));
	});

	test("block holds the gate on the same gap", () => {
		const verdict = fireAt(project("coverage-block"), unit("missing-entry"));
		expect(verdict).toMatchObject({ pass: false, coverage_mode: "block" });
		expect(verdict.findings).toEqual(uncovered(T003));
		expect(verdict.coverage_gaps).toEqual(uncovered(T003));
	});

	test("off checks nothing, even against a threat model that cannot be read", () => {
		expect(fireAt(project("coverage-off"), unit("missing-entry"))).toMatchObject({
			pass: true,
			coverage_mode: "off",
			coverage_gaps: [],
		});
		expect(fireAt(project("coverage-off"), brokenModel)).toMatchObject({ pass: true, coverage_gaps: [] });
	});

	test("a threat model that cannot be read is one gap", () => {
		const verdict = fireAt(NO_CONFIG, brokenModel);
		expect(verdict).toMatchObject({ pass: true, findings: [] });
		expect(verdict.coverage_gaps).toHaveLength(1);
		expect(verdict.coverage_gaps[0]).toStartWith("security-threat-model.md: its json block is not valid JSON");
		expect(verdict.coverage_gaps[0]).toEndWith("The gate cannot tell which threats need evidence.");
		expect(fireAt(project("coverage-block"), brokenModel).pass).toBe(false);
	});

	test("a version 1 record written before the check passes under off and warn when a threat model exists", () => {
		expect(fireAt(project("coverage-off"), unit("no-coverage"))).toMatchObject({
			pass: true,
			findings: [],
			coverage_gaps: [],
		});
		const warn = fireAt(NO_CONFIG, unit("no-coverage"));
		expect(warn).toMatchObject({ pass: true, findings: [] });
		expect(warn.coverage_gaps).toEqual(uncovered(T001, T002, T003));
	});

	test("complete coverage passes in block, and the MEDIUM and LOW threats need no entry", () => {
		expect(fireAt(project("coverage-block"), unit("covered"))).toMatchObject({
			pass: true,
			findings: [],
			coverage_gaps: [],
		});
	});

	test("--threshold MEDIUM requires the MEDIUM threat too", () => {
		const verdict = fireAt(project("coverage-block"), unit("covered"), "--threshold", "MEDIUM");
		expect(verdict.pass).toBe(false);
		expect(verdict.coverage_gaps).toEqual(uncovered("T-004 (MEDIUM) Error responses name the check that failed"));
	});

	test("in strict mode an ACCEPTED threat is a gap that sends the person to Override blocking sensors", () => {
		const verdict = fireAt(project("coverage-block"), unit("accepted"));
		expect(verdict.pass).toBe(false);
		expect(verdict.coverage_gaps).toHaveLength(1);
		expect(verdict.coverage_gaps[0]).toStartWith(`${T003}: ACCEPTED, but the gate ignores its override`);
		expect(verdict.coverage_gaps[0]).toContain("Override blocking sensors at the gate");
	});

	test("in lenient mode a valid override accepts the threat", () => {
		expect(fireAt(project("lenient-coverage-block"), unit("accepted"))).toMatchObject({
			pass: true,
			override_mode: "lenient",
			coverage_gaps: [],
		});
	});

	test("coverage written for another threat model leaves every required threat uncovered", () => {
		const verdict = fireAt(project("coverage-block"), unit("stale"));
		expect(verdict.pass).toBe(false);
		expect(verdict.coverage_gaps[0]).toContain(
			"its threat_model_scan_id is scan-tm-0f0e0d0c, and the scan_id in security-threat-model.md is scan-tm-1a2b3c4d",
		);
		expect(verdict.coverage_gaps.slice(1)).toEqual(uncovered(T001, T002, T003));
	});

	test("an entry for a threat the threat model does not list, or a threat named twice, is a gap", () => {
		expect(fireAt(project("coverage-block"), unit("ids")).coverage_gaps).toEqual([
			"threat_coverage names T-001 2 times. Keep one entry per threat.",
			"threat_coverage names T-009, which security-threat-model.md does not list.",
		]);
	});

	test("evidence names a finding of this record, or a file by its path from the repository root", () => {
		expect(fireAt(NO_CONFIG, unit("weak-evidence")).coverage_gaps).toEqual([
			`${T001}: its evidence cites finding f-404, which this record's findings do not hold.`,
			`${T002}: MITIGATED with no evidence. Name the code, test or finding that shows its control.`,
			`${T003}: its code evidence has file_path "/home/dev/app/src/log.ts". Use a path relative to the repository root.`,
		]);
	});

	test("NOT_APPLICABLE needs a reason, and in lenient mode ACCEPTED needs a valid override", () => {
		expect(fireAt(project("lenient-coverage-block"), unit("weak-decisions")).coverage_gaps).toEqual([
			`${T002}: NOT_APPLICABLE with no reason. Say why this unit does not touch it.`,
			`${T003}: ACCEPTED, but its override names no one in \`by\`.`,
		]);
	});

	test("a threat_coverage that does not match its shape is a coverage gap, never a record error", () => {
		const warn = fireAt(NO_CONFIG, unit("malformed"));
		expect(warn).toMatchObject({ pass: true, findings: [] });
		expect(warn.coverage_gaps).toEqual([
			'security-scan-result.md: threat_coverage.threats[0].status is "DONE"; it must be one of MITIGATED, ACCEPTED, NOT_APPLICABLE.',
			'security-scan-result.md: threat_coverage.threats[1].evidence[0].kind is "file"; it must be one of code, test, finding.',
			...uncovered(T001, T002, T003),
		]);
		expect(fireAt(project("coverage-block"), unit("malformed")).pass).toBe(false);
	});

	test("threat_coverage in a version 1 record, or beside not_run, is a record error even with coverage off", () => {
		expect(fireAt(project("coverage-off"), unit("v1-with-coverage")).findings).toEqual([
			"security-scan-result.md: threat_coverage needs schema_version 2.",
		]);
		expect(fireAt(project("coverage-off"), unit("not-run-with-coverage")).findings).toEqual([
			"security-scan-result.md: threat_coverage sits beside scan, so a not_run record holds none.",
		]);
	});

	test("the plan's fire leaves coverage to the record's own fire", () => {
		expect(fireAt(project("coverage-block"), unit("missing-entry", "code-generation-plan.md"))).toMatchObject({
			pass: true,
			coverage_gaps: [],
		});
	});

	test("a unit named construction still finds its record's threat model", () => {
		expect(fireAt(NO_CONFIG, unit("construction")).coverage_gaps).toEqual(uncovered(T001, T002, T003));
	});

	test("a plan without units finds the threat model, a version 1 threat model's unknown severity is required, and a long statement is cut between words", () => {
		const record = join(TREES, "no-units", "construction", "code-generation", "security-scan-result.md");
		expect(fireAt(NO_CONFIG, record).coverage_gaps).toEqual(
			uncovered(
				"e1c5d3f0-7c1e (SEVERE) The upload endpoint accepts a file of any size, so one large request can fill...",
				"e1c5d3f0-4f8a (HIGH) A file name such as ../../app.env makes the upload handler write outside its own...",
			),
		);
	});

	test("a record whose plan skipped the threat model has no gaps, even in block mode", () => {
		const record = join(TREES, "no-threat-model", "construction", "unit-a", "code-generation", "security-scan-result.md");
		expect(fireAt(project("coverage-block"), record)).toMatchObject({ pass: true, coverage_gaps: [] });
	});
});

test("without --output-path the worker exits 2 and prints no verdict", () => {
	const run = spawnSync(process.execPath, [WORKER, "--stage", "code-generation"], { encoding: "utf-8" });
	expect(run.status).toBe(2);
	expect(run.stdout).toBe("");
	expect(run.stderr).toContain("Usage:");
});
