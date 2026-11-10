// The security plugin's content and composition: the shipped validator accepts
// the authored root, and each projection built by aidlc-plugin-build composes
// into a scratch install of that harness, both through aidlc-workflows'
// plugin-kit and through the shipped aidlc-plugin-test, with no compose drops.
// The install's own dispatcher then fires the gate check the way the gate
// does, to prove the check reads the project's override mode on a real fire.
import { afterAll, beforeAll, describe, expect, setDefaultTimeout, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { PLUGIN_ROOT, REPO_ROOT, upstreamDir } from "../scripts/upstream.ts";

setDefaultTimeout(900_000);

type Harness = "claude" | "kiro-ide";

interface PluginKit {
	validatePluginContent(pluginRoot: string): unknown[];
	copyHarnessInstall(harness: Harness, projectDir: string): string;
	composePluginFixture(options: {
		plugin: string;
		harness: Harness;
		projectDir: string;
		pluginBuilt: string;
	}): { projectDir: string; dropLogs: string };
}

interface GraphNode {
	slug: string;
	phase: string;
	lead_agent: string;
	scopes?: string[];
	produces?: string[];
	consumes?: { artifact: string; required: boolean }[];
	requires_stage?: string[];
	sensors_applicable?: {
		id: string;
		path: string;
		fire_on: string;
		default_severity: string;
		category?: string;
		matches?: string;
	}[];
}

const kit = (await import(join(upstreamDir(), "tests", "harness", "plugin-kit.ts"))) as PluginKit;

const HARNESS_DIR: Record<Harness, string> = { claude: ".claude", "kiro-ide": ".kiro" };
const TEMPLATE = join("tools", "data", "templates", "security-threat-model.md");

function pluginTool(...args: string[]): ReturnType<typeof spawnSync> {
	return spawnSync(process.execPath, [join(REPO_ROOT, "scripts", "plugin-tool.ts"), ...args], {
		cwd: REPO_ROOT,
		encoding: "utf-8",
	});
}

test("the shipped validator accepts the authored plugin root", () => {
	expect(kit.validatePluginContent(PLUGIN_ROOT)).toEqual([]);
});

// The agent writes the sections Step 6 lists, and required-sections checks the
// template's, so the two lists must not drift apart.
test("the threat model stage's Step 6 lists its template's sections, in order", () => {
	const stage = readFileSync(join(PLUGIN_ROOT, "stages", "inception", "security-threat-model.md"), "utf-8");
	const stepSix = /^### Step 6:[\s\S]*?(?=^### )/m.exec(stage)?.[0] ?? "";
	const named = [...stepSix.matchAll(/`(## [^`]+)`/g)].map(([, heading]) => heading.replace(/\s+/g, " "));
	const template = readFileSync(join(PLUGIN_ROOT, TEMPLATE), "utf-8");
	expect([...new Set(named)]).toEqual(template.match(/^## .+$/gm) ?? []);
});

for (const harness of ["claude", "kiro-ide"] as const) {
	describe(`${harness} projection`, () => {
		let scratch = "";
		let projection = "";
		let project = "";
		let installed = "";
		let graph: GraphNode[] = [];
		let dropLogs = "";

		beforeAll(() => {
			scratch = mkdtempSync(join(tmpdir(), `security-plugin-${harness}-`));
			projection = join(scratch, "projection");
			const build = pluginTool("build", PLUGIN_ROOT, harness, projection);
			if (build.status !== 0) throw new Error(`build failed: ${build.stderr}${build.stdout}`);
			const fixture = kit.composePluginFixture({
				plugin: "security",
				harness,
				projectDir: join(scratch, "composed"),
				pluginBuilt: projection,
			});
			dropLogs = fixture.dropLogs;
			project = fixture.projectDir;
			installed = join(project, HARNESS_DIR[harness]);
			graph = JSON.parse(readFileSync(join(installed, "tools", "data", "stage-graph.json"), "utf-8")) as GraphNode[];
		});

		afterAll(() => {
			if (scratch) rmSync(scratch, { recursive: true, force: true });
		});

		test("composes with an empty drop log", () => {
			expect(dropLogs).toBe("");
		});

		test("puts the threat model in Inception, led by the core DevSecOps agent", () => {
			const stage = graph.find((node) => node.slug === "security-threat-model");
			expect(stage?.phase).toBe("inception");
			expect(stage?.lead_agent).toBe("aidlc-devsecops-agent");
			expect(stage?.scopes).toEqual(["enterprise", "feature", "mvp", "classic", "workshop"]);
		});

		test("binds the blocking findings gate to Code Generation, which writes the scan record", () => {
			const stage = graph.find((node) => node.slug === "code-generation");
			expect(stage?.sensors_applicable).toContainEqual({
				id: "security-findings-gate",
				path: `${HARNESS_DIR[harness]}/sensors/aidlc-security-findings-gate.md`,
				fire_on: "gate",
				default_severity: "blocking",
				category: "security",
				matches: "**/code-generation/{code-generation-plan,security-scan-result}.md",
			});
			expect(stage?.produces).toContain("security-scan-result");
			expect(stage?.consumes).toContainEqual({ artifact: "security-threat-model", required: false });
			expect(stage?.requires_stage).toContain("security-threat-model");
		});

		const fixtures = join(REPO_ROOT, "tests", "fixtures");
		const placeRecord = (unit: string, fixture: string): string => {
			const record = join(project, "aidlc-docs", "construction", unit, "code-generation", "security-scan-result.md");
			mkdirSync(dirname(record), { recursive: true });
			copyFileSync(fixture, record);
			return record;
		};
		const useConfig = (name: string) =>
			copyFileSync(join(fixtures, "projects", name, ".aidlc-security.json"), join(project, ".aidlc-security.json"));
		const fire = (record: string): string => {
			const run = spawnSync(
				process.execPath,
				[
					join(installed, "tools", "aidlc-sensor.ts"),
					"fire",
					"security-findings-gate",
					"--stage",
					"code-generation",
					"--output-path",
					record,
				],
				{
					cwd: project,
					encoding: "utf-8",
					env: { ...process.env, AIDLC_PROJECT_DIR: project, CLAUDE_PROJECT_DIR: project },
				},
			);
			expect(run.status, `${run.stdout}${run.stderr}`).toBe(0);
			return (JSON.parse(run.stdout) as { result: string }).result;
		};

		test("the dispatcher's fire blocks a recorded override without a config, and passes it with a lenient one", () => {
			const record = placeRecord("unit-a", join(fixtures, "scan-records", "override-accepted", "security-scan-result.md"));
			expect(fire(record)).toBe("failed");
			useConfig("lenient");
			expect(fire(record)).toBe("passed");
		});

		test("the dispatcher's fire finds the threat model, and holds the gate on a threat with no evidence only in block mode", () => {
			const model = join(project, "aidlc-docs", "inception", "security-threat-model", "security-threat-model.md");
			mkdirSync(dirname(model), { recursive: true });
			copyFileSync(join(fixtures, "records", "threat-model", "inception", "security-threat-model", "security-threat-model.md"), model);
			const record = placeRecord("unit-b", join(fixtures, "scan-records", "clean", "security-scan-result.md"));
			useConfig("coverage-warn");
			expect(fire(record)).toBe("passed");
			useConfig("coverage-block");
			expect(fire(record)).toBe("failed");
		});

		test("gives the core DevSecOps agent the security baseline and the AWS Security Agent guidance", () => {
			const knowledge = join(installed, "knowledge", "aidlc-devsecops-agent");
			expect(readdirSync(knowledge)).toContain("security-baseline.md");
			expect(readFileSync(join(knowledge, "security-baseline.md"), "utf-8")).toContain("## SECURITY-15:");
			const persona = readFileSync(join(installed, "agents", "aidlc-devsecops-agent.md"), "utf-8");
			expect(persona).toContain("**AWS writes need the person's yes (security plugin).**");
			expect(persona).toContain("## AWS Security Agent (security plugin)");
		});

		test("passes the shipped aidlc-plugin-test against a scratch install", () => {
			const install = kit.copyHarnessInstall(harness, join(scratch, "install"));
			const run = pluginTool("test", PLUGIN_ROOT, "--install", install, "--harness", harness);
			expect(run.status, `${run.stdout}${run.stderr}`).toBe(0);
		});
	});
}
