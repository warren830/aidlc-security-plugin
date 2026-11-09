// Fixed version: only non-sensitive identifiers reach the log line. The
// bearer token is replaced with a short, obviously-masked placeholder so
// the log entry still shows that authentication happened without leaking
// the credential itself.
export interface AuthContext {
	user: string;
	token: string;
}

function maskToken(token: string): string {
	return token.length <= 4 ? "****" : `****${token.slice(-4)}`;
}

export function handleRequest(ctx: AuthContext): void {
	console.log("incoming request", { user: ctx.user, token: maskToken(ctx.token) });
	// ... business logic would go here; the sample is a static fixture.
}
