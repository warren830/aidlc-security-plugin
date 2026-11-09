# Dockerfile：漂移的 latest 标签 + root 运行 — 修好版

## 场景

和 `dockerfile-latest-root` 是同一处的修复：基座镜像固定到 `node:22.11.0-bookworm-slim`
（明确的 major/minor/patch + 发行版代号），并新建 `appuser` 这个非 root 系统账户，用
`USER appuser` 切换。镜像构建可重现，运行时即便被攻破也落在低权限账户里。这是
`dockerfile-latest-root` 的干净对照。

## 理论上应该在哪个环节被检测

CI。同一门禁应该不再对这个 diff 报 HIGH 及以上的容器镜像 finding。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `Dockerfile`，离线的本地检查看不到它。与 `dockerfile-latest-root` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-3c3a44b9-a4b6-4797-8dbc-79c15588026a`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-47bdc83e-84a6-4a8d-a6e9-962dc297fa0c`：LOW，SECURITY_MISCONFIGURATION: Dockerfile chowns all of /app to the runtime user, making application code writable at runtime (persistence/code tampering)，位置 `Dockerfile:12`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `Dockerfile` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "Dockerfile：漂移的 latest 标签 + root 运行 — 修好版",
  "stage": "ci",
  "expected": "not-detected",
  "pair": "dockerfile-latest-root",
  "sources": [
    "https://www.wiz.io/blog/trivy-compromised-teampcp-supply-chain-attack",
    "https://www.stepsecurity.io/blog/teampcp-supply-chain-attack-cicd-secrets-cloudsek-disclosure"
  ],
  "files": [
    "Dockerfile"
  ]
}
```
