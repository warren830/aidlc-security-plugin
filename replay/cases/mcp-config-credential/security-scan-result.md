# Security scan

A recorded sample, not a real AWS Security Agent result. It has the shape
Code Generation's Step 4b writes, so the gate reads it the way it reads a
real record. The key in `.mcp.json` is a fake value.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-902 | CRITICAL | Hardcoded credential | .mcp.json:7-8 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "scan-replay-902",
    "scan_type": "DIFF",
    "base_ref": "HEAD",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "awslabs.security-agent-mcp-server@0.2.1",
    "completed_at": "2026-11-07T10:00:00Z"
  },
  "findings": [
    {
      "finding_id": "f-902",
      "name": "Hardcoded credential",
      "risk_level": "CRITICAL",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [{ "file_path": ".mcp.json", "line_start": 7, "line_end": 8 }]
    }
  ]
}
```
