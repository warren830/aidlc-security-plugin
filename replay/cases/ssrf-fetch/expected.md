# 服务端请求伪造（SSRF）

## 场景

`src/preview.ts` 的 `previewLink` 把请求体里的 `url` 直接交给 `fetch`。服务端会从自己的网络位置
发起这个请求，攻击者可以把它指向 `http://169.254.169.254/latest/meta-data/...`（云厂商元数据接口）、
`http://internal-db/...` 或 `file:///etc/passwd` 之类的目标。OWASP A10（SSRF）和 CWE-918。
AWS-13 incidents.md 里 Bedrock AgentCore Starter Toolkit 的 CVE-2026-106032 就是同类 SSRF。

## 理论上应该在哪个环节被检测

代码生成门禁。Code Generation 的 Step 4b 对这个 unit 的 diff 跑 AWS Security Agent diff scan，
`security-findings-gate` 在 finding 没处理之前不让门禁通过。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `src/preview.ts`，离线的本地检查看不到它。与 `ssrf-fetch-fixed` 成对。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的 AWS Continuum 差分 code review（job `cj-4be8bd14-e60e-4448-a6b1-2094d21d4eb5`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-3222cd16-2c77-4fdf-8cec-0f4ebb8bf924`：HIGH，SERVER_SIDE_REQUEST_FORGERY: previewLink fetches attacker-controlled req.body.url with no validation (full-read SSRF)，位置 `src/preview.ts:12`。
- `f-d0305d03-af76-4836-aa17-ac1ce4f9458f`：MEDIUM，CROSS_SITE_SCRIPTING: Remote response body echoed unescaped via res.send (reflected XSS)，位置 `src/preview.ts:15`。
- `f-e7fa4a06-6983-406d-8c26-fe25ebdb86e4`：HIGH，SERVER_SIDE_REQUEST_FORGERY: previewLink fetches unvalidated user-supplied URL server-side and returns the body (full SSRF)，位置 `src/preview.ts:12`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `src/preview.ts` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "服务端请求伪造（SSRF）",
  "stage": "code-generation-gate",
  "expected": "continuum",
  "pair": "ssrf-fetch-fixed",
  "sources": [
    "https://www.veracode.com/blog/genai-code-security-report/",
    "https://aws.amazon.com/security/security-bulletins/rss/2026-127-aws/"
  ],
  "files": [
    "src/preview.ts"
  ]
}
```
