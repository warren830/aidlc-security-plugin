# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-57ff77f1-b925-4854-a298-bb6e9a243f43` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-636f08f5-3bd6-483f-9c71-41c5c520ee3d | HIGH | CROSS_SITE_SCRIPTING: Reflected XSS: renderGreeting interpolates unescaped req.query.name into HTML response | src/greeting.ts:12 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-57ff77f1-b925-4854-a298-bb6e9a243f43",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:31:25Z"
  },
  "findings": [
    {
      "finding_id": "f-636f08f5-3bd6-483f-9c71-41c5c520ee3d",
      "name": "CROSS_SITE_SCRIPTING: Reflected XSS: renderGreeting interpolates unescaped req.query.name into HTML response",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/greeting.ts",
          "line_start": 12,
          "line_end": 15
        },
        {
          "file_path": "src/greeting.ts",
          "line_start": 13,
          "line_end": 13
        },
        {
          "file_path": "src/greeting.ts",
          "line_start": 14,
          "line_end": 14
        }
      ]
    }
  ]
}
```
