// Static sample of a CORS pre-flight responder that combines a wildcard
// origin with credentials. The browser refuses this combination for cookies
// but the intent (reflect any origin, allow cookies) is a common source of
// credential-leaking misconfigurations.
export interface CorsResponse {
	setHeader(name: string, value: string): void;
	end(): void;
}

export function handlePreflight(res: CorsResponse): void {
	res.setHeader("Access-Control-Allow-Origin", "*");
	res.setHeader("Access-Control-Allow-Credentials", "true");
	res.setHeader("Access-Control-Allow-Methods", "GET, POST");
	res.end();
}
