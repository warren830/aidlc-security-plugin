# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-111aceb1-326e-472f-87f2-0d410f7a6b7d` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-0681b67b-b2fb-498f-8a06-f520a93c261c | HIGH | PRIVILEGE_ESCALATION: "Pwn request": pull_request_target workflow checks out untrusted PR head with contents:write token | .github/workflows/triage.yml:16 | ACTIVE |
| f-61cfe730-2786-47d2-9238-62716fae2176 | CRITICAL | COMMAND_INJECTION: GitHub Actions script injection: issue title interpolated into run: shell in privileged workflow | .github/workflows/triage.yml:19 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-111aceb1-326e-472f-87f2-0d410f7a6b7d",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:40:09Z"
  },
  "findings": [
    {
      "finding_id": "f-0681b67b-b2fb-498f-8a06-f520a93c261c",
      "name": "PRIVILEGE_ESCALATION: \"Pwn request\": pull_request_target workflow checks out untrusted PR head with contents:write token",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".github/workflows/triage.yml",
          "line_start": 16,
          "line_end": 18
        },
        {
          "file_path": ".github/workflows/triage.yml",
          "line_start": 3,
          "line_end": 10
        }
      ]
    },
    {
      "finding_id": "f-61cfe730-2786-47d2-9238-62716fae2176",
      "name": "COMMAND_INJECTION: GitHub Actions script injection: issue title interpolated into run: shell in privileged workflow",
      "risk_level": "CRITICAL",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".github/workflows/triage.yml",
          "line_start": 19,
          "line_end": 20
        },
        {
          "file_path": ".github/workflows/triage.yml",
          "line_start": 8,
          "line_end": 10
        }
      ]
    }
  ]
}
```
