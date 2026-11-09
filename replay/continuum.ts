// Runs each case through a real AWS Continuum differential code review (the
// securityagent API the AWS-9 Action calls) and writes what it found to the
// case's security-scan-result.md, in the record shape the plugin's gate reads.
// run.ts then gates every case on that record offline, so CI replays the real
// Continuum output through the real gate without calling AWS.
//
// It starts code review jobs in your AWS account, so CI never runs it. All the
// cases share one code review, `aidlc-replay`, whose source snapshot is an empty
// repository: each job's diff adds the whole of the case's repo/, so the review
// reads only the case. A finding's job ID stays valid for lookup while that
// code review exists.
//
// Usage: bun replay/continuum.ts --agent-space-id <id> --bucket <bucket connected to the space>
//          --service-role-arn <arn> [--region ap-southeast-1] [--case <id>]... [--concurrency 2]
//          [--timeout-minutes 30]
// Without --case it runs every case that has no record yet.
import { mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { REPO_ROOT } from "../scripts/upstream.ts";

const CASES = join(REPO_ROOT, "replay", "cases");
// The gate reads a record only under this name; any other path counts as a plan
// fire and blocks for the missing record.
export const CONTINUUM_RECORD = "security-scan-result.md";
const CODE_REVIEW_TITLE = "aidlc-replay";
const PREFIX = "aidlc-replay";
const DONE = new Set(["COMPLETED", "FAILED", "STOPPED"]);
const RETRYABLE = /ThrottlingException|ServiceQuotaExceededException|ConflictException|InternalServerException/;
// The service reports a path under its own checkout, sometimes inside a
// code_sc-<id>/ folder; the record keeps the path inside the case's repo/.
const SERVICE_ROOT = /^\/tmp\/opt\/source_code\/(?:code_sc-[^/]+\/)?/;

interface Options {
	agentSpaceId: string;
	bucket: string;
	serviceRoleArn: string;
	region: string;
	cases: string[];
	concurrency: number;
	timeoutMinutes: number;
}

interface ServiceFinding {
	findingId: string;
	name?: string;
	riskType?: string;
	riskLevel?: string;
	status?: string;
	confidence?: string;
	codeLocations?: { filePath?: string; lineStart?: number; lineEnd?: number }[];
}

function options(argv: string[]): Options {
	const values = (flag: string) => argv.flatMap((arg, index) => (arg === flag ? [argv[index + 1] ?? ""] : []));
	const one = (flag: string, fallback?: string): string => {
		const value = values(flag).at(-1) ?? fallback;
		if (!value) throw new Error(`${flag} is required`);
		return value;
	};
	const pending = readdirSync(CASES).filter(
		(id) => !readdirSync(join(CASES, id)).includes(CONTINUUM_RECORD),
	);
	return {
		agentSpaceId: one("--agent-space-id"),
		bucket: one("--bucket"),
		serviceRoleArn: one("--service-role-arn"),
		region: one("--region", "ap-southeast-1"),
		cases: values("--case").length > 0 ? values("--case") : pending,
		concurrency: Number(one("--concurrency", "2")),
		timeoutMinutes: Number(one("--timeout-minutes", "30")),
	};
}

const sleep = (seconds: number) => new Promise((resolve) => setTimeout(resolve, seconds * 1000));

async function aws(opts: Options, args: string[]): Promise<Record<string, unknown>> {
	const run = Bun.spawn(["aws", ...args, "--region", opts.region, "--output", "json"], {
		stdout: "pipe",
		stderr: "pipe",
		env: { ...process.env, AWS_PAGER: "" },
	});
	const [stdout, stderr, code] = await Promise.all([
		new Response(run.stdout).text(),
		new Response(run.stderr).text(),
		run.exited,
	]);
	if (code !== 0) throw new Error(`aws ${args.slice(0, 2).join(" ")}: ${stderr.trim()}`);
	return stdout.trim() === "" ? {} : (JSON.parse(stdout) as Record<string, unknown>);
}

async function exec(cmd: string[], cwd: string): Promise<{ code: number; stdout: string }> {
	const run = Bun.spawn(cmd, { cwd, stdout: "pipe", stderr: "inherit" });
	const [stdout, code] = await Promise.all([new Response(run.stdout).text(), run.exited]);
	return { code, stdout };
}

async function ensureCodeReview(opts: Options): Promise<string> {
	const listed = await aws(opts, ["securityagent", "list-code-reviews", "--agent-space-id", opts.agentSpaceId]);
	const reviews = (listed.codeReviewSummaries ?? []) as { codeReviewId: string; title: string }[];
	const existing = reviews.find((review) => review.title === CODE_REVIEW_TITLE);
	if (existing) return existing.codeReviewId;

	const scratch = mkdtempSync(join(tmpdir(), "aidlc-replay-base-"));
	try {
		writeFileSync(join(scratch, "README.md"), "Empty base for the aidlc-security-plugin replay cases.\n");
		await exec(["zip", "-q", "source.zip", "README.md"], scratch);
		const key = `${PREFIX}/base/source.zip`;
		await aws(opts, ["s3", "cp", "--only-show-errors", join(scratch, "source.zip"), `s3://${opts.bucket}/${key}`]);
		const created = await aws(opts, [
			"securityagent",
			"create-code-review",
			"--title",
			CODE_REVIEW_TITLE,
			"--agent-space-id",
			opts.agentSpaceId,
			"--assets",
			JSON.stringify({ sourceCode: [{ s3Location: `s3://${opts.bucket}/${key}` }] }),
			"--service-role",
			opts.serviceRoleArn,
		]);
		return created.codeReviewId as string;
	} finally {
		rmSync(scratch, { recursive: true, force: true });
	}
}

function repoFiles(dir: string, prefix = ""): string[] {
	return readdirSync(join(dir, prefix), { withFileTypes: true }).flatMap((entry) => {
		const path = prefix === "" ? entry.name : `${prefix}/${entry.name}`;
		return entry.isDirectory() ? repoFiles(dir, path) : [path];
	});
}

// `git diff --no-index` exits 1 when the files differ, which they always do here.
async function caseDiff(id: string): Promise<string> {
	const repo = join(CASES, id, "repo");
	const parts: string[] = [];
	for (const file of repoFiles(repo).sort()) {
		const { code, stdout } = await exec(["git", "diff", "--no-index", "--", "/dev/null", file], repo);
		if (code !== 1) throw new Error(`git diff of ${id}/repo/${file} exited ${code}`);
		parts.push(stdout);
	}
	return parts.join("");
}

async function startJob(opts: Options, codeReviewId: string, s3Uri: string): Promise<string> {
	for (let attempt = 1; ; attempt++) {
		try {
			const started = await aws(opts, [
				"securityagent",
				"start-code-review-job",
				"--agent-space-id",
				opts.agentSpaceId,
				"--code-review-id",
				codeReviewId,
				"--diff-source",
				JSON.stringify({ s3Uri }),
			]);
			return started.codeReviewJobId as string;
		} catch (error) {
			if (attempt >= 30 || !RETRYABLE.test(String(error))) throw error;
			await sleep(60);
		}
	}
}

async function waitForJob(opts: Options, jobId: string): Promise<Record<string, unknown>> {
	const deadline = Date.now() + opts.timeoutMinutes * 60_000;
	for (;;) {
		const got = await aws(opts, [
			"securityagent",
			"batch-get-code-review-jobs",
			"--agent-space-id",
			opts.agentSpaceId,
			"--code-review-job-ids",
			jobId,
		]);
		const job = ((got.codeReviewJobs ?? []) as Record<string, unknown>[])[0];
		if (job && DONE.has(job.status as string)) return job;
		if (Date.now() > deadline) {
			await aws(opts, [
				"securityagent",
				"stop-code-review-job",
				"--agent-space-id",
				opts.agentSpaceId,
				"--code-review-job-id",
				jobId,
			]);
			throw new Error(`job ${jobId} did not finish in ${opts.timeoutMinutes} minutes; stopped it`);
		}
		await sleep(30);
	}
}

async function jobFindings(opts: Options, jobId: string): Promise<ServiceFinding[]> {
	const ids: string[] = [];
	let nextToken: string | undefined;
	do {
		const page = await aws(opts, [
			"securityagent",
			"list-findings",
			"--agent-space-id",
			opts.agentSpaceId,
			"--code-review-job-id",
			jobId,
			...(nextToken ? ["--next-token", nextToken] : []),
		]);
		ids.push(...((page.findingsSummaries ?? page.findings ?? []) as { findingId: string }[]).map((f) => f.findingId));
		nextToken = page.nextToken as string | undefined;
	} while (nextToken);
	const findings: ServiceFinding[] = [];
	for (let at = 0; at < ids.length; at += 20) {
		const got = await aws(opts, [
			"securityagent",
			"batch-get-findings",
			"--agent-space-id",
			opts.agentSpaceId,
			"--finding-ids",
			...ids.slice(at, at + 20),
		]);
		findings.push(...((got.findings ?? []) as ServiceFinding[]));
	}
	return findings.sort((a, b) => a.findingId.localeCompare(b.findingId));
}

function findingName(finding: ServiceFinding): string {
	const name = (finding.name ?? "").replace(/^\[[^\]]*\]\s*/, "").trim();
	return [finding.riskType, name].filter(Boolean).join(": ") || finding.findingId;
}

function recordMarkdown(opts: Options, jobId: string, job: Record<string, unknown>, findings: ServiceFinding[]): string {
	const mapped = findings.map((finding) => ({
		finding_id: finding.findingId,
		name: findingName(finding),
		risk_level: finding.riskLevel ?? "UNKNOWN",
		status: finding.status ?? "ACTIVE",
		confidence: finding.confidence ?? "UNKNOWN",
		code_locations: (finding.codeLocations ?? []).map((location) => ({
			file_path: (location.filePath ?? "").replace(SERVICE_ROOT, ""),
			...(location.lineStart === undefined ? {} : { line_start: location.lineStart }),
			...(location.lineEnd === undefined ? {} : { line_end: location.lineEnd }),
		})),
	}));
	const record = {
		schema_version: 1,
		scan: {
			scan_id: jobId,
			scan_type: "DIFF",
			base_ref: "empty repository",
			status: job.status,
			region: opts.region,
			mcp_server: "none: securityagent StartCodeReviewJob from replay/continuum.ts",
			completed_at: new Date(job.updatedAt as string).toISOString().replace(/\.\d{3}Z$/, "Z"),
		},
		findings: mapped,
	};
	const rows = mapped.map((finding) => {
		const where = finding.code_locations[0];
		const location = where ? `${where.file_path}${where.line_start === undefined ? "" : `:${where.line_start}`}` : "";
		return `| ${finding.finding_id} | ${finding.risk_level} | ${finding.name.replaceAll("|", "\\|")} | ${location} | ${finding.status} |`;
	});
	return [
		"# Security scan",
		"",
		`Written by \`bun replay/continuum.ts\` from AWS Continuum code review job \`${jobId}\` in ${opts.region}.`,
		"Do not edit it by hand: run the script again to refresh it.",
		"",
		"| ID | Risk | Name | Location | Status |",
		"| --- | --- | --- | --- | --- |",
		...(rows.length > 0 ? rows : ["| | | No findings | | |"]),
		"",
		"```json",
		JSON.stringify(record, null, 2),
		"```",
		"",
	].join("\n");
}

async function runCase(opts: Options, codeReviewId: string, id: string): Promise<void> {
	const scratch = mkdtempSync(join(tmpdir(), `aidlc-replay-${id}-`));
	try {
		const patch = join(scratch, "case.patch");
		writeFileSync(patch, await caseDiff(id));
		const s3Uri = `s3://${opts.bucket}/${PREFIX}/${id}/${Date.now()}.patch`;
		await aws(opts, ["s3", "cp", "--only-show-errors", patch, s3Uri]);
		const jobId = await startJob(opts, codeReviewId, s3Uri);
		process.stdout.write(`${id}: started ${jobId}\n`);
		const job = await waitForJob(opts, jobId);
		if (job.status !== "COMPLETED") throw new Error(`${id}: job ${jobId} ended ${job.status}`);
		const findings = await jobFindings(opts, jobId);
		writeFileSync(join(CASES, id, CONTINUUM_RECORD), recordMarkdown(opts, jobId, job, findings));
		process.stdout.write(`${id}: ${jobId} completed with ${findings.length} findings\n`);
	} finally {
		rmSync(scratch, { recursive: true, force: true });
	}
}

if (import.meta.main) {
	const opts = options(process.argv.slice(2));
	const codeReviewId = await ensureCodeReview(opts);
	process.stdout.write(`code review ${codeReviewId}, cases: ${opts.cases.join(", ") || "(none)"}\n`);
	const queue = [...opts.cases];
	const failures: string[] = [];
	await Promise.all(
		Array.from({ length: opts.concurrency }, async () => {
			for (let id = queue.shift(); id !== undefined; id = queue.shift()) {
				await runCase(opts, codeReviewId, id).catch((error) => failures.push(String(error)));
			}
		}),
	);
	for (const failure of failures) process.stderr.write(`${failure}\n`);
	process.exit(failures.length > 0 ? 1 : 0);
}
