// Runs every case in replay/cases/ against the detection this repository ships
// today, and writes replay/REPORT.md. Two probes, both offline:
//   - every security-category sensor, core's or the plugin's, whose `matches`
//     covers one of the case's files, fired on that file;
//   - the security-findings-gate worker on the case's recorded scan record.
// A case's measured result must equal the `expected` its expected.md declares,
// so a gap cannot be hidden by editing the report, and closing one fails the
// run until expected.md says so.
// Usage: bun replay/run.ts [--check]. --check also fails when REPORT.md is stale.
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";
import { PLUGIN_ROOT, REPO_ROOT, upstreamDir } from "../scripts/upstream.ts";

const REPLAY = join(REPO_ROOT, "replay");
const CASES = join(REPLAY, "cases");
const REPORT = join(REPLAY, "REPORT.md");
const GATE = join(PLUGIN_ROOT, "tools", "aidlc-sensor-security-findings-gate.ts");

const STAGES = { "threat-model": "威胁建模", "code-generation-gate": "代码生成门禁", ci: "CI" } as const;
const RESULTS = { detected: "检测到", "not-detected": "未检测到", "needs-aws": "需要 AWS" } as const;
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
	record?: string;
	gap_owner?: GapOwner;
}

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
	if (spec.record !== undefined && !existsSync(join(CASES, id, spec.record))) {
		problems.push(`record ${spec.record} does not exist`);
	}
	if (spec.expected === "not-detected" && !((spec.gap_owner ?? "") in GAP_OWNERS)) {
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
	let gateHolds = false;
	if (spec.record !== undefined) {
		const verdict = fire(GATE, join(dir, spec.record), dir);
		gateHolds = !verdict.pass;
		evidence.push(
			verdict.pass
				? "门禁放行了录制样本"
				: `门禁拦下录制样本：${verdict.findings.map((finding) => finding.split(". ")[0]).join("；")}`,
		);
	}
	const result: Result = detected ? "detected" : gateHolds ? "needs-aws" : "not-detected";
	return { result, evidence };
}

function cell(text: string): string {
	return text.replaceAll("|", "\\|").replaceAll("\n", " ");
}

function report(rows: { spec: Case; outcome: Outcome }[]): string {
	const table = rows.map(
		({ spec, outcome }) =>
			`| [${cell(spec.vector)}](cases/${spec.id}/expected.md) | ${STAGES[spec.stage]} | ${RESULTS[outcome.result]} | ${cell(outcome.evidence.join("；"))} |`,
	);
	const gaps = rows
		.filter(({ outcome }) => outcome.result === "not-detected")
		.map(({ spec }) => `- ${spec.vector}。建议补在：${GAP_OWNERS[spec.gap_owner as GapOwner]}。`);
	const counts = Object.entries(RESULTS)
		.map(([result, label]) => `${label} ${rows.filter(({ outcome }) => outcome.result === result).length}`)
		.join("，");
	return [
		"# 验证测试套件报告",
		"",
		"由 `bun replay/run.ts` 生成，不要手改。用例和预期见 `replay/cases/*/expected.md`。",
		"",
		`共 ${rows.length} 个用例：${counts}。`,
		"",
		"| 测试向量 | 检测环节 | 当前结果 | 证据 |",
		"| --- | --- | --- | --- |",
		...table,
		"",
		"## 未检测到",
		"",
		...(gaps.length > 0 ? gaps : ["无。"]),
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
