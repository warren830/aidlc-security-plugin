// Runs every case in replay/cases/ against the detection this repository ships
// today, and writes replay/REPORT.md. Three probes, all offline:
//   - every security-category sensor, core's or the plugin's, whose `matches`
//     covers one of the case's files, fired on that file;
//   - the security-findings-gate worker on the case's security-scan-result.md,
//     the real AWS Continuum output that replay/continuum.ts recorded;
//   - for a case with threat-coverage.json, the same worker on that record
//     with the coverage merged in, beside the case's threat model.
// A case's measured result must equal the `expected` its expected.md declares,
// so a gap cannot be hidden by editing the report, and closing one fails the
// run until expected.md says so.
// Usage: bun replay/run.ts [--check]. --check also fails when REPORT.md is stale.
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";
import { PLUGIN_ROOT, REPO_ROOT, upstreamDir } from "../scripts/upstream.ts";
import { CONTINUUM_RECORD } from "./continuum.ts";

const REPLAY = join(REPO_ROOT, "replay");
const CASES = join(REPLAY, "cases");
const REPORT = join(REPLAY, "REPORT.md");
const GATE = join(PLUGIN_ROOT, "tools", "aidlc-sensor-security-findings-gate.ts");
const THREAT_MODEL = "security-threat-model.md";
const COVERAGE = "threat-coverage.json";

const STAGES = { "threat-model": "威胁建模", "code-generation-gate": "代码生成门禁", ci: "CI" } as const;
const RESULTS = {
	local: "本地检测到",
	continuum: "Continuum 检测到",
	coverage: "威胁覆盖检查拦下",
	"not-detected": "未检测到",
} as const;
const GAP_OWNERS = { plugin: "插件", action: "AWS-9 Action" } as const;
type Stage = keyof typeof STAGES;
type Result = keyof typeof RESULTS;
type GapOwner = keyof typeof GAP_OWNERS;
interface Case {
	id: string;
	vector: string;
	stage: Stage;
	expected: Result;
	sources: string[];
	files: string[];
	gap_owner?: GapOwner;
	// A paired case's counterpart: `<id>` has the vulnerability, `<id>-fixed`
	// is the same code with it removed, so the gate is scored on both.
	pair?: string;
}

const isFixed = (spec: Case) => spec.pair !== undefined && spec.id.endsWith("-fixed");

interface Sensor {
	id: string;
	matches: string;
	tool: string;
}

interface Outcome {
	result: Result;
	evidence: string[];
}

interface Verdict {
	pass: boolean;
	findings: string[];
	coverage_mode?: string | null;
}

interface ContinuumRecord {
	scan: { scan_id: string; region: string; completed_at: string };
	findings: { risk_level: string; name: string; code_locations: { file_path: string; line_start?: number }[] }[];
}

function frontmatter(markdown: string): Record<string, string> {
	const block = /^---\n([\s\S]*?)\n---/.exec(markdown)?.[1] ?? "";
	const fields: Record<string, string> = {};
	for (const line of block.split("\n")) {
		const field = /^([a-z_]+):\s*(.*)$/.exec(line);
		if (field) fields[field[1]] = field[2].replace(/^"(.*)"$/, "$1");
	}
	return fields;
}

// A sensor's command names its worker under {{HARNESS_DIR}}/tools/, which is
// the tools/ folder beside the manifest in the authored source.
function securitySensors(): Sensor[] {
	const roots = [join(upstreamDir(), "core"), PLUGIN_ROOT];
	return roots.flatMap((root) =>
		readdirSync(join(root, "sensors"))
			.filter((file) => file.endsWith(".md"))
			.map((file) => frontmatter(readFileSync(join(root, "sensors", file), "utf-8")))
			.filter((fields) => fields.category === "security" && fields.matches)
			.map((fields) => {
				const worker = /\{\{HARNESS_DIR\}\}\/tools\/(\S+\.ts)/.exec(fields.command ?? "")?.[1];
				if (worker === undefined) throw new Error(`sensor ${fields.id}: no worker in its command`);
				return { id: fields.id, matches: fields.matches, tool: join(root, "tools", worker) };
			}),
	);
}

function readCase(id: string): Case {
	const path = join(CASES, id, "expected.md");
	const blocks = [...readFileSync(path, "utf-8").matchAll(/^```json\n([\s\S]*?)\n```$/gm)];
	if (blocks.length !== 1) throw new Error(`${path}: needs exactly one json block, found ${blocks.length}`);
	const spec = { id, ...JSON.parse(blocks[0][1]) } as Case;
	const problems: string[] = [];
	if (!(spec.stage in STAGES)) problems.push(`stage "${spec.stage}" is not one of ${Object.keys(STAGES).join(", ")}`);
	if (!(spec.expected in RESULTS)) {
		problems.push(`expected "${spec.expected}" is not one of ${Object.keys(RESULTS).join(", ")}`);
	}
	if (!spec.sources?.length || !spec.sources.every((url) => url.startsWith("https://"))) {
		problems.push("sources must list the public https URLs of the scenario");
	}
	if (!spec.files?.length) problems.push("files must name the case's files under repo/");
	for (const file of spec.files ?? []) {
		if (!existsSync(join(CASES, id, "repo", file))) problems.push(`repo/${file} does not exist`);
	}
	if (!existsSync(join(CASES, id, CONTINUUM_RECORD))) {
		problems.push(`${CONTINUUM_RECORD} is missing. Run \`bun replay/continuum.ts --case ${id}\` (see replay/README.md)`);
	}
	if (existsSync(join(CASES, id, COVERAGE)) !== existsSync(join(CASES, id, THREAT_MODEL))) {
		problems.push(`${COVERAGE} and ${THREAT_MODEL} come together: the coverage names the threat model's threats`);
	}
	if (spec.pair !== undefined && spec.pair !== (id.endsWith("-fixed") ? id.slice(0, -"-fixed".length) : `${id}-fixed`)) {
		problems.push(`pair "${spec.pair}" must name ${id.endsWith("-fixed") ? "the case without -fixed" : `${id}-fixed`}`);
	}
	if (spec.pair !== undefined && !existsSync(join(CASES, spec.pair, "expected.md"))) {
		problems.push(`pair ${spec.pair} does not exist`);
	}
	if (spec.expected === "not-detected" && !isFixed(spec) && !((spec.gap_owner ?? "") in GAP_OWNERS)) {
		problems.push(`a not-detected case names its gap_owner: ${Object.keys(GAP_OWNERS).join(" or ")}`);
	}
	if (problems.length > 0) throw new Error(`${path}:\n  ${problems.join("\n  ")}`);
	return spec;
}

function fire(tool: string, outputPath: string, cwd: string): Verdict {
	const run = spawnSync(process.execPath, [tool, "--stage", "code-generation", "--output-path", outputPath], {
		cwd,
		encoding: "utf-8",
	});
	if (run.status !== 0) throw new Error(`${tool} exited ${run.status}: ${run.stderr}`);
	return JSON.parse(run.stdout) as Verdict;
}

const blockedBy = (findings: string[]) =>
	findings.map((finding) => /^\S+ \([A-Z]+\)/.exec(finding)?.[0] ?? finding.split(". ")[0]).join("、");

// The gate finds the threat model from the record's place in the record tree,
// so the case becomes one unit of a scratch record: the threat model under
// inception/, and the Continuum record, at schema_version 2 with the coverage
// merged in, under construction/<id>/code-generation/. The case's own record
// stays the service's output.
function fireCoverage(spec: Case, record: ContinuumRecord): Verdict | null {
	const dir = join(CASES, spec.id);
	if (!existsSync(join(dir, COVERAGE))) return null;
	const scratch = mkdtempSync(join(tmpdir(), "aidlc-replay-coverage-"));
	try {
		const model = join(scratch, "aidlc-docs", "inception", "security-threat-model", THREAT_MODEL);
		const unit = join(scratch, "aidlc-docs", "construction", spec.id, "code-generation", CONTINUUM_RECORD);
		mkdirSync(dirname(model), { recursive: true });
		mkdirSync(dirname(unit), { recursive: true });
		copyFileSync(join(dir, THREAT_MODEL), model);
		const threat_coverage: unknown = JSON.parse(readFileSync(join(dir, COVERAGE), "utf-8"));
		const json = JSON.stringify({ ...record, schema_version: 2, threat_coverage }, null, 2);
		writeFileSync(unit, `# Security scan\n\n\`\`\`json\n${json}\n\`\`\`\n`);
		return fire(GATE, unit, dir);
	} finally {
		rmSync(scratch, { recursive: true, force: true });
	}
}

function measure(spec: Case, sensors: Sensor[]): Outcome {
	const dir = join(CASES, spec.id);
	const repo = join(dir, "repo");
	const evidence: string[] = [];
	let detected = false;
	for (const file of spec.files) {
		const covering = sensors.filter((sensor) => new Bun.Glob(sensor.matches).match(file));
		if (covering.length === 0) evidence.push(`没有 security 类 sensor 覆盖 \`${file}\``);
		for (const sensor of covering) {
			const verdict = fire(sensor.tool, join(repo, file), repo);
			detected ||= !verdict.pass;
			evidence.push(`\`${sensor.id}\` 对 \`${file}\`：${verdict.pass ? "通过" : verdict.findings.join("；")}`);
		}
	}
	const recordPath = join(dir, CONTINUUM_RECORD);
	const record = JSON.parse(
		/^```json\n([\s\S]*?)\n```$/m.exec(readFileSync(recordPath, "utf-8"))?.[1] ?? "{}",
	) as ContinuumRecord;
	const reported = record.findings.map(({ risk_level, name, code_locations: [where] }) => {
		const location = where ? ` @ ${where.file_path}${where.line_start === undefined ? "" : `:${where.line_start}`}` : "";
		return `${risk_level} ${name.split(":")[0]}${location}`;
	});
	const verdict = fire(GATE, recordPath, dir);
	evidence.push(
		`Continuum \`${record.scan.scan_id}\`（${record.scan.region}，${record.scan.completed_at.slice(0, 10)}）报了 ${reported.length} 条${
			reported.length > 0 ? `：${reported.join("、")}` : ""
		}；门禁${verdict.pass ? "放行" : `拦下：${blockedBy(verdict.findings)}`}`,
	);
	const coverage = fireCoverage(spec, record);
	if (coverage !== null) {
		evidence.push(
			`威胁覆盖检查（coverage_mode ${coverage.coverage_mode}）${coverage.pass ? "放行" : `拦下：${blockedBy(coverage.findings)}`}`,
		);
	}
	const result: Result = detected
		? "local"
		: !verdict.pass
			? "continuum"
			: coverage?.pass === false
				? "coverage"
				: "not-detected";
	return { result, evidence };
}

function cell(text: string): string {
	return text.replaceAll("|", "\\|").replaceAll("\n", " ");
}

function report(rows: { spec: Case; outcome: Outcome }[]): string {
	const blocked = ({ outcome }: { outcome: Outcome }) => outcome.result !== "not-detected";
	const resultLabel = ({ spec, outcome }: { spec: Case; outcome: Outcome }) =>
		isFixed(spec) ? (blocked({ outcome }) ? "误拦（修好版）" : "放行（修好版）") : RESULTS[outcome.result];
	const table = rows.map(
		(row) =>
			`| [${cell(row.spec.vector)}](cases/${row.spec.id}/expected.md) | ${STAGES[row.spec.stage]} | ${resultLabel(row)} | ${cell(row.outcome.evidence.join("；"))} |`,
	);
	const problemRows = rows.filter(({ spec }) => !isFixed(spec));
	const fixedRows = rows.filter(({ spec }) => isFixed(spec));
	const caught = problemRows.filter(blocked).length;
	const falseAlarms = fixedRows.filter(blocked).length;
	const pairs = fixedRows.map((fixed) => {
		const problem = rows.find(({ spec }) => spec.id === fixed.spec.pair);
		return `| ${cell(problem?.spec.vector ?? fixed.spec.pair ?? "")} | ${problem ? resultLabel(problem) : "缺失"} | ${resultLabel(fixed)} |`;
	});
	const gaps = problemRows
		.filter((row) => !blocked(row))
		.map(({ spec }) => `- ${spec.vector}。建议补在：${GAP_OWNERS[spec.gap_owner as GapOwner]}。`);
	const wrong = fixedRows.filter(blocked).map(({ spec }) => `- ${spec.vector}。`);
	return [
		"# 验证测试套件报告",
		"",
		"由 `bun replay/run.ts` 生成，不要手改。用例和预期见 `replay/cases/*/expected.md`。",
		"Continuum 的结果来自 `bun replay/continuum.ts` 对真实 AWS Continuum 跑的差分 code review，记录在各用例的",
		"`security-scan-result.md`。CI 不调用 AWS，只用插件门禁重新判一遍这些真实记录。",
		"",
		`共 ${rows.length} 个用例：${problemRows.length} 个有问题的版本，${fixedRows.length} 个修好的版本。`,
		"",
		"## 拦截率和误报率",
		"",
		"| 指标 | 结果 |",
		"| --- | --- |",
		`| 拦截率：有问题的版本被拦下 | ${caught} / ${problemRows.length} |`,
		`| 误报率：修好的版本被误拦 | ${falseAlarms} / ${fixedRows.length} |`,
		"",
		...(pairs.length > 0 ? ["| 成对场景 | 有问题版 | 修好版 |", "| --- | --- | --- |", ...pairs, ""] : []),
		"## 全部用例",
		"",
		"| 测试向量 | 检测环节 | 当前结果 | 证据 |",
		"| --- | --- | --- | --- |",
		...table,
		"",
		"## 未检测到",
		"",
		...(gaps.length > 0 ? gaps : ["无。"]),
		"",
		"## 误拦",
		"",
		...(wrong.length > 0 ? wrong : ["无。"]),
		"",
	].join("\n");
}

const check = process.argv.includes("--check");
const sensors = securitySensors();
const rows = readdirSync(CASES, { withFileTypes: true })
	.filter((entry) => entry.isDirectory())
	.map((entry) => entry.name)
	.sort()
	.map((id) => {
		const spec = readCase(id);
		return { spec, outcome: measure(spec, sensors) };
	});

const failures = rows
	.filter(({ spec, outcome }) => outcome.result !== spec.expected)
	.map(
		({ spec, outcome }) =>
			`${spec.id}: measured ${outcome.result}, expected.md says ${spec.expected}. Fix the detection or update expected.md with the evidence.`,
	);
const text = report(rows);
if (check) {
	const current = existsSync(REPORT) ? readFileSync(REPORT, "utf-8") : "";
	if (current !== text) failures.push(`${relative(REPO_ROOT, REPORT)} is stale. Run \`bun replay/run.ts\` and commit it.`);
} else {
	writeFileSync(REPORT, text);
}
for (const failure of failures) process.stderr.write(`${failure}\n`);
process.stdout.write(`${rows.length} cases, ${failures.length} problems\n`);
process.exit(failures.length > 0 ? 1 : 0);
