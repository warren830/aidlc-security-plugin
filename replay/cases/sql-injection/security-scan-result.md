# Security scan

A recorded sample, not a real AWS Security Agent result. It has the shape
Code Generation's Step 4b writes, so the gate reads it the way it reads a
real record.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-901 | HIGH | SQL injection | src/users.ts:6 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "scan-replay-901",
    "scan_type": "DIFF",
    "base_ref": "HEAD",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "awslabs.security-agent-mcp-server@0.2.1",
    "completed_at": "2026-11-07T10:00:00Z"
  },
  "findings": [
    {
      "finding_id": "f-901",
      "name": "SQL injection",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [{ "file_path": "src/users.ts", "line_start": 6, "line_end": 6 }]
    }
  ]
}
```
