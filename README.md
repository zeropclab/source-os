# SourceOS

个人经营者使用的、证据驱动的现实需求发现与产品验证工作台。

它管理信号、证据、Need Issue、反证、实验、Product Thesis、Feature、交付和结果记录；它不自动证明需求、付费、留存或盈利。

## 本地启动

需要 Python 3.11+、Node.js（仅 Pi Agent runtime）和 Docker。

```bash
docker compose up -d
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/`。

复制 `.env.example` 为 `.env` 后按需配置数据库与 Pi provider。未配置真实 Pi provider 时，可在工作台使用 `pi-faux-v1` 验证受控提案机制。

## 推荐的首次路径

1. 在 **Observe** 手工录入一条访谈、销售对话、邮件或线下观察；或在 **Missions** 运行 fixture 采集任务。
2. 在 Evidence Inbox 分诊为接受、忽略或待复核；接受的信号才能创建 Need Issue。
3. 在 Need 中同时记录支持证据、反证、未知项、挑战和最小验证行动。
4. 仅在明确的建设授权后创建 Product Thesis 与 Feature。
5. 在 Delivery 中保存测试、Review、PR、回滚和 Tracking 证据；发布后再记录结果和决策。

## 验证

```bash
uv run pytest -q
```

测试会使用独立的 `sourceos_test` 数据库并在每个测试后清理表。fixture/synthetic 数据只验证产品机制，不能作为真实市场验证、用户付费、留存或盈利的证据。

## 边界

- Pi Agent 只能基于明确选择的证据包提出可审计提案；不能自行采集、改写业务事实、越过门禁或发起外部商业行动。
- 评论数量、热度、情绪、模型输出和本体关系都不是需求、市场规模或付费意愿的证明。
- 真实市场结论只能来自后续的真实采集、接触、交付和结果数据。
