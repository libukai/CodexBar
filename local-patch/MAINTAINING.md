# CodexBar 个人 Fork 维护

本地源码：`~/Github/Tools/CodexBar`。个人 Fork：[libukai/CodexBar](https://github.com/libukai/CodexBar)，官方上游：[steipete/CodexBar](https://github.com/steipete/CodexBar)。

## 分支与远程

| 名称 | 用途 |
| --- | --- |
| `origin` | 个人 Fork，日常提交和推送的目标 |
| `upstream` | 官方仓库，只读，禁止推送 |
| `main` | 官方 `upstream/main` 的镜像，不放个人修改 |
| `codex/ultrafast-cost-pricing` | 个人维护分支，也是 Fork 的默认分支 |
| `v0.74.1-libukai.1` | 首次本地补丁版本的源码标签 |

首次补丁基于官方 `v0.74.1`。2026-10-14 整理 Fork 时，官方最新发行版已为 [v0.75.0](https://github.com/steipete/CodexBar/releases/tag/v0.75.0)；`main` 同步当前上游，维护分支保留已构建的 v0.74.1 补丁基线。后续升级优先选择明确的 Release 标签。

本地 Git 默认向 `origin` 推送，GitHub CLI 的默认仓库也是个人 Fork。

## 查看上游更新

```bash
./local-patch/upstream.sh check
```

只更新远程引用和标签，输出最新 Release、上游提交与差异数量。不会修改当前源码或安装应用。需要同步 Fork 的 `main` 镜像时运行：

```bash
./local-patch/upstream.sh mirror
```

脚本要求工作区干净，只允许 `main` 快进；已有个人提交时会停止，正常推送不使用 `--force`。

## 将一个发行版合入维护分支

先确保修改已提交，再选择目标标签，例如：

```bash
git switch codex/ultrafast-cost-pricing
./local-patch/upstream.sh merge v0.75.0
```

脚本会创建 `codex/backup-before-upstream-*` 恢复分支，然后执行普通 merge，保留补丁历史和提交身份。冲突时先解决冲突；放弃本次合入可用 `git merge --abort`。不要把未解决冲突、未核对的计价结果或临时安装状态推送为维护版本。

每次检查这些补丁是否仍需要保留：

1. 上游是否已经正确解析 `ultrafast`，并在增量扫描、SQLite 恢复和模式切换时保留档位。
2. 保留真实 Token 和请求档位。订阅金额按 API 标准单价乘订阅倍率 1 / 2.5 / 8 计算，不应用 API 长上下文附加价，不使用 API Ultrafast 的 6 倍替代订阅 8 倍。
3. 缓存版本、计价指纹和解析器哈希要与最终代码一致。使用上游生成脚本更新哈希。
4. 继续保留长上下文、缓存 Token、分叉/子任务去重和压缩用量的上游修复。
5. 当完整 Xcode 可用时，可逐步去掉 Command Line Tools 的兼容层；不要提前删除仍在使用的重编译入口。

## 核对、构建和安装

完整 Xcode 环境沿用项目 `make check` / `make test`。本机 Command Line Tools 环境可先运行已维护的离线计价用例：

```bash
source Scripts/test_environment.sh
CODEXBAR_LOCAL_PRICING_TESTS=1 local-patch/toolchain/bin/swift test \
  --disable-xctest --filter CostUsageCodexSessionTierTests
./local-patch/build-app.sh
```

构建成功只代表生成了候选 `.app`。安装与恢复见 `install-app.sh`：

```bash
./local-patch/install-app.sh
```

它会验证候选签名、备份已安装应用、退出旧进程，移走旧 bundle 后复制完整新 bundle，再检查签名并启动。必须整体替换；直接用 `ditto` 合并旧 bundle 会残留文件、导致签名校验失败。安装状态只保存在被 Git 忽略的 `local-patch/install-state.json`。

安装后记录版本、主程序/CLI 哈希、签名、进程路径与本地用量读取结果。不要使用会触发真实 Keychain 授权或真实账户请求的测试来代替离线计价核对。

确认当前维护版本后：

```bash
git add <本次改动文件>
git commit
git push origin codex/ultrafast-cost-pricing
git tag -a vX.Y.Z-libukai.N -m 'Describe the maintained version'
git push origin vX.Y.Z-libukai.N
```

标签一旦发布，不覆盖或复用；新增版本用新标签。个人政策与本机构建兼容层暂不作为上游 PR 提交。

## GitHub 检查入口

Fork 提供手动 `Local patch checks` 工作流，用于有完整 Xcode 的 macOS runner 上运行档位测试。操作入口在个人 Fork 的 Actions，不使用上游发布、签名或部署工作流。`upstream.sh check` 是按需检查，不配置定时自动合入或自动安装。

## 本地说明文字与发布边界

Codex 的速度说明由模型元数据提供，修改模型缓存后可用 `reapply-speed-description.py` 重应用“8 倍速度，8 倍消耗”。服务器刷新模型目录可能覆盖它；这是用户指定的显示文字，不是独立测速结论。

应用包、构建目录、安装路径、PID、个人 Token/金额统计、登录数据、私钥和令牌不提交。编译出的本地签名版关闭自动更新且没有上游 CloudKit 权限，原版备份保持可恢复。

## 2026-10-14 最终统计口径

用户明确要求：订阅 Token 计入总量，金额表示“这些订阅消耗按 API 标准价格和订阅速度倍率折算，等值多少美元”。这不是官方账单，也不是额外的参考指数。

计算：`[(总输入 - 缓存输入) × 标准输入单价 + 缓存输入 × 标准缓存单价 + 输出 × 标准输出单价] × 订阅速度倍率`。普通 1 倍、Fast 2.5 倍、Ultrafast 8 倍。真实 Token 不乘倍率，推理 Token 不重复加入输出；订阅不套 API 的 272K 上下文附加价。

Codex 菜单、图表和汇总保留这个美元等值，明确标记订阅 API 等值；不把金额隐藏，不另建一套“参考用量”。API 真正调用和购买 Credits 的条件计算可以使用各自价格，但不能套进订阅折算。

```bash
python3 local-patch/recalculate-usage.py --date YYYY-MM-DD \
  --channel chatgpt_subscription --output local-patch/reports/usage-YYYY-MM-DD.json
python3 -m unittest discover -s local-patch -p 'test_recalculate_usage.py'
```

报告按模型和请求速度分组、列出原始 Token 和一个金额；缺失模型或档位不编造单价。当前渠道来自用户确认，本机日志不能确认每条请求的服务端实际档位。报告不提交。
