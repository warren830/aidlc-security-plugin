# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-57dee867-17e2-4bb2-b2bc-4bb4b7088a65` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-409b902c-ae0a-4ab8-8b3e-49ec0c26d0c6 | HIGH | CODE_INJECTION: VS Code task with runOn:folderOpen auto-executes committed shell command on opening repo | .vscode/tasks.json:1 | ACTIVE |
| f-8053e941-2b9f-4948-bdfa-ad292f62b630 | HIGH | CODE_INJECTION: Committed autorun developer-tool configs (VS Code folderOpen task, Claude SessionStart hook) execute repo-controlled shell commands without consent | .vscode/tasks.json:1 | ACTIVE |
| f-cfa41421-10f1-4abd-bf85-36d614bb5898 | MEDIUM | CODE_INJECTION: Committed project-scoped .mcp.json auto-launches a repo-defined subprocess on the developer machine | .mcp.json:1 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-57dee867-17e2-4bb2-b2bc-4bb4b7088a65",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T01:41:56Z"
  },
  "findings": [
    {
      "finding_id": "f-409b902c-ae0a-4ab8-8b3e-49ec0c26d0c6",
      "name": "CODE_INJECTION: VS Code task with runOn:folderOpen auto-executes committed shell command on opening repo",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".vscode/tasks.json",
          "line_start": 1,
          "line_end": 13
        }
      ]
    },
    {
      "finding_id": "f-8053e941-2b9f-4948-bdfa-ad292f62b630",
      "name": "CODE_INJECTION: Committed autorun developer-tool configs (VS Code folderOpen task, Claude SessionStart hook) execute repo-controlled shell commands without consent",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": ".vscode/tasks.json",
          "line_start": 1,
          "line_end": 13
        },
        {
          "file_path": ".claude/settings.json",
          "line_start": 1,
          "line_end": 14
        }
      ]
    },
    {
      "finding_id": "f-cfa41421-10f1-4abd-bf85-36d614bb5898",
      "name": "CODE_INJECTION: Committed project-scoped .mcp.json auto-launches a repo-defined subprocess on the developer machine",
      "risk_level": "MEDIUM",
      "status": "ACTIVE",
      "confidence": "MEDIUM",
      "code_locations": [
        {
          "file_path": ".mcp.json",
          "line_start": 1,
          "line_end": 10
        }
      ]
    }
  ]
}
```
