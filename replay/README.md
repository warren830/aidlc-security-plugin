# 验证测试套件

每个用例是一个最小场景，记录它理论上应该在哪个环节被检测，以及这个仓库现在的实现能否检测到。
每个用例都在真实的 AWS Continuum 上跑过一次差分 code review，结果存在用例目录里。
`bun replay/run.ts` 离线跑完所有用例，用插件的门禁重新判一遍这些真实结果，生成 [`REPORT.md`](REPORT.md)。

## 一个用例

`cases/<id>/` 下有：

- `repo/`：场景的最小仓库。runner 只读里面的文件，从不执行，内容都是无害的占位。
- `security-scan-result.md`：`replay/continuum.ts` 写的 Continuum 真实结果，格式就是 Code Generation
  Step 4b 写给门禁的扫描记录。不要手改，重跑脚本来刷新。
- `expected.md`：场景、理论检测环节、现在能否检测到、证据，以及唯一一个 `json` 块：

| 字段 | 值 |
| --- | --- |
| `vector` | 报告里的测试向量名 |
| `stage` | `threat-model`、`code-generation-gate` 或 `ci` |
| `expected` | `local`、`continuum`、`coverage`、`sections` 或 `not-detected` |
| `sources` | 场景的公开出处 URL |
| `files` | `repo/` 下承载场景的文件，相对 `repo/` |
| `gap_owner` | `expected` 是 `not-detected` 时必填（修好版不用填）：`plugin` 或 `action`（AWS-9） |
| `pair` | 可选。成对用例的另一半：`<id>` 是有问题版，`<id>-fixed` 是只修掉问题点的修好版，两边互相指向 |

威胁模型用例另有三个文件：

- `security-threat-model.md`：Inception 的威胁模型，格式见 Security Threat Model 的 Step 6，章节按插件的模板
  `security/tools/data/templates/security-threat-model.md`。手写的要在 `expected.md` 里写明。
- `threat-coverage.json`：agent 在 Code Generation Step 4c 写进扫描记录的 `threat_coverage`。
- `.aidlc-security.json`：门禁读的配置，比如 `{ "coverage_mode": "block" }`。

威胁模型用例可以原样复制另一个用例的 `repo/` 和 `security-scan-result.md`，在 `expected.md` 里写明出处。

## 结果怎么算

runner 对每个用例做两件事，威胁模型用例再多做两件：

1. 对 `files` 里的每个文件，找出 core 和插件里 `category: security`、`matches` 覆盖它的
   sensor，逐个运行。有一个不通过，结果就是 `local`（本地检测到）。
2. 对 `security-scan-result.md` 运行插件的 `security-findings-gate`。门禁拦下，结果就是 `continuum`：
   Continuum 报出了 HIGH 及以上的 finding，插件门禁据此拦下。
3. 威胁覆盖：在临时目录里搭一个记录目录，`security-threat-model.md` 放在
   `<record>/inception/security-threat-model/`，`security-scan-result.md` 合进 `threat-coverage.json`、
   `schema_version` 改成 2 以后放在 `<record>/construction/<id>/code-generation/`，再在用例目录下运行门禁。
   前两步都没拦下、这一步拦下，结果就是 `coverage`（威胁覆盖检查拦下）。用例目录里的
   `security-scan-result.md` 不改。
4. 必备章节：在用例目录下对 `security-threat-model.md` 运行 core 的 `required-sections` worker，参数和
   dispatcher 在 Security Threat Model 门禁上给的一样，只是不给团队模板目录（`--templates-dir`）。
   `--framework-templates-dir` 指向插件的 `security/tools/data/templates/`，安装以后它就是 dispatcher 读的
   `<harness>/tools/data/templates/`。前三步都没拦下、这一步拦下，结果就是 `sections`（必备章节检查拦下）。
   模板没有生效时 runner 报错退出，不算放行。

都没拦下，结果就是 `not-detected`。Continuum 报了、但等级低于门禁阈值的，也算 `not-detected`，
证据里会列出它报的等级。

修好版（带 `pair`、名字以 `-fixed` 结尾）被拦下算误拦。报告开头给出拦截率（有问题的版本被拦下几个）
和误报率（修好版被误拦几个），以及每对场景两边的结果。

结果和 `expected` 不一致时，`run.ts` 失败。缺口不能靠改报告藏起来；补上缺口以后，
也要同时改 `expected.md`。

## 运行

```bash
bun replay/run.ts           # 重新生成 REPORT.md
bun replay/run.ts --check   # CI 用：结果和预期不一致，或者 REPORT.md 过期，就失败
```

runner 读 aidlc-workflows checkout 里的 core sensor，所以和 `bun run test` 一样需要
`AIDLC_WORKFLOWS_DIR`（见仓库根目录的 README）。

## 跑 Continuum

新用例要先在 Continuum 上跑一次，才有 `security-scan-result.md`。`replay/continuum.ts` 会在你的 AWS
账户里启动 code review job，所以只手动跑，CI 不跑：

```bash
bun replay/continuum.ts --agent-space-id <agent space> --bucket <该 agent space 连接的 S3 桶> \
  --service-role-arn <SecurityAgentScanRole 的 ARN> --region ap-southeast-1 --case <id>
```

- 不加 `--case` 时，跑所有还没有记录的用例。`--concurrency` 默认 2；一个账户同时最多跑 5 个 code review。
- 所有用例共用一个 code review，名叫 `aidlc-replay`，第一次运行时创建。它的源码快照是一个空仓库，
  每个 job 的 diff 新增用例 `repo/` 下的全部文件，所以 Continuum 只看到这个用例。
- 上传的对象都在桶里的 `aidlc-replay/` 前缀下。记录里的 job ID 在 `aidlc-replay` 这个 code review
  还在时都能查到，所以不要删它。
- 一个 job 大约 10 分钟。

看起来像凭证的样本用明显是假的值，并且在仓库根目录的 `.gitleaks.toml` 里放行。
