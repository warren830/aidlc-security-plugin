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

待补。插件和 core 没有 security 类 sensor 覆盖 `src/preview.ts`，离线的本地检查看不到它。
`security-scan-result.md` 由开发·EC2 跑 `bun replay/continuum.ts --case ssrf-fetch` 之后写入。
与 `ssrf-fetch-fixed` 成对。

## 证据

`bun replay/run.ts` 离线复验：对 `src/preview.ts` 跑所有覆盖它的 security 类 sensor，再用插件的
`security-findings-gate` 判 `security-scan-result.md`。

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
