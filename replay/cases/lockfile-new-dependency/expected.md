# lockfile 里的被劫持版本和陌生依赖

## 场景

`package.json` 写的是 `axios: ^1.14.0`，lockfile 把它解析到了被劫持的 1.14.1，还多出一个之前从没出现过、
带安装脚本的依赖 `plain-crypto-js`。这正是 axios 那次的样子；Shai-Hulud 2.0 也是这样，靠被感染的新版本
传播。`repo/package-lock.json` 是最小样本：`resolved` 都指向 `registry.invalid`，`integrity` 是假值，
所以这个目录装不了任何东西。

## 理论上应该在哪个环节被检测

CI：PR 改了 lockfile 时，对照已知恶意版本，并标出第一次出现的依赖和新增的安装脚本。

## 现在的实现能否检测到

Continuum 检测到，插件门禁拦下。插件和 core 没有 security 类 sensor 覆盖 `package-lock.json`、`package.json`，离线的本地检查看不到它。

2026-11-09 用 `replay/continuum.ts` 在 ap-southeast-1 对 `repo/` 跑了一次真实的
AWS Continuum 差分 code review（job `cj-4549a304-de2f-409f-b6df-9241bc63f1a5`，基线是空仓库，diff 新增了 `repo/` 下的全部文件）。它报出：

- `f-29c61b7f-871d-44ba-bb7e-62b439afae80`：HIGH，SECURITY_MISCONFIGURATION: Lockfile resolves dependencies from untrusted registry.invalid with placeholder integrity hashes and an install-script typosquat dependency, enabling build-time RCE，位置 `package-lock.json:14`。
- `f-595467f4-0ced-4e44-a48e-9ccbbe8aeb9b`：HIGH，CODE_INJECTION: Malicious/typosquat transitive dependency plain-crypto-js@4.2.1 with install script → build-time RCE，位置 `package-lock.json:23`。

## 证据

`security-scan-result.md` 是 Continuum 这次的原始结果，按插件门禁读的记录格式写入。`bun replay/run.ts --check`
对 `package-lock.json`、`package.json` 跑了所有覆盖它们的 security 类 sensor，又用插件的 `security-findings-gate` 判了这份记录。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "lockfile 里的被劫持版本和陌生依赖",
  "stage": "ci",
  "expected": "continuum",
  "sources": [
    "https://www.stepsecurity.io/blog/axios-compromised-on-npm-malicious-versions-drop-remote-access-trojan",
    "https://www.wiz.io/blog/shai-hulud-2-0-ongoing-supply-chain-attack"
  ],
  "files": [
    "package-lock.json",
    "package.json"
  ]
}
```
