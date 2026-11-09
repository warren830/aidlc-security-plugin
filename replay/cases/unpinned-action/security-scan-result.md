# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-25a2a2cb-cebe-419c-b04a-4bb04880409c` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-d9545f10-915d-45fa-b760-96831d979447 | HIGH | OTHER: CI workflow uses known-compromised tj-actions/changed-files@v45 pinned to mutable tag (CVE-2025-30066) | .github/workflows/build.yml:14 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-25a2a2cb-cebe-419c-b04a-4bb04880409c",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:30:39Z"
  },
  "findings": [
    {
      "finding_id": "f-d9545f10-915d-45fa-b760-96831d979447",
      "name": "OTHER: CI workflow uses known-compromised tj-actions/changed-files@v45 pinned to mutable tag (CVE-2025-30066)",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".github/workflows/build.yml",
          "line_start": 14,
          "line_end": 14
        },
        {
          "file_path": ".github/workflows/build.yml",
          "line_start": 13,
          "line_end": 13
        }
      ]
    }
  ]
}
```
