// Static sample of a JWT verifier that trusts whatever `alg` the token
// header claims. An attacker can submit a token with `alg: "none"` and an
// empty signature, and the verifier below will accept it.
export interface DecodedToken {
	sub: string;
	roles: string[];
}

interface Header {
	alg: string;
}

export function verifyJwt(token: string, _secret: string): DecodedToken {
	const [headerPart, payloadPart] = token.split(".");
	const header = JSON.parse(Buffer.from(headerPart, "base64url").toString()) as Header;
	const payload = JSON.parse(Buffer.from(payloadPart, "base64url").toString()) as DecodedToken;
	// Vulnerable: any algorithm (including "none") is accepted as-is.
	if (header.alg === "none") return payload;
	// Real signature verification is intentionally omitted in this sample;
	// the point is the algorithm-confusion branch above.
	return payload;
}
