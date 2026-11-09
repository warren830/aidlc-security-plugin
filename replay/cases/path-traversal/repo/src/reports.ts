// Static sample of the unvalidated path-join pattern. The handler takes a
// user-supplied filename and reads it from a "reports" directory. With no
// containment check, a name like ../../etc/passwd escapes that directory.
import { readFile } from "node:fs/promises";
import { join } from "node:path";

const REPORTS_DIR = "/srv/app/reports";

export async function downloadReport(name: string): Promise<Buffer> {
	return readFile(join(REPORTS_DIR, name));
}
