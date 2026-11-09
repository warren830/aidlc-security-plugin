# Dockerfile：漂移的 latest 标签 + root 运行 — 修好版

## 场景

和 `dockerfile-latest-root` 是同一处的修复：基座镜像固定到 `node:22.11.0-bookworm-slim`
（明确的 major/minor/patch + 发行版代号），并新建 `appuser` 这个非 root 系统账户，用
`USER appuser` 切换。镜像构建可重现，运行时即便被攻破也落在低权限账户里。这是
`dockerfile-latest-root` 的干净对照。

## 理论上应该在哪个环节被检测

CI。同一门禁应该不再对这个 diff 报 HIGH 及以上的容器镜像 finding。

## 现在的实现能否检测到

待补。本用例与 `dockerfile-latest-root` 成对，预期结果是 `not-detected`。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case dockerfile-latest-root-fixed` 之后写入。

## 证据

`bun replay/run.ts` 离线复验：对 `Dockerfile` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

```json
{
  "vector": "Dockerfile：漂移的 latest 标签 + root 运行 — 修好版",
  "stage": "ci",
  "expected": "not-detected",
  "pair": "dockerfile-latest-root",
  "gap_owner": "action",
  "sources": [
    "https://www.wiz.io/blog/trivy-compromised-teampcp-supply-chain-attack",
    "https://www.stepsecurity.io/blog/teampcp-supply-chain-attack-cicd-secrets-cloudsek-disclosure"
  ],
  "files": [
    "Dockerfile"
  ]
}
```
