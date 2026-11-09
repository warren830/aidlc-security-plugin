// Fixed version: the user-supplied name is resolved against the reports
// directory, then the resolved path is checked to still sit inside it.
// Any `..` segment that escapes the root causes the request to fail closed.
import { readFile } from "node:fs/promises";
import { resolve, sep } from "node:path";

const REPORTS_DIR = "/srv/app/reports";

export async function downloadReport(name: string): Promise<Buffer> {
	const target = resolve(REPORTS_DIR, name);
	if (!target.startsWith(REPORTS_DIR + sep)) {
		throw new Error("report path escapes the reports directory");
	}
	return readFile(target);
}
