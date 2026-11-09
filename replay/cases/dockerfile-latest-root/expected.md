# Dockerfile：漂移的 latest 标签 + root 运行

## 场景

`Dockerfile` 用 `FROM node:latest` 作基座，`USER root` 让进程以 root 跑。`latest` 是一个会变
的 tag：不同时间构建同一个 Dockerfile 会拿到不同的上游镜像，无法审计也无法重现。容器内
以 root 跑则让任何应用层 RCE 直接获得 root，配合 docker socket 或 capabilities 还能逃逸。
这一类是容器镜像 lint（hadolint、Trivy、Checkov）的基础规则。Trivy 自己 2026-03 被 TeamPCP
劫持的事件也说明镜像工具链的信任假设需要外部兜底。

## 理论上应该在哪个环节被检测

CI。PR 改 Dockerfile 时，由 CI 上的容器 lint（或 AWS-9 Action 调用的规则）拦下。AI-DLC 的
威胁建模阶段也可能标出"用 latest"是设计风险，但本用例不走 AI 流程，归 CI。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `Dockerfile`，离线的本地检查看不到它。与 `dockerfile-latest-root-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-4e5a0ddc-2c32-4cea-9ece-2c7f00d9ec7f`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-0baf4a05-71a9-4ee4-9c38-608e5b21454f`：MEDIUM，SECURITY_MISCONFIGURATION: Dockerfile uses mutable unpinned base image `node:latest`, allowing non-reproducible builds with unknown/compromised upstream layers，位置 `Dockerfile:4`。
- `f-7eb3df1d-80c5-4350-9c35-88428aad4272`：MEDIUM，SECURITY_MISCONFIGURATION: Non-reproducible `npm install --production` as root permits dependency drift and build-time script execution，位置 `Dockerfile:7`。
- `f-d9e4da50-57d0-4877-9e6a-005c0b9d1fc7`：HIGH，PRIVILEGE_ESCALATION: Dockerfile sets USER root before CMD (container runs as uid 0)，位置 `Dockerfile:11`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `Dockerfile` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "Dockerfile：漂移的 latest 标签 + root 运行",
  "stage": "ci",
  "expected": "continuum",
  "pair": "dockerfile-latest-root-fixed",
  "sources": [
    "https://www.wiz.io/blog/trivy-compromised-teampcp-supply-chain-attack",
    "https://www.stepsecurity.io/blog/teampcp-supply-chain-attack-cicd-secrets-cloudsek-disclosure"
  ],
  "files": [
    "Dockerfile"
  ]
}
```
