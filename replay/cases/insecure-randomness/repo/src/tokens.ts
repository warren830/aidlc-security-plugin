// Static sample of Math.random() being used to mint a password-reset token.
// The PRNG is not cryptographically secure, so the token space is predictable
// and much smaller than the call site assumes.
export function generateResetToken(): string {
	const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";
	let token = "";
	for (let i = 0; i < 32; i += 1) {
		token += alphabet[Math.floor(Math.random() * alphabet.length)];
	}
	return token;
}
