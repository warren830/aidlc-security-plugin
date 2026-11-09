# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-232b1e97-cc1e-4b00-88ee-6ca29bfa09a1` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-1550e6e6-d949-40a8-8e16-6c7adfd4512b | HIGH | OTHER: Hardcoded AWS credentials committed in new .mcp.json | .mcp.json:6 | ACTIVE |
| f-3a24368f-6a8d-4c30-818c-724488e1e12e | HIGH | DEFAULT_CREDENTIALS: AWS access key ID and secret key committed in plaintext in .mcp.json, exposing cloud credentials to anyone with repo access | .mcp.json:6 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-232b1e97-cc1e-4b00-88ee-6ca29bfa09a1",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:31:22Z"
  },
  "findings": [
    {
      "finding_id": "f-1550e6e6-d949-40a8-8e16-6c7adfd4512b",
      "name": "OTHER: Hardcoded AWS credentials committed in new .mcp.json",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".mcp.json",
          "line_start": 6,
          "line_end": 10
        }
      ]
    },
    {
      "finding_id": "f-3a24368f-6a8d-4c30-818c-724488e1e12e",
      "name": "DEFAULT_CREDENTIALS: AWS access key ID and secret key committed in plaintext in .mcp.json, exposing cloud credentials to anyone with repo access",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".mcp.json",
          "line_start": 6,
          "line_end": 10
        },
        {
          "file_path": ".mcp.json",
          "line_start": 4,
          "line_end": 5
        }
      ]
    }
  ]
}
```
