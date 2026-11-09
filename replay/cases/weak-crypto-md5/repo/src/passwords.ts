// Static sample of MD5 being used as a password hash. MD5 is a fast general
// -purpose digest: it is unsalted and cheap to brute-force, so an attacker
// who reads the table can recover weak passwords offline.
import { createHash } from "node:crypto";

export function hashPassword(plain: string): string {
	return createHash("md5").update(plain).digest("hex");
}
