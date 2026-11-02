// Where this repository finds the aidlc-workflows checkout whose shipped plugin
// tools (validate, build, test) and test helpers it runs against. CI and people
// resolve it the same way: AIDLC_WORKFLOWS_DIR, else ../aidlc-workflows beside
// this repository.
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const PLUGIN_ROOT = join(REPO_ROOT, "security");

const TOOLS = join("dist", "claude", ".claude", "tools");

export function upstreamDir(): string {
	const dir = resolve(REPO_ROOT, process.env.AIDLC_WORKFLOWS_DIR ?? "../aidlc-workflows");
	if (!existsSync(join(dir, TOOLS, "aidlc-plugin-validate.ts"))) {
		throw new Error(
			`No built aidlc-workflows checkout at ${dir}. Clone https://github.com/awslabs/aidlc-workflows, ` +
				"run `bun install --frozen-lockfile` and `bun scripts/package.ts` in it, then set " +
				"AIDLC_WORKFLOWS_DIR to its path (the default is ../aidlc-workflows beside this repository).",
		);
	}
	return dir;
}

export function upstreamTool(name: string): string {
	return join(upstreamDir(), TOOLS, name);
}
