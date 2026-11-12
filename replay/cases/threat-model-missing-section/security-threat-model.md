# Security threat model

Written by hand for this replay case. No AWS Security Agent threat model
review ran, so the IDs and the `scan_id` below come from no service.

## Scope

- `inception/requirements-analysis/requirements.md`
- `inception/domain-design/components.md`
- Review `hand-written`

## Assumptions

- A-001 Only auth-service and the token issuer, `https://auth.example.com`,
  hold the HS256 secret.
- A-002 Callers reach auth-service from outside the service, so any caller
  can send it a token that the caller made.

## Trust boundaries

- Caller to auth-service: the caller that presents a token on one side, and
  auth-service on the other.

## Asset flows

- Token: the issuer signs it, the caller sends it with each request, and
  auth-service verifies it. It crosses caller to auth-service.
- HS256 secret: the issuer and auth-service each hold it, and no request
  carries it. It crosses no trust boundary.
- auth-service, which each threat's record names as its impacted asset: the
  user and roles it reads from a token it accepts go to the code in the
  service that called it. They cross no trust boundary.

## Spoofing

- T-001 (CRITICAL) A token whose header names alg none, or any algorithm but
  HS256, is accepted without a valid signature. STRIDE: spoofing. Component:
  auth-service. Trust boundary: caller to auth-service. Recommendation: pin
  the algorithm and verify the signature before reading the claims.
- T-002 (HIGH) A token that has expired, or that another issuer signed or
  another service was meant to receive, is still accepted. STRIDE: spoofing,
  elevation of privilege. Component: auth-service. Trust boundary: caller to
  auth-service. Recommendation: check `exp`, `iss` and `aud` on every token.

## Tampering

The review found no tampering threat.

## Information disclosure

- T-003 (MEDIUM) The verifier's errors say which check failed, which helps an
  attacker probe it. STRIDE: information disclosure. Component: auth-service.
  Trust boundary: caller to auth-service. Recommendation: return one error to
  the caller and log the detail.

## Denial of service

The review found no denial of service threat.

## Elevation of privilege

- T-002. Its entry is under `## Spoofing`.

## Mitigations for Construction

- M-001 (T-001) Accept only HS256, and compare the HMAC with `timingSafeEqual`
  before parsing the claims.
- M-002 (T-002) Reject a token whose `exp` has passed, or whose `iss` or `aud`
  is not this service's.

## Record

```json
{
  "schema_version": 2,
  "scan": {
    "scan_id": "hand-written",
    "threat_model_id": "none: written by hand",
    "scan_type": "THREAT_MODEL",
    "status": "COMPLETED",
    "region": "none",
    "mcp_server": "none: written by hand for replay/",
    "completed_at": "2026-11-10T00:00:00Z",
    "specs": ["inception/requirements-analysis/requirements.md", "inception/domain-design/components.md"]
  },
  "threats": [
    {
      "threat_id": "T-001",
      "service_threat_id": "none: written by hand",
      "statement": "A token whose header names alg none, or any algorithm but HS256, is accepted without a valid signature.",
      "severity": "CRITICAL",
      "status": "OPEN",
      "stride": ["SPOOFING"],
      "impact": "Anyone can forge a token for any user and role.",
      "impacted_assets": ["auth-service"],
      "recommendation": "Pin the algorithm and verify the signature before reading the claims.",
      "components": ["auth-service"],
      "mitigations": [
        { "mitigation_id": "M-001", "control": "Accept only HS256, and compare the HMAC with timingSafeEqual before parsing the claims." }
      ]
    },
    {
      "threat_id": "T-002",
      "service_threat_id": "none: written by hand",
      "statement": "A token that has expired, or that another issuer signed or another service was meant to receive, is still accepted.",
      "severity": "HIGH",
      "status": "OPEN",
      "stride": ["SPOOFING", "ELEVATION_OF_PRIVILEGE"],
      "impact": "A leaked or replayed token keeps working after it should not.",
      "impacted_assets": ["auth-service"],
      "recommendation": "Check exp, iss and aud on every token.",
      "components": ["auth-service"],
      "mitigations": [
        { "mitigation_id": "M-002", "control": "Reject a token whose exp has passed, or whose iss or aud is not this service's." }
      ]
    },
    {
      "threat_id": "T-003",
      "service_threat_id": "none: written by hand",
      "statement": "The verifier's errors say which check failed, which helps an attacker probe it.",
      "severity": "MEDIUM",
      "status": "OPEN",
      "stride": ["INFORMATION_DISCLOSURE"],
      "impact": "An attacker learns which part of a forged token to change next.",
      "impacted_assets": ["auth-service"],
      "recommendation": "Return one error to the caller and log the detail.",
      "components": ["auth-service"],
      "mitigations": []
    }
  ]
}
```
