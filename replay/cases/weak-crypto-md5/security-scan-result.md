# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-b491b3bc-e771-488a-89d1-5023555b4ec8` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-64515405-6b25-483b-8101-182ad8499844 | HIGH | CRYPTOGRAPHIC_VULNERABILITIES: hashPassword() uses unsalted MD5 for password storage | src/passwords.ts:4 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-b491b3bc-e771-488a-89d1-5023555b4ec8",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:03:12Z"
  },
  "findings": [
    {
      "finding_id": "f-64515405-6b25-483b-8101-182ad8499844",
      "name": "CRYPTOGRAPHIC_VULNERABILITIES: hashPassword() uses unsalted MD5 for password storage",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/passwords.ts",
          "line_start": 4,
          "line_end": 8
        }
      ]
    }
  ]
}
```
