// Static sample of a handler that logs the whole request context, including
// the bearer token the client used. Application logs are usually shipped to
// a shared aggregator, so this effectively leaks the credential.
export interface AuthContext {
	user: string;
	token: string;
}

export function handleRequest(ctx: AuthContext): void {
	console.log("incoming request", { user: ctx.user, token: ctx.token });
	// ... business logic would go here; the sample is a static fixture.
}
