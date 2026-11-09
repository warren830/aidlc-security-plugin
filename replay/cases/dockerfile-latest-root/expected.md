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

待补。插件和 core 没有 security 类 sensor 覆盖 `Dockerfile`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case dockerfile-latest-root` 之后写入。
与 `dockerfile-latest-root-fixed` 成对。

## 证据

`bun replay/run.ts` 离线复验：对 `Dockerfile` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

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
