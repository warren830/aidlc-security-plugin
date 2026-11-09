// Static sample of an SSRF sink: the handler takes a URL from the request
// body and fetches it server-side without validating the destination. With
// no allowlist, an attacker can point the fetch at internal-only services.
export interface PreviewRequest {
	body: { url: string };
}

export interface PreviewResponse {
	send(body: string): void;
}

export async function previewLink(req: PreviewRequest, res: PreviewResponse): Promise<void> {
	const target = req.body.url;
	const response = await fetch(target);
	res.send(await response.text());
}
