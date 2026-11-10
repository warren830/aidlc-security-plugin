# Security threat model

## Scope

- `inception/requirements-analysis/requirements.md`
- `inception/domain-design/components.md`
- Review `scan-tm-1a2b3c4d`

## Threats

- T-001 (CRITICAL) A token whose header says alg none is accepted without a signature. Component: auth-service.
- T-002 (HIGH) An expired token, or one issued for another service, is still accepted. Component: auth-service.
- T-003 (HIGH) Session tokens are written to the access log. Component: api-gateway.
- T-004 (MEDIUM) Error responses name the check that failed. Component: auth-service.
- T-005 (LOW) The login form sets no autocomplete hint. Component: web-ui.

## Mitigations for Construction

- M-001 (T-001) Pin the algorithm to HS256 and verify the signature before reading any claim.
- M-002 (T-002) Reject a token whose exp has passed, or whose iss or aud is not this service.
- M-003 (T-003) Log the token's subject, never the token.

## Record

```json
{
  "schema_version": 2,
  "scan": {
    "scan_id": "scan-tm-1a2b3c4d",
    "threat_model_id": "tm-5e6f",
    "scan_type": "THREAT_MODEL",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "awslabs.security-agent-mcp-server@0.2.1",
    "completed_at": "2026-11-02T08:15:00Z",
    "specs": ["inception/requirements-analysis/requirements.md", "inception/domain-design/components.md"]
  },
  "threats": [
    {
      "threat_id": "T-001",
      "service_threat_id": "th-9f1c",
      "statement": "A token whose header says alg none is accepted without a signature.",
      "severity": "CRITICAL",
      "status": "OPEN",
      "stride": ["SPOOFING"],
      "components": ["auth-service"],
      "mitigations": [{ "mitigation_id": "M-001", "control": "Pin the algorithm to HS256 and verify the signature before reading any claim." }]
    },
    {
      "threat_id": "T-002",
      "service_threat_id": "th-27ab",
      "statement": "An expired token, or one issued for another service, is still accepted.",
      "severity": "HIGH",
      "status": "OPEN",
      "stride": ["SPOOFING", "ELEVATION_OF_PRIVILEGE"],
      "components": ["auth-service"],
      "mitigations": [{ "mitigation_id": "M-002", "control": "Reject a token whose exp has passed, or whose iss or aud is not this service." }]
    },
    {
      "threat_id": "T-003",
      "service_threat_id": "th-3c40",
      "statement": "Session tokens are written to the access log.",
      "severity": "HIGH",
      "status": "OPEN",
      "stride": ["INFORMATION_DISCLOSURE"],
      "components": ["api-gateway"],
      "mitigations": [{ "mitigation_id": "M-003", "control": "Log the token's subject, never the token." }]
    },
    {
      "threat_id": "T-004",
      "service_threat_id": "th-4d51",
      "statement": "Error responses name the check that failed.",
      "severity": "MEDIUM",
      "status": "OPEN",
      "stride": ["INFORMATION_DISCLOSURE"],
      "components": ["auth-service"],
      "mitigations": []
    },
    {
      "threat_id": "T-005",
      "service_threat_id": "th-5e62",
      "statement": "The login form sets no autocomplete hint.",
      "severity": "LOW",
      "status": "OPEN",
      "stride": ["INFORMATION_DISCLOSURE"],
      "components": ["web-ui"],
      "mitigations": []
    }
  ]
}
```
