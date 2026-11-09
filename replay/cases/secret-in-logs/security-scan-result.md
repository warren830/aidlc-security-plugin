# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-9695a0cb-4178-40d9-8d6e-521cdfe589ce` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-270386cc-557d-491e-9298-ca7293ab93c7 | HIGH | INFORMATION_DISCLOSURE: Bearer token logged in plaintext via console.log in handleRequest (CWE-532) | src/handler.ts:9 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-9695a0cb-4178-40d9-8d6e-521cdfe589ce",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:03:17Z"
  },
  "findings": [
    {
      "finding_id": "f-270386cc-557d-491e-9298-ca7293ab93c7",
      "name": "INFORMATION_DISCLOSURE: Bearer token logged in plaintext via console.log in handleRequest (CWE-532)",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/handler.ts",
          "line_start": 9,
          "line_end": 11
        },
        {
          "file_path": "src/handler.ts",
          "line_start": 4,
          "line_end": 7
        }
      ]
    }
  ]
}
```
