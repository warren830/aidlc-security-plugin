# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-3c3a44b9-a4b6-4797-8dbc-79c15588026a` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-47bdc83e-84a6-4a8d-a6e9-962dc297fa0c | LOW | SECURITY_MISCONFIGURATION: Dockerfile chowns all of /app to the runtime user, making application code writable at runtime (persistence/code tampering) | Dockerfile:12 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-3c3a44b9-a4b6-4797-8dbc-79c15588026a",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:24:45Z"
  },
  "findings": [
    {
      "finding_id": "f-47bdc83e-84a6-4a8d-a6e9-962dc297fa0c",
      "name": "SECURITY_MISCONFIGURATION: Dockerfile chowns all of /app to the runtime user, making application code writable at runtime (persistence/code tampering)",
      "risk_level": "LOW",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "Dockerfile",
          "line_start": 12,
          "line_end": 13
        },
        {
          "file_path": "Dockerfile",
          "line_start": 15,
          "line_end": 15
        }
      ]
    }
  ]
}
```
