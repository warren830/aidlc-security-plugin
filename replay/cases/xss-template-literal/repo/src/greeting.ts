// Minimal Express-style handler that reflects a request parameter into the
// page. The vulnerable version interpolates the value straight into the HTML
// shell. Nothing here actually runs: the case is a static sample.
export interface Request {
	query: Record<string, string>;
}

export interface Response {
	send(body: string): void;
}

export function renderGreeting(req: Request, res: Response): void {
	const name = req.query.name ?? "";
	res.send(`<!doctype html><html><body><h1>Hello, ${name}!</h1></body></html>`);
}
