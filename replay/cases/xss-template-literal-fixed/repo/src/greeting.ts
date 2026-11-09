// Fixed version: user input goes through a tiny HTML-escaping helper so any
// markup in `name` becomes inert text. Same public surface as the vulnerable
// variant; only the escaping differs.
export interface Request {
	query: Record<string, string>;
}

export interface Response {
	send(body: string): void;
}

function escapeHtml(value: string): string {
	return value.replace(/[&<>"']/g, (ch) => {
		switch (ch) {
			case "&":
				return "&amp;";
			case "<":
				return "&lt;";
			case ">":
				return "&gt;";
			case '"':
				return "&quot;";
			default:
				return "&#39;";
		}
	});
}

export function renderGreeting(req: Request, res: Response): void {
	const name = escapeHtml(req.query.name ?? "");
	res.send(`<!doctype html><html><body><h1>Hello, ${name}!</h1></body></html>`);
}
