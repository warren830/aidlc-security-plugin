# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-5c8d27e8-289a-4d68-9e44-664f1a8aef00` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-90b44628-cd56-4571-b9d9-b6c77a33bea2 | HIGH | COMMAND_INJECTION: checkoutBranch() interpolates untrusted branch name into child_process.exec shell command, enabling arbitrary command execution | src/git.ts:6 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-5c8d27e8-289a-4d68-9e44-664f1a8aef00",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:12:42Z"
  },
  "findings": [
    {
      "finding_id": "f-90b44628-cd56-4571-b9d9-b6c77a33bea2",
      "name": "COMMAND_INJECTION: checkoutBranch() interpolates untrusted branch name into child_process.exec shell command, enabling arbitrary command execution",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "src/git.ts",
          "line_start": 6,
          "line_end": 12
        },
        {
          "file_path": "src/git.ts",
          "line_start": 8,
          "line_end": 8
        }
      ]
    }
  ]
}
```
