# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-4be8bd14-e60e-4448-a6b1-2094d21d4eb5` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-3222cd16-2c77-4fdf-8cec-0f4ebb8bf924 | HIGH | SERVER_SIDE_REQUEST_FORGERY: previewLink fetches attacker-controlled req.body.url with no validation (full-read SSRF) | src/preview.ts:12 | ACTIVE |
| f-d0305d03-af76-4836-aa17-ac1ce4f9458f | MEDIUM | CROSS_SITE_SCRIPTING: Remote response body echoed unescaped via res.send (reflected XSS) | src/preview.ts:15 | ACTIVE |
| f-e7fa4a06-6983-406d-8c26-fe25ebdb86e4 | HIGH | SERVER_SIDE_REQUEST_FORGERY: previewLink fetches unvalidated user-supplied URL server-side and returns the body (full SSRF) | src/preview.ts:12 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-4be8bd14-e60e-4448-a6b1-2094d21d4eb5",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:23:42Z"
  },
  "findings": [
    {
      "finding_id": "f-3222cd16-2c77-4fdf-8cec-0f4ebb8bf924",
      "name": "SERVER_SIDE_REQUEST_FORGERY: previewLink fetches attacker-controlled req.body.url with no validation (full-read SSRF)",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/preview.ts",
          "line_start": 12,
          "line_end": 16
        }
      ]
    },
    {
      "finding_id": "f-d0305d03-af76-4836-aa17-ac1ce4f9458f",
      "name": "CROSS_SITE_SCRIPTING: Remote response body echoed unescaped via res.send (reflected XSS)",
      "risk_level": "MEDIUM",
      "status": "ACTIVE",
      "confidence": "MEDIUM",
      "code_locations": [
        {
          "file_path": "src/preview.ts",
          "line_start": 15,
          "line_end": 15
        }
      ]
    },
    {
      "finding_id": "f-e7fa4a06-6983-406d-8c26-fe25ebdb86e4",
      "name": "SERVER_SIDE_REQUEST_FORGERY: previewLink fetches unvalidated user-supplied URL server-side and returns the body (full SSRF)",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/preview.ts",
          "line_start": 12,
          "line_end": 16
        }
      ]
    }
  ]
}
```
