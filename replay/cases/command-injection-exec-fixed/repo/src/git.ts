// Fixed version: the same command runs without a shell. execFile takes the
// argument list as an array, so a branch name that contains spaces or shell
// metacharacters is passed as a literal argument instead of being parsed.
import { execFile } from "node:child_process";

export function checkoutBranch(branch: string): Promise<string> {
	return new Promise((resolve, reject) => {
		execFile("git", ["checkout", branch], (error, stdout) => {
			if (error) reject(error);
			else resolve(stdout);
		});
	});
}
