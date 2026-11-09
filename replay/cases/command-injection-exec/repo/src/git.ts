// Static sample of the classic exec-with-template-literal pattern. The
// vulnerable version hands a shell a single interpolated string, so any
// shell metacharacters in the user-controlled `branch` would be evaluated.
import { exec } from "node:child_process";

export function checkoutBranch(branch: string): Promise<string> {
	return new Promise((resolve, reject) => {
		exec(`git checkout ${branch}`, (error, stdout) => {
			if (error) reject(error);
			else resolve(stdout);
		});
	});
}
