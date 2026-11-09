# 服务端请求伪造 — 修好版

## 场景

和 `ssrf-fetch` 是同一处的修复：先用 `new URL()` 解析目标，再校验 scheme 必须是 `https:`、
hostname 必须在显式 allowlist 里。任何 loopback、link-local 或内网地址都会在 fetch 之前被
拒绝。fetch 不跟随重定向，避免跳出校验过的主机。这是 `ssrf-fetch` 的干净对照。

## 理论上应该在哪个环节被检测

代码生成门禁。同一门禁应该不再对这个 diff 报 HIGH 及以上的 SSRF finding。

## 现在的实现能否检测到

放行，符合预期。Continuum 没有报出 HIGH 及以上的 finding，插件门禁不拦。插件和 core 没有 security 类 sensor 覆盖 `src/preview.ts`，离线的本地检查看不到它。与 `ssrf-fetch` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-8d97f232-045e-47af-adb5-8fa14598f4b7`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它没有报出任何 finding。

第一版修复没过：Continuum 在 job `cj-7df3ac27-014c-4474-af2d-59b8ac1beb9f` 里报出 HIGH SERVER_SIDE_REQUEST_FORGERY：fetch 默认跟随重定向，allowlist 里的主机可以 302 到内网地址。这是真实的残留问题，不是误报。补全修复（fetch 加上 `redirect: "error"`）后重新扫描，结果如上。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/preview.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "服务端请求伪造 — 修好版",
  "stage": "code-generation-gate",
  "expected": "not-detected",
  "pair": "ssrf-fetch",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://aws.amazon.com/security/security-bulletins/rss/2026-127-aws/"
  ],
  "files": [
    "src/preview.ts"
  ]
}
```
