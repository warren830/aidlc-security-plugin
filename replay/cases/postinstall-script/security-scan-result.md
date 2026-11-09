# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-d4673b60-ee67-480c-b64d-84f0fe524893` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-9ad052a9-6f47-44ee-9185-5bdbf5db5210 | MEDIUM | CODE_INJECTION: Vendored dependency adds npm postinstall hook, executing repo-controlled code on every install (CI/dev) | vendor/example-helper/package.json:4 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-d4673b60-ee67-480c-b64d-84f0fe524893",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:41:59Z"
  },
  "findings": [
    {
      "finding_id": "f-9ad052a9-6f47-44ee-9185-5bdbf5db5210",
      "name": "CODE_INJECTION: Vendored dependency adds npm postinstall hook, executing repo-controlled code on every install (CI/dev)",
      "risk_level": "MEDIUM",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "vendor/example-helper/package.json",
          "line_start": 4,
          "line_end": 6
        },
        {
          "file_path": "vendor/example-helper/postinstall.js",
          "line_start": 1,
          "line_end": 3
        },
        {
          "file_path": "package.json",
          "line_start": 5,
          "line_end": 7
        }
      ]
    }
  ]
}
```
