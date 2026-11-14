# Agent Continuity 中文说明

这个项目专门针对 AI 编程 Agent 的两个真实体验问题：

1. 上下文自动压缩以后，AI 遗忘此前的关键约束、设计决定和工作进度。
2. Agent 在工作前低效地逐个打开大量文件，而不是一次性定向定位相关代码。

**功能不是修改 Gemini 或 Antigravity 模型。** 目前只提供一个本地命令行工具、工作区规则，以及 Antigravity 可读取的 Skill。它无法拦截内部压缩，也无法控制工具调用的串行/并行调度。

## 安装

需要 Python 3.10+：

```bash
git clone https://github.com/ancient-echo/agent-continuity.git
cd agent-continuity
python -m pip install .
agent-continuity init --project "你自己的项目目录"
```

以后让 AI 在做出重要决定后执行：

```bash
agent-continuity checkpoint --project . \
  --goal "修复登录超时" \
  --constraint "不得修改现有API" \
  --decision "沿用已有重试模块" \
  --verified "登录模块测试通过" \
  --next "添加超时边界条件"
```

上下文压缩后，执行 `agent-continuity resume --project .`。工具会输出前面记录的决定及进度，并提示 Git 提交或工作区状态有无变化。

定位源代码：`agent-continuity locate "函数名" --project .`。

项目处于 v0.1 实验版，尚未经过真实 Antigravity A/B 性能测试，不能宣称已证明省 Token。请不要在检查点中写入密钥或敏感信息。
