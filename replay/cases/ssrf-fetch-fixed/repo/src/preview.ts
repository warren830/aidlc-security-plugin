// Fixed version: the destination URL is parsed and checked against an
// explicit allowlist of public hosts and the http/https schemes. Requests
// for loopback, link-local, or any other internal destination fail closed,
// and so does a redirect, which would leave the checked host.
export interface PreviewRequest {
	body: { url: string };
}

export interface PreviewResponse {
	send(body: string): void;
}

const ALLOWED_HOSTS = new Set(["example.com", "cdn.example.com"]);

export async function previewLink(req: PreviewRequest, res: PreviewResponse): Promise<void> {
	const url = new URL(req.body.url);
	if (url.protocol !== "https:" || !ALLOWED_HOSTS.has(url.hostname)) {
		throw new Error("preview target is not on the allowlist");
	}
	const response = await fetch(url, { redirect: "error" });
	res.send(await response.text());
}
