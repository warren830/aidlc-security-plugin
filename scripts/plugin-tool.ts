// Runs one of the AI-DLC plugin authoring tools (aidlc-plugin-<verb>.ts) from the
// upstream checkout with the given arguments, so `bun run validate` and CI run the
// same command. Usage: bun scripts/plugin-tool.ts <create|validate|build|test> [args...]
import { spawnSync } from "node:child_process";
import { upstreamTool } from "./upstream.ts";

const VERBS = new Set(["create", "validate", "build", "test"]);

const [verb, ...args] = process.argv.slice(2);
if (verb === undefined || !VERBS.has(verb)) {
	process.stderr.write("Usage: bun scripts/plugin-tool.ts <create|validate|build|test> [args...]\n");
	process.exit(2);
}

let tool: string;
try {
	tool = upstreamTool(`aidlc-plugin-${verb}.ts`);
} catch (error) {
	process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
	process.exit(2);
}

const run = spawnSync(process.execPath, [tool, ...args], { stdio: "inherit" });
process.exit(run.status ?? 1);
