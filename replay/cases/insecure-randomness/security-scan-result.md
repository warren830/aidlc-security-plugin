# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-4a0af396-dede-493e-ae42-753c1d08b243` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-6ba5eea1-9bfd-41f4-8a35-a3de80bcb71f | HIGH | CRYPTOGRAPHIC_VULNERABILITIES: Password-reset token generated with non-cryptographic Math.random() | src/tokens.ts:4 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-4a0af396-dede-493e-ae42-753c1d08b243",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:13:11Z"
  },
  "findings": [
    {
      "finding_id": "f-6ba5eea1-9bfd-41f4-8a35-a3de80bcb71f",
      "name": "CRYPTOGRAPHIC_VULNERABILITIES: Password-reset token generated with non-cryptographic Math.random()",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/tokens.ts",
          "line_start": 4,
          "line_end": 11
        }
      ]
    }
  ]
}
```
