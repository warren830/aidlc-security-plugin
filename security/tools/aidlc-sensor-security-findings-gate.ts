// security-findings-gate sensor: holds the Code Generation gate while a unit's
// AWS Security Agent diff scan record has an open finding at or above the
// threshold. It also lists each threat at or above the threshold in the
// Inception threat model that the record gives no evidence for, and holds the
// gate on those only in block coverage mode. It reads only that record, the
// threat model and the project's .aidlc-security.json, never the network. The
// dispatcher treats any non-zero exit as "could not run", so every verdict,
// pass or fail, is one JSON line on stdout with exit 0.
//
// Self-contained: a plugin tool must not import the framework's aidlc-lib.
import { readFileSync } from "node:fs";
import { basename, dirname, isAbsolute, join } from "node:path";

const RECORD_FILE = "security-scan-result.md";
const THREAT_MODEL_FILE = "security-threat-model.md";

// UNKNOWN ranks above CRITICAL so it blocks at every threshold: a finding the
// service could not rate is no evidence that it is minor.
const RISK_RANK = { INFORMATIONAL: 0, LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4, UNKNOWN: 5 } as const;
type RiskLevel = keyof typeof RISK_RANK;
type Threshold = Exclude<RiskLevel, "UNKNOWN">;
const RISK_LEVELS = Object.keys(RISK_RANK) as RiskLevel[];
const THRESHOLDS = RISK_LEVELS.filter((level): level is Threshold => level !== "UNKNOWN");

// The manifest's command cannot carry a threshold: the dispatcher runs this file
// with --stage and --output-path only. A different gate level is a change here.
const DEFAULT_THRESHOLD: Threshold = "HIGH";

// The dispatcher runs this file with the project root as its working directory,
// so a committed file there reaches every real fire and shows in review. An
// environment variable would not: the agent sets the environment of the
// commands it runs. Strict is the default because the gate cannot tell whether
// a person or the agent wrote an override into the record. Warn is the default
// coverage mode, so a coverage gap never changes the pass or the findings of a
// project that does not choose block.
const CONFIG_FILE = ".aidlc-security.json";
const OVERRIDE_MODES = ["strict", "lenient"] as const;
type OverrideMode = (typeof OVERRIDE_MODES)[number];
const COVERAGE_MODES = ["off", "warn", "block"] as const;
type CoverageMode = (typeof COVERAGE_MODES)[number];
interface Config {
	override_mode: OverrideMode;
	coverage_mode: CoverageMode;
}
const DEFAULT_CONFIG: Config = { override_mode: "strict", coverage_mode: "warn" };
const quoted = (values: readonly string[]) => values.map((value) => `"${value}"`).join(" or ");
const CONFIG_SHAPE = `{"override_mode": ${quoted(OVERRIDE_MODES)}, "coverage_mode": ${quoted(COVERAGE_MODES)}}, with each key optional`;
const AT_THE_GATE = "the person can accept the risk by choosing Override blocking sensors at the gate.";
const ACCEPT_AT_GATE = `Fix it and scan again, or ${AT_THE_GATE}`;
const NO_EVIDENCE =
	"no evidence in threat_coverage. Record the code or test that mitigates it, or why it does not apply to this unit.";

const FINDING_STATUSES = ["ACTIVE", "RESOLVED", "ACCEPTED", "FALSE_POSITIVE"] as const;
const SCAN_STATUSES = ["IN_PROGRESS", "STOPPING", "STOPPED", "FAILED", "COMPLETED"] as const;
type ScanStatus = (typeof SCAN_STATUSES)[number];
const COVERAGE_STATUSES = ["MITIGATED", "ACCEPTED", "NOT_APPLICABLE"] as const;
const EVIDENCE_KINDS = ["code", "test", "finding"] as const;

interface CodeLocation {
	file_path: string;
	line_start?: number;
	line_end?: number;
}

interface Override {
	by: string;
	reason: string;
	at: string;
}

interface Finding {
	finding_id: string;
	name: string;
	risk_level: RiskLevel;
	status: (typeof FINDING_STATUSES)[number];
	code_locations: CodeLocation[];
	override?: Override;
}

interface Scan {
	scan_id: string;
	base_ref: string;
	status: ScanStatus;
	region: string;
	mcp_server: string;
	completed_at?: string;
}

interface ScannedRecord {
	kind: "scanned";
	scan: Scan;
	findings: Finding[];
	// The coverage check parses it, because its problems are coverage gaps and
	// never record errors.
	threat_coverage: unknown;
}

type ScanRecord = ScannedRecord | { kind: "not-run"; reason: string; at: string };

interface Threat {
	threat_id: string;
	severity: string;
	statement: string;
}

interface ThreatModel {
	scan_id: string;
	threats: Threat[];
}

type Evidence =
	| { kind: "code"; file_path: string; line_start?: number; line_end?: number }
	| { kind: "test"; file_path: string; name?: string }
	| { kind: "finding"; finding_id: string };

type CoverageEntry =
	| { threat_id: string; status: "MITIGATED"; evidence: Evidence[] }
	| { threat_id: string; status: "ACCEPTED"; override: Override }
	| { threat_id: string; status: "NOT_APPLICABLE"; reason: string };

interface ThreatCoverage {
	threat_model_scan_id: string;
	threats: CoverageEntry[];
}

type ConfigSetting = { config: Config } | { problem: string };
type ThreatModelSetting = { model: ThreatModel | null } | { problem: string };

interface Verdict {
	pass: boolean;
	findings: string[];
	findings_count: number;
	threshold: string;
	override_mode: OverrideMode | null;
	overrides: string[];
	coverage_mode: CoverageMode | null;
	coverage_gaps: string[];
}

const ISO_8601 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/;

function isTimestamp(value: string): boolean {
	return ISO_8601.test(value) && Number.isFinite(Date.parse(value));
}

function isOneOf<T extends string>(allowed: readonly T[], value: unknown): value is T {
	return typeof value === "string" && (allowed as readonly string[]).includes(value);
}

function message(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

// Only a missing file or key falls back to its default. Anything else that is
// not one of a key's modes fails the gate, so a typo never decides a mode.
function readConfig(projectDir: string): ConfigSetting {
	const path = join(projectDir, CONFIG_FILE);
	const problem = (what: string): ConfigSetting => ({ problem: `${path} ${what}. It must hold ${CONFIG_SHAPE}.` });
	let text: string;
	try {
		text = readFileSync(path, "utf-8");
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return { config: DEFAULT_CONFIG };
		return problem(`cannot be read (${message(error)})`);
	}
	let raw: unknown;
	try {
		raw = JSON.parse(text);
	} catch (error) {
		return problem(`is not valid JSON (${message(error)})`);
	}
	if (typeof raw !== "object" || raw === null || Array.isArray(raw)) return problem("is not a JSON object");
	const unread = Object.keys(raw).filter((key) => !Object.hasOwn(DEFAULT_CONFIG, key));
	if (unread.length > 0) {
		return problem(`has keys the gate does not read (${unread.map((key) => JSON.stringify(key)).join(", ")})`);
	}
	const { override_mode = DEFAULT_CONFIG.override_mode, coverage_mode = DEFAULT_CONFIG.coverage_mode } =
		raw as Record<string, unknown>;
	if (!isOneOf(OVERRIDE_MODES, override_mode)) return problem(`sets override_mode to ${JSON.stringify(override_mode)}`);
	if (!isOneOf(COVERAGE_MODES, coverage_mode)) return problem(`sets coverage_mode to ${JSON.stringify(coverage_mode)}`);
	return { config: { override_mode, coverage_mode } };
}

function recordJson(markdown: string): { value: unknown } | { problem: string } {
	const lines = markdown.split(/\r?\n/);
	const blocks: string[] = [];
	for (let open = 0; open < lines.length; open++) {
		if (!/^```json\s*$/.test(lines[open])) continue;
		const close = lines.findIndex((line, index) => index > open && /^```\s*$/.test(line));
		if (close === -1) return { problem: "its ```json block is never closed" };
		blocks.push(lines.slice(open + 1, close).join("\n"));
		open = close;
	}
	if (blocks.length !== 1) {
		return { problem: `it holds ${blocks.length} \`\`\`json blocks, and the record is exactly one` };
	}
	try {
		return { value: JSON.parse(blocks[0]) };
	} catch (error) {
		return { problem: `its json block is not valid JSON (${message(error)})` };
	}
}

function fieldReader(problems: string[]) {
	const object = (input: unknown, at: string): Record<string, unknown> => {
		if (typeof input === "object" && input !== null && !Array.isArray(input)) {
			return input as Record<string, unknown>;
		}
		problems.push(`${at} must be an object`);
		return {};
	};
	const list = (input: unknown, at: string): unknown[] => {
		if (Array.isArray(input)) return input;
		problems.push(`${at} must be a list`);
		return [];
	};
	const text = (input: unknown, at: string, nonEmpty = true): string => {
		if (typeof input === "string" && (!nonEmpty || input.trim() !== "")) return input;
		problems.push(`${at} must be a${nonEmpty ? " non-empty" : ""} string`);
		return "";
	};
	const variant = <T extends string>(input: unknown, at: string, allowed: readonly T[]): T | null => {
		if (isOneOf(allowed, input)) return input;
		problems.push(`${at} is ${JSON.stringify(input)}; it must be one of ${allowed.join(", ")}`);
		return null;
	};
	const oneOf = <T extends string>(input: unknown, at: string, allowed: readonly T[]): T =>
		variant(input, at, allowed) ?? allowed[0];
	const timestamp = (input: unknown, at: string): string => {
		const time = text(input, at);
		if (time !== "" && !isTimestamp(time)) problems.push(`${at} is "${time}", not an ISO-8601 time`);
		return time;
	};
	const optionalLine = (input: unknown, at: string): number | undefined => {
		if (input === undefined) return undefined;
		if (Number.isInteger(input)) return input as number;
		problems.push(`${at} must be a whole number`);
		return undefined;
	};
	return { object, list, text, variant, oneOf, timestamp, optionalLine };
}

function parseRecord(value: unknown): { record: ScanRecord } | { problems: string[] } {
	const problems: string[] = [];
	const { object, list, text, oneOf, timestamp, optionalLine } = fieldReader(problems);

	const root = object(value, "the record");
	if (root.schema_version !== 1 && root.schema_version !== 2) {
		problems.push(`schema_version is ${JSON.stringify(root.schema_version)}; this gate reads version 1 or 2`);
	}
	if ((root.scan === undefined) === (root.not_run === undefined)) {
		problems.push("the record must hold either scan or not_run, and not both");
		return { problems };
	}
	if (root.threat_coverage !== undefined && root.schema_version === 1) {
		problems.push("threat_coverage needs schema_version 2");
	}
	if (root.threat_coverage !== undefined && root.not_run !== undefined) {
		problems.push("threat_coverage sits beside scan, so a not_run record holds none");
	}

	if (root.not_run !== undefined) {
		const notRun = object(root.not_run, "not_run");
		const record: ScanRecord = {
			kind: "not-run",
			reason: text(notRun.reason, "not_run.reason"),
			at: timestamp(notRun.at, "not_run.at"),
		};
		return problems.length > 0 ? { problems } : { record };
	}

	const rawScan = object(root.scan, "scan");
	if (rawScan.scan_type !== "DIFF") {
		problems.push(`scan.scan_type is ${JSON.stringify(rawScan.scan_type)}; this gate reads a DIFF scan`);
	}
	const scan: Scan = {
		scan_id: text(rawScan.scan_id, "scan.scan_id"),
		base_ref: text(rawScan.base_ref, "scan.base_ref"),
		status: oneOf(rawScan.status, "scan.status", SCAN_STATUSES),
		region: text(rawScan.region, "scan.region"),
		mcp_server: text(rawScan.mcp_server, "scan.mcp_server"),
	};
	if (rawScan.completed_at !== undefined || scan.status === "COMPLETED") {
		scan.completed_at = timestamp(rawScan.completed_at, "scan.completed_at");
	}

	const findings = list(root.findings, "findings").map((input, index): Finding => {
		const at = `findings[${index}]`;
		const raw = object(input, at);
		const finding: Finding = {
			finding_id: text(raw.finding_id, `${at}.finding_id`),
			name: text(raw.name, `${at}.name`),
			risk_level: oneOf(raw.risk_level, `${at}.risk_level`, RISK_LEVELS),
			status: oneOf(raw.status, `${at}.status`, FINDING_STATUSES),
			code_locations: (raw.code_locations === undefined ? [] : list(raw.code_locations, `${at}.code_locations`)).map(
				(location, place): CodeLocation => {
					const where = `${at}.code_locations[${place}]`;
					const rawLocation = object(location, where);
					return {
						file_path: text(rawLocation.file_path, `${where}.file_path`),
						line_start: optionalLine(rawLocation.line_start, `${where}.line_start`),
						line_end: optionalLine(rawLocation.line_end, `${where}.line_end`),
					};
				},
			),
		};
		if (raw.override !== undefined) {
			const override = object(raw.override, `${at}.override`);
			finding.override = {
				by: text(override.by, `${at}.override.by`, false),
				reason: text(override.reason, `${at}.override.reason`, false),
				at: text(override.at, `${at}.override.at`, false),
			};
		}
		return finding;
	});

	return problems.length > 0
		? { problems }
		: { record: { kind: "scanned", scan, findings, threat_coverage: root.threat_coverage } };
}

function overrideProblem(override: Override): string | null {
	if (override.by.trim() === "") return "names no one in `by`";
	if (override.reason.trim() === "") return "gives no `reason`";
	if (!isTimestamp(override.at)) return `has an \`at\` ("${override.at}") that is not an ISO-8601 time`;
	return null;
}

function describe(finding: Finding): string {
	const location = finding.code_locations[0];
	const lines =
		location?.line_start === undefined
			? ""
			: location.line_end === undefined || location.line_end === location.line_start
				? `:${location.line_start}`
				: `:${location.line_start}-${location.line_end}`;
	const where = location === undefined ? "" : ` at ${location.file_path}${lines}`;
	return `${finding.finding_id} (${finding.risk_level}) ${finding.name}${where}`;
}

function decide(
	record: ScanRecord,
	threshold: Threshold,
	mode: OverrideMode,
): { blocking: string[]; overrides: string[] } {
	if (record.kind === "not-run") {
		return {
			blocking: [
				`No diff scan ran for this unit: ${record.reason} (recorded ${record.at}). The gate needs a COMPLETED scan: scan the unit, or the person can override the gate.`,
			],
			overrides: [],
		};
	}
	const blocking: string[] = [];
	const overrides: string[] = [];
	if (record.scan.status !== "COMPLETED") {
		blocking.push(
			`Diff scan ${record.scan.scan_id} is ${record.scan.status}, not COMPLETED. An unfinished scan is no evidence: wait for it to complete, or scan again, then write the record again.`,
		);
	}
	for (const finding of record.findings) {
		if (RISK_RANK[finding.risk_level] < RISK_RANK[threshold] || finding.status === "RESOLVED") continue;
		const label = describe(finding);
		if (mode === "strict") {
			blocking.push(
				finding.override === undefined
					? `${label} is ${finding.status}. ${ACCEPT_AT_GATE}`
					: `${label} is ${finding.status}. The gate ignores its override in the record, because the override mode is strict unless the project's ${CONFIG_FILE} sets it to lenient. ${ACCEPT_AT_GATE}`,
			);
			continue;
		}
		if (finding.override === undefined) {
			blocking.push(
				`${label} is ${finding.status}. Fix it and scan again, or record the person's decision to accept the risk.`,
			);
			continue;
		}
		const problem = overrideProblem(finding.override);
		if (problem !== null) {
			blocking.push(`${label} still blocks: its override ${problem}.`);
			continue;
		}
		const { by, at, reason } = finding.override;
		overrides.push(`${label}: accepted by ${by} at ${at}. Reason: ${reason}`);
	}
	return { blocking, overrides };
}

// Code Generation writes the record to <record>/construction/<unit>/code-generation/,
// or to <record>/construction/code-generation/ when the plan has no units. The
// unit layout is tried first, so a unit named construction still finds <record>.
function threatModelPath(recordPath: string): string | null {
	const folder = dirname(recordPath);
	const construction = [dirname(dirname(folder)), dirname(folder)].find((dir) => basename(dir) === "construction");
	return construction === undefined
		? null
		: join(dirname(construction), "inception", "security-threat-model", THREAT_MODEL_FILE);
}

function parseThreatModel(value: unknown): { model: ThreatModel } | { problems: string[] } {
	const problems: string[] = [];
	const { object, list, text } = fieldReader(problems);
	const root = object(value, "the record");
	if (root.schema_version !== 1 && root.schema_version !== 2) {
		problems.push(`schema_version is ${JSON.stringify(root.schema_version)}; this gate reads version 1 or 2`);
	}
	const scan_id = text(object(root.scan, "scan").scan_id, "scan.scan_id");
	const threats = list(root.threats, "threats").map((input, index): Threat => {
		const at = `threats[${index}]`;
		const raw = object(input, at);
		return {
			threat_id: text(raw.threat_id, `${at}.threat_id`),
			severity: text(raw.severity, `${at}.severity`),
			statement: typeof raw.statement === "string" ? raw.statement : "",
		};
	});
	threats.forEach(({ threat_id }, index) => {
		if (threat_id !== "" && threats.findIndex((threat) => threat.threat_id === threat_id) < index) {
			problems.push(`threats[${index}].threat_id repeats ${threat_id}`);
		}
	});
	return problems.length > 0 ? { problems } : { model: { scan_id, threats } };
}

// No threat model means the plan skipped the stage, so nothing is required.
function readThreatModel(recordPath: string): ThreatModelSetting {
	const path = threatModelPath(recordPath);
	if (path === null) return { model: null };
	const problem = (what: string): ThreatModelSetting => ({
		problem: `${THREAT_MODEL_FILE}: ${what}. The gate cannot tell which threats need evidence.`,
	});
	let markdown: string;
	try {
		markdown = readFileSync(path, "utf-8");
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return { model: null };
		return problem(`it cannot be read (${message(error)})`);
	}
	const block = recordJson(markdown);
	if ("problem" in block) return problem(block.problem);
	const parsed = parseThreatModel(block.value);
	return "problems" in parsed ? problem(parsed.problems.join("; ")) : parsed;
}

function parseCoverage(value: unknown): { coverage: ThreatCoverage } | { problems: string[] } {
	const problems: string[] = [];
	const { object, list, text, variant, optionalLine } = fieldReader(problems);
	const evidence = (input: unknown, at: string): Evidence[] => {
		const raw = object(input, at);
		switch (variant(raw.kind, `${at}.kind`, EVIDENCE_KINDS)) {
			case "code":
				return [
					{
						kind: "code",
						file_path: text(raw.file_path, `${at}.file_path`, false),
						line_start: optionalLine(raw.line_start, `${at}.line_start`),
						line_end: optionalLine(raw.line_end, `${at}.line_end`),
					},
				];
			case "test":
				return [
					{
						kind: "test",
						file_path: text(raw.file_path, `${at}.file_path`, false),
						name: raw.name === undefined ? undefined : text(raw.name, `${at}.name`, false),
					},
				];
			case "finding":
				return [{ kind: "finding", finding_id: text(raw.finding_id, `${at}.finding_id`) }];
			case null:
				return [];
		}
	};
	const entry = (input: unknown, at: string): CoverageEntry[] => {
		const raw = object(input, at);
		const threat_id = text(raw.threat_id, `${at}.threat_id`);
		switch (variant(raw.status, `${at}.status`, COVERAGE_STATUSES)) {
			case "MITIGATED": {
				const items = list(raw.evidence, `${at}.evidence`);
				return [
					{
						threat_id,
						status: "MITIGATED",
						evidence: items.flatMap((item, place) => evidence(item, `${at}.evidence[${place}]`)),
					},
				];
			}
			case "ACCEPTED": {
				const override = object(raw.override, `${at}.override`);
				return [
					{
						threat_id,
						status: "ACCEPTED",
						override: {
							by: text(override.by, `${at}.override.by`, false),
							reason: text(override.reason, `${at}.override.reason`, false),
							at: text(override.at, `${at}.override.at`, false),
						},
					},
				];
			}
			case "NOT_APPLICABLE":
				return [{ threat_id, status: "NOT_APPLICABLE", reason: text(raw.reason, `${at}.reason`, false) }];
			case null:
				return [];
		}
	};
	const root = object(value, "threat_coverage");
	const threat_model_scan_id = text(root.threat_model_scan_id, "threat_coverage.threat_model_scan_id");
	const threats = list(root.threats, "threat_coverage.threats").flatMap((input, index) =>
		entry(input, `threat_coverage.threats[${index}]`),
	);
	return problems.length > 0 ? { problems } : { coverage: { threat_model_scan_id, threats } };
}

// A severity outside the known levels ranks with UNKNOWN, for the same reason:
// it is no evidence that the threat is minor.
function rank(severity: string): number {
	return isOneOf(RISK_LEVELS, severity) ? RISK_RANK[severity] : RISK_RANK.UNKNOWN;
}

function describeThreat(threat: Threat): string {
	const statement = threat.statement.trim().replace(/\.$/, "");
	// The character past the limit shows whether the cut falls between two words.
	const brief = statement.length > 80 ? `${statement.slice(0, 81).replace(/\s+\S*$/, "")}...` : statement;
	return `${threat.threat_id} (${threat.severity})${brief === "" ? "" : ` ${brief}`}`;
}

// The gate never opens an evidence file: the unit's code can live in a Bolt
// worktree, not under the project root the gate runs in.
function evidenceProblem(item: Evidence, findingIds: Set<string>): string | null {
	if (item.kind === "finding") {
		return findingIds.has(item.finding_id)
			? null
			: `its evidence cites finding ${item.finding_id}, which this record's findings do not hold.`;
	}
	if (item.file_path.trim() !== "" && !isAbsolute(item.file_path)) return null;
	return `its ${item.kind} evidence has file_path ${JSON.stringify(item.file_path)}. Use a path relative to the repository root.`;
}

function entryProblem(entry: CoverageEntry, findingIds: Set<string>, mode: OverrideMode): string | null {
	switch (entry.status) {
		case "MITIGATED":
			if (entry.evidence.length === 0) {
				return "MITIGATED with no evidence. Name the code, test or finding that shows its control.";
			}
			return entry.evidence.map((item) => evidenceProblem(item, findingIds)).find((problem) => problem !== null) ?? null;
		case "ACCEPTED": {
			if (mode === "strict") {
				return `ACCEPTED, but the gate ignores its override, because the override mode is strict unless the project's ${CONFIG_FILE} sets it to lenient. Under coverage_mode block, ${AT_THE_GATE}`;
			}
			const problem = overrideProblem(entry.override);
			return problem === null ? null : `ACCEPTED, but its override ${problem}.`;
		}
		case "NOT_APPLICABLE":
			return entry.reason.trim() === "" ? "NOT_APPLICABLE with no reason. Say why this unit does not touch it." : null;
	}
}

function coverageGaps(
	setting: ThreatModelSetting,
	record: ScannedRecord,
	threshold: Threshold,
	mode: OverrideMode,
): string[] {
	if ("problem" in setting) return [setting.problem];
	const { model } = setting;
	if (model === null) return [];
	const required = model.threats.filter((threat) => rank(threat.severity) >= RISK_RANK[threshold]);
	const gap = (threat: Threat, problem: string) => `${describeThreat(threat)}: ${problem}`;
	const uncovered = required.map((threat) => gap(threat, NO_EVIDENCE));
	if (record.threat_coverage === undefined) return uncovered;
	const parsed = parseCoverage(record.threat_coverage);
	if ("problems" in parsed) return [...parsed.problems.map((problem) => `${RECORD_FILE}: ${problem}.`), ...uncovered];
	const { coverage } = parsed;
	if (coverage.threat_model_scan_id !== model.scan_id) {
		return [
			`threat_coverage was written for another threat model: its threat_model_scan_id is ${coverage.threat_model_scan_id}, and the scan_id in ${THREAT_MODEL_FILE} is ${model.scan_id}. Write it again from the current threat model.`,
			...uncovered,
		];
	}
	const entries = new Map<string, CoverageEntry[]>();
	for (const entry of coverage.threats) entries.set(entry.threat_id, [...(entries.get(entry.threat_id) ?? []), entry]);
	const listed = new Set(model.threats.map((threat) => threat.threat_id));
	const gaps: string[] = [];
	for (const [threat_id, own] of entries) {
		if (!listed.has(threat_id)) {
			gaps.push(`threat_coverage names ${threat_id}, which ${THREAT_MODEL_FILE} does not list.`);
		} else if (own.length > 1) {
			gaps.push(`threat_coverage names ${threat_id} ${own.length} times. Keep one entry per threat.`);
		}
	}
	const findingIds = new Set(record.findings.map((finding) => finding.finding_id));
	for (const threat of required) {
		const own = entries.get(threat.threat_id) ?? [];
		// A threat named twice already has its gap from the loop above.
		const problem = own.length === 0 ? NO_EVIDENCE : own.length === 1 ? entryProblem(own[0], findingIds, mode) : null;
		if (problem !== null) gaps.push(gap(threat, problem));
	}
	return gaps;
}

// The gate fires this sensor on the record and on the unit's plan. The plan's
// fire proves a record exists beside it, so a unit that skipped the scan still
// stops the gate; the record's own fire judges what it says.
function evaluate(outputPath: string, threshold: string, setting: ConfigSetting): Verdict {
	const config = "config" in setting ? setting.config : null;
	const verdict = (blocking: string[], overrides: string[] = [], gaps: string[] = []): Verdict => {
		const findings = config?.coverage_mode === "block" ? [...blocking, ...gaps] : blocking;
		return {
			pass: findings.length === 0,
			findings,
			findings_count: findings.length,
			threshold,
			override_mode: config?.override_mode ?? null,
			overrides,
			coverage_mode: config?.coverage_mode ?? null,
			coverage_gaps: gaps,
		};
	};
	if (!isOneOf(THRESHOLDS, threshold)) {
		return verdict([`The gate's threshold "${threshold}" is not a risk level. Use one of ${THRESHOLDS.join(", ")}.`]);
	}
	if ("problem" in setting) return verdict([setting.problem]);
	const firedOnRecord = basename(outputPath) === RECORD_FILE;
	const recordPath = firedOnRecord ? outputPath : join(dirname(outputPath), RECORD_FILE);
	let markdown: string;
	try {
		markdown = readFileSync(recordPath, "utf-8");
	} catch {
		return verdict([
			`No security scan record at ${recordPath}. Code Generation's security step writes it after the code is generated.`,
		]);
	}
	if (!firedOnRecord) return verdict([]);

	const block = recordJson(markdown);
	if ("problem" in block) return verdict([`${RECORD_FILE}: ${block.problem}.`]);
	const parsed = parseRecord(block.value);
	if ("problems" in parsed) return verdict(parsed.problems.map((problem) => `${RECORD_FILE}: ${problem}.`));
	const { record } = parsed;
	const { override_mode, coverage_mode } = setting.config;
	const { blocking, overrides } = decide(record, threshold, override_mode);
	const gaps =
		record.kind === "scanned" && coverage_mode !== "off"
			? coverageGaps(readThreatModel(recordPath), record, threshold, override_mode)
			: [];
	return verdict(blocking, overrides, gaps);
}

function flagValue(argv: string[], flag: string): string | undefined {
	const index = argv.indexOf(flag);
	return index === -1 ? undefined : (argv[index + 1] ?? "");
}

export function main(argv: string[]): void {
	const outputPath = flagValue(argv, "--output-path");
	if (outputPath === undefined || outputPath === "") {
		process.stderr.write(
			"Usage: aidlc-sensor-security-findings-gate.ts --output-path <path> [--stage <slug>] [--threshold <level>]\n",
		);
		process.exitCode = 2;
		return;
	}
	const result = evaluate(outputPath, flagValue(argv, "--threshold") ?? DEFAULT_THRESHOLD, readConfig(process.cwd()));
	process.stdout.write(`${JSON.stringify(result)}\n`);
}

if (import.meta.main) main(process.argv.slice(2));
