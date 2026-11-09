# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-6433c732-b80e-4664-b22d-c9b0a731f5ed` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-c2d98e7c-d2fe-467f-8e37-da43dac79c7a | HIGH | CODE_INJECTION: Hidden Unicode-tag/zero-width prompt-injection instructions in new always-applied AI agent rule files | .cursor/rules/style.mdc:1 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-6433c732-b80e-4664-b22d-c9b0a731f5ed",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:31:33Z"
  },
  "findings": [
    {
      "finding_id": "f-c2d98e7c-d2fe-467f-8e37-da43dac79c7a",
      "name": "CODE_INJECTION: Hidden Unicode-tag/zero-width prompt-injection instructions in new always-applied AI agent rule files",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".cursor/rules/style.mdc",
          "line_start": 1,
          "line_end": 6
        },
        {
          "file_path": ".kiro/steering/style.md",
          "line_start": 1,
          "line_end": 3
        },
        {
          "file_path": "README.md",
          "line_start": 1,
          "line_end": 1
        }
      ]
    }
  ]
}
```
