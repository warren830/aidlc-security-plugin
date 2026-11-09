# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-83aa88e6-59be-4b27-8511-e136a832add3` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-33498a67-679b-487c-89fb-7f9050014712 | HIGH | SECURITY_MISCONFIGURATION: handlePreflight emits wildcard Access-Control-Allow-Origin with Access-Control-Allow-Credentials: true, no Origin allowlist or Vary | src/cors.ts:10 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-83aa88e6-59be-4b27-8511-e136a832add3",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:33:24Z"
  },
  "findings": [
    {
      "finding_id": "f-33498a67-679b-487c-89fb-7f9050014712",
      "name": "SECURITY_MISCONFIGURATION: handlePreflight emits wildcard Access-Control-Allow-Origin with Access-Control-Allow-Credentials: true, no Origin allowlist or Vary",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/cors.ts",
          "line_start": 10,
          "line_end": 15
        }
      ]
    }
  ]
}
```
