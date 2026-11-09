# Security scan

Written by `bun replay/continuum.ts` from AWS Continuum code review job `cj-4e5a0ddc-2c32-4cea-9ece-2c7f00d9ec7f` in ap-southeast-1.
Do not edit it by hand: run the script again to refresh it.

| ID | Risk | Name | Location | Status |
| --- | --- | --- | --- | --- |
| f-0baf4a05-71a9-4ee4-9c38-608e5b21454f | MEDIUM | SECURITY_MISCONFIGURATION: Dockerfile uses mutable unpinned base image `node:latest`, allowing non-reproducible builds with unknown/compromised upstream layers | Dockerfile:4 | ACTIVE |
| f-7eb3df1d-80c5-4350-9c35-88428aad4272 | MEDIUM | SECURITY_MISCONFIGURATION: Non-reproducible `npm install --production` as root permits dependency drift and build-time script execution | Dockerfile:7 | ACTIVE |
| f-d9e4da50-57d0-4877-9e6a-005c0b9d1fc7 | HIGH | PRIVILEGE_ESCALATION: Dockerfile sets USER root before CMD (container runs as uid 0) | Dockerfile:11 | ACTIVE |

```json
{
  "schema_version": 1,
  "scan": {
    "scan_id": "cj-4e5a0ddc-2c32-4cea-9ece-2c7f00d9ec7f",
    "scan_type": "DIFF",
    "base_ref": "empty repository",
    "status": "COMPLETED",
    "region": "ap-southeast-1",
    "mcp_server": "none: securityagent StartCodeReviewJob from replay/continuum.ts",
    "completed_at": "2026-11-09T08:05:04Z"
  },
  "findings": [
    {
      "finding_id": "f-0baf4a05-71a9-4ee4-9c38-608e5b21454f",
      "name": "SECURITY_MISCONFIGURATION: Dockerfile uses mutable unpinned base image `node:latest`, allowing non-reproducible builds with unknown/compromised upstream layers",
      "risk_level": "MEDIUM",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "Dockerfile",
          "line_start": 4,
          "line_end": 4
        },
        {
          "file_path": "Dockerfile",
          "line_start": 11,
          "line_end": 11
        }
      ]
    },
    {
      "finding_id": "f-7eb3df1d-80c5-4350-9c35-88428aad4272",
      "name": "SECURITY_MISCONFIGURATION: Non-reproducible `npm install --production` as root permits dependency drift and build-time script execution",
      "risk_level": "MEDIUM",
      "status": "ACTIVE",
      "confidence": "MEDIUM",
      "code_locations": [
        {
          "file_path": "Dockerfile",
          "line_start": 7,
          "line_end": 8
        },
        {
          "file_path": "Dockerfile",
          "line_start": 11,
          "line_end": 11
        }
      ]
    },
    {
      "finding_id": "f-d9e4da50-57d0-4877-9e6a-005c0b9d1fc7",
      "name": "PRIVILEGE_ESCALATION: Dockerfile sets USER root before CMD (container runs as uid 0)",
      "risk_level": "HIGH",
      "status": "ACTIVE",
      "confidence": "HIGH",
      "code_locations": [
        {
          "file_path": "Dockerfile",
          "line_start": 11,
          "line_end": 13
        }
      ]
    }
  ]
}
```
