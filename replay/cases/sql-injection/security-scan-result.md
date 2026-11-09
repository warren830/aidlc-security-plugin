# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-a92c256f-4a89-41de-957e-0228dac69d6d` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-dc04b1d9-e96a-4421-8edd-9659d380f7dc | HIGH | SQL_INJECTION: findUser interpolates untrusted `name` into SQL string literal (SQL injection) | src/users.ts:5 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-a92c256f-4a89-41de-957e-0228dac69d6d",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:21:04Z"
  },
  "findings": [
    {
      "finding_id": "f-dc04b1d9-e96a-4421-8edd-9659d380f7dc",
      "name": "SQL_INJECTION: findUser interpolates untrusted `name` into SQL string literal (SQL injection)",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/users.ts",
          "line_start": 5,
          "line_end": 7
        },
        {
          "file_path": "src/users.ts",
          "line_start": 1,
          "line_end": 3
        }
      ]
    }
  ]
}
```
