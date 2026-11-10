# Security threat model

Written by hand for this replay case. No AWS Security Agent threat model
review ran, so the IDs and the `scan_id` below come from no service.

## Scope

- `inception/requirements-analysis/requirements.md`
- `inception/domain-design/components.md`
- Review `hand-written`

## Threats

- T-001 (CRITICAL) A token whose header names alg none, or any algorithm but
  HS256, is accepted without a valid signature. STRIDE: spoofing. Component:
  auth-service. Recommendation: pin the algorithm and verify the signature
  before reading the claims.
- T-002 (HIGH) A token that has expired, or that another issuer signed or
  another service was meant to receive, is still accepted. STRIDE: spoofing,
  elevation of privilege. Component: auth-service. Recommendation: check
  `exp`, `iss` and `aud` on every token.
- T-003 (MEDIUM) The verifier's errors say which check failed, which helps an
  attacker probe it. STRIDE: information disclosure. Component: auth-service.
  Recommendation: return one error to the caller and log the detail.

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
