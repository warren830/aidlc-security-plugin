# lockfile 里的被劫持版本和陌生依赖

## 场景

`package.json` 写的是 `axios: ^1.14.0`，lockfile 把它解析到了被劫持的 1.14.1，还多出一个之前从没出现过、
带安装脚本的依赖 `plain-crypto-js`。这正是 axios 那次的样子；Shai-Hulud 2.0 也是这样，靠被感染的新版本
传播。`repo/package-lock.json` 是最小样本：`resolved` 都指向 `registry.invalid`，`integrity` 是假值，
所以这个目录装不了任何东西。

## 理论上应该在哪个环节被检测

CI：PR 改了 lockfile 时，对照已知恶意版本，并标出第一次出现的依赖和新增的安装脚本。

## 现在的实现能否检测到

未检测到。插件和 core 都没有 sensor 覆盖 `package-lock.json`，插件也不比较依赖的变化。建议由 AWS-9 的
Action 补，它在 PR 上能看到 lockfile 的前后差异。

## 证据

`bun replay/run.ts --check` 对 `files` 里的每个文件跑了所有覆盖它的 security 类 sensor。实际结果和下面的
`expected` 不一致时，命令失败。输出见 `replay/REPORT.md` 里的对应行。

```json
{
  "vector": "lockfile 里的被劫持版本和陌生依赖",
  "stage": "ci",
  "expected": "not-detected",
  "sources": [
    "https://www.stepsecurity.io/blog/axios-compromised-on-npm-malicious-versions-drop-remote-access-trojan",
    "https://www.wiz.io/blog/shai-hulud-2-0-ongoing-supply-chain-attack"
  ],
  "files": [
    "package-lock.json",
    "package.json"
  ],
  "gap_owner": "action"
}
```
