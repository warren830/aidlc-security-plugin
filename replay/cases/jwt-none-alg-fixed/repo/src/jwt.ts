// Fixed version: the verifier pins a single expected algorithm (HS256) and
// re-computes the HMAC before looking at any claims. Tokens that switch to
// a different `alg`, including "none", are rejected before decoding. It then
// requires an unexpired token issued by and for this service.
import { createHmac, timingSafeEqual } from "node:crypto";

export interface DecodedToken {
	sub: string;
	roles: string[];
	exp: number;
	iss: string;
	aud: string;
}

interface Header {
	alg: string;
	typ: string;
}

const EXPECTED_ALG = "HS256";
const EXPECTED_ISSUER = "https://auth.example.com";
const EXPECTED_AUDIENCE = "example-api";

export function verifyJwt(token: string, secret: string): DecodedToken {
	const [headerPart, payloadPart, signaturePart] = token.split(".");
	if (!signaturePart) throw new Error("missing signature");
	const header = JSON.parse(Buffer.from(headerPart, "base64url").toString()) as Header;
	if (header.alg !== EXPECTED_ALG) throw new Error("unexpected JWT algorithm");
	const expected = createHmac("sha256", secret).update(`${headerPart}.${payloadPart}`).digest();
	const actual = Buffer.from(signaturePart, "base64url");
	if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
		throw new Error("invalid signature");
	}
	if (header.typ !== "JWT") throw new Error("unexpected token type");
	const claims = JSON.parse(Buffer.from(payloadPart, "base64url").toString()) as DecodedToken;
	if (typeof claims.exp !== "number" || claims.exp <= Math.floor(Date.now() / 1000)) {
		throw new Error("token expired");
	}
	if (claims.iss !== EXPECTED_ISSUER || claims.aud !== EXPECTED_AUDIENCE) {
		throw new Error("token was not issued for this service");
	}
	return claims;
}
