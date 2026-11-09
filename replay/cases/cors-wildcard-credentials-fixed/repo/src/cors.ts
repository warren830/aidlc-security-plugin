// Fixed version: the response echoes only an explicitly allow-listed
// origin. Requests from anywhere else get no CORS headers at all, so the
// browser blocks the cross-origin read. Credentials stay enabled because
// the legitimate SPA at app.example.com needs them.
export interface CorsResponse {
	setHeader(name: string, value: string): void;
	end(): void;
}

export interface CorsRequest {
	headers: Record<string, string | undefined>;
}

const ALLOWED_ORIGINS = new Set(["https://app.example.com"]);

export function handlePreflight(req: CorsRequest, res: CorsResponse): void {
	const origin = req.headers.origin;
	if (origin && ALLOWED_ORIGINS.has(origin)) {
		res.setHeader("Access-Control-Allow-Origin", origin);
		res.setHeader("Access-Control-Allow-Credentials", "true");
		res.setHeader("Access-Control-Allow-Methods", "GET, POST");
	}
	res.end();
}
