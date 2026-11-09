// Fixed version: passwords go through scrypt with a per-user random salt
// and an explicit work factor. scrypt is designed to be expensive to brute
// -force, which is the property MD5 was missing.
import { randomBytes, scryptSync } from "node:crypto";

const SCRYPT_COST = 16384;

export function hashPassword(plain: string): string {
	const salt = randomBytes(16);
	const derived = scryptSync(plain, salt, 64, { N: SCRYPT_COST });
	return `scrypt:${SCRYPT_COST}:${salt.toString("base64url")}:${derived.toString("base64url")}`;
}
