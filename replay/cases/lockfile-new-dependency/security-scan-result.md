# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-4549a304-de2f-409f-b6df-9241bc63f1a5` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-29c61b7f-871d-44ba-bb7e-62b439afae80 | HIGH | SECURITY_MISCONFIGURATION: Lockfile resolves dependencies from untrusted registry.invalid with placeholder integrity hashes and an install-script typosquat dependency, enabling build-time RCE | package-lock.json:14 | ACTIVE |
| f-595467f4-0ced-4e44-a48e-9ccbbe8aeb9b | HIGH | CODE_INJECTION: Malicious/typosquat transitive dependency plain-crypto-js@4.2.1 with install script → build-time RCE | package-lock.json:23 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-4549a304-de2f-409f-b6df-9241bc63f1a5",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:50:28Z"
  },
  "findings": [
    {
      "finding_id": "f-29c61b7f-871d-44ba-bb7e-62b439afae80",
      "name": "SECURITY_MISCONFIGURATION: Lockfile resolves dependencies from untrusted registry.invalid with placeholder integrity hashes and an install-script typosquat dependency, enabling build-time RCE",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "package-lock.json",
          "line_start": 14,
          "line_end": 28
        },
        {
          "file_path": "package-lock.json",
          "line_start": 22,
          "line_end": 27
        },
        {
          "file_path": "package.json",
          "line_start": 5,
          "line_end": 7
        }
      ]
    },
    {
      "finding_id": "f-595467f4-0ced-4e44-a48e-9ccbbe8aeb9b",
      "name": "CODE_INJECTION: Malicious/typosquat transitive dependency plain-crypto-js@4.2.1 with install script → build-time RCE",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "package-lock.json",
          "line_start": 23,
          "line_end": 28
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
