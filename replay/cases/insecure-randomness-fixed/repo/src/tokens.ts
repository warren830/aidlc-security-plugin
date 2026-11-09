// Fixed version: tokens come from the platform CSPRNG. 32 bytes of entropy
// are base64url-encoded, which keeps the URL-safe alphabet without weakening
// the unpredictability of the token.
import { randomBytes } from "node:crypto";

export function generateResetToken(): string {
	return randomBytes(32).toString("base64url");
}
