// The security plugin's content and composition: the shipped validator accepts
// the authored root, and each projection built by aidlc-plugin-build composes
// into a scratch install of that harness, both through aidlc-workflows'
// plugin-kit and through the shipped aidlc-plugin-test, with no compose drops.
import { afterAll, beforeAll, describe, expect, setDefaultTimeout, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
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

function pluginTool(...args: string[]): ReturnType<typeof spawnSync> {
	return spawnSync(process.execPath, [join(REPO_ROOT, "scripts", "plugin-tool.ts"), ...args], {
		cwd: REPO_ROOT,
		encoding: "utf-8",
	});
}

test("the shipped validator accepts the authored plugin root", () => {
	expect(kit.validatePluginContent(PLUGIN_ROOT)).toEqual([]);
});

for (const harness of ["claude", "kiro-ide"] as const) {
	describe(`${harness} projection`, () => {
		let scratch = "";
		let projection = "";
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
			installed = join(fixture.projectDir, HARNESS_DIR[harness]);
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
