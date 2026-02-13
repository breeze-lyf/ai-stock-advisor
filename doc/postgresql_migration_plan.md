# 技术预研：AI 智能投顾系统迁移至 PostgreSQL

## 1. 执行摘要 (Executive Summary)

虽然 **SQLite** 在项目初期的开发和单用户阶段表现良好，但其架构在并发性、可扩展性和高级数据处理方面存在固有的局限性。

迁移到 **PostgreSQL** 是将 *AI 智能投顾系统* 演进为能够处理多用户并发、高频数据摄入和复杂 AI 向量运算的稳健、生产级系统的推荐路径。

## 2. 为什么要迁移到 PostgreSQL? (差距分析)

| 特性 (Feature) | SQLite (当前) | PostgreSQL (目标) | 对 AI 智能投顾系统的影响 |
| :--- | :--- | :--- | :--- |
| **并发性 (Concurrency)** | **文件级写入锁 (File-level Write Lock)**。实际上是串行写入。并在高频更新期间极易出现 `database is locked` 错误。 | **行级锁 (Row-level Locking / MVCC)**。支持成千上万的并发写入（例如：用户分析 + 后台爬虫同时进行）。 | **关键 (Critical)**。允许后台数据刷新 *同时* 用户正在生成报告，互不阻塞。 |
| **架构 (Architecture)** | **无服务器 (嵌入式)**。绑定到应用程序文件系统。难以水平扩展。 | **客户端-服务器 (C/S)**。数据库可以托管在 AWS RDS/Cloud SQL 上，允许后端独立扩展。 | **高 (High)**。对于未来云部署（SaaS 模式）至关重要。 |
| **数据类型 (Data Types)** | **弱类型 (Weak Typing)**。有限的 JSON 支持。 | **丰富类型 (Rich Typing)**。支持 **JSONB** (二进制 JSON) 用于高性能存储 AI 分析结果。 | **高 (High)**。显著加快查询 JSON 字段内的历史 AI 报告速度。 |
| **AI 能力 (AI Capabilities)** | 无。 | **pgvector 插件**。原生向量存储和相似性搜索。 | **变革性 (Transformative)**。无需外部向量数据库 (Chroma/Milvus) 即可在数据库中原生启用 **RAG (检索增强生成)**。 |
| **时间序列 (Time-Series)** | 基本 B-Tree 索引。 | **TimescaleDB 扩展**。专为金融时间序列 (K线) 数据优化。 | **高 (High)**。使得股票历史图表查询和技术指标计算快 10-100 倍。 |

## 3. 实施计划 (Implementation Plan)

### 第一阶段：准备工作 (Phase 1: Preparation)

1.  **环境设置**:
    *   安装 PostgreSQL 16+ (本地或 Docker)。
    *   创建数据库 `ai_advisor`。
    *   创建用户 `breeze` 并设置密码。
2.  **依赖更新**:
    *   安装 `asyncpg`: `pip install asyncpg` (SQLAlchemy 的高性能异步驱动)。
    *   安装 `psycopg2-binary`: `pip install psycopg2-binary` (用于同步迁移脚本)。

### 第二阶段：配置变更 (Phase 2: Configuration Changes)

1.  **修改 `backend/app/core/config.py`**:
    更改 `DATABASE_URL` 格式:
    ```python
    # 旧配置 (Old)
    DATABASE_URL = "sqlite+aiosqlite:///./ai_advisor.db"
    
    # 新配置 (New)
    DATABASE_URL = "postgresql+asyncpg://user:password@localhost/ai_advisor"
    ```

2.  **更新 `alembic.ini`**:
    确保同步 URL (用于迁移) 使用 `postgresql+psycopg2`。

### 第三阶段：数据迁移策略 (Phase 3: Data Migration Strategy)

由于 Schema 由 Alembic/SQLAlchemy 管理，我们有两个数据迁移选项：

#### 选项 A: 全新开始 (推荐用于开发环境)
1.  删除 SQLite 数据库。
2.  针对 Postgres 运行 `alembic upgrade head` 以创建全新表结构。
3.  运行现有的 `seed_stocks.py` 重新填充代码。
4.  运行现有的 *市场数据刷新* 脚本重新获取最新数据。
    *   *优点*: 状态最干净，测试迁移脚本。
    *   *缺点*: 丢失历史 "AI 分析" 报告。

#### 选项 B: 数据传输 (如果历史数据至关重要)
1.  使用 **pgloader** 工具自动将 SQLite 文件转换为 Postgres。
    ```bash
    pgloader ./backend/ai_advisor.db postgresql://user:pass@localhost/ai_advisor
    ```
2.  *风险*: 类型不匹配（例如：SQLite 布尔值存储为 0/1 整数）可能需要手动 SQL 清理。

### 第四阶段：代码调整 (Phase 4: Code Adjustments)

1.  **布尔值处理**: 检查代码中的 `is_ai_strategy == 1` / `0` 判断，确保严格使用 `True` / `False`。
2.  **JSON 查询**: 如果我们使用 JSON 字段（例如在 `AI Analysis` 中），Postgres 语法 (`->>`) 与 SQLite `json_extract` 不同。（SQLAlchemy 处理大部分情况，但原生 SQL 需审查）。
3.  **自增主键**: 验证主键的 `Sequence` 处理（Postgres 比 SQLite 的 `rowid` 更严格）。

## 4. 高级特性路线图 (Post-Migration Roadmap)

迁移到 PostgreSQL 后，我们可以解锁：

1.  **混合搜索 (Hybrid Search / RAG)**:
    *   启用 `pgvector` 扩展。
    *   在 `StockNews` 表中存储 "新闻 Embeddings"。
    *   允许用户使用语义搜索提问 "显示受红海危机影响的股票"。
2.  **分区 (Partitioning)**:
    *   按 `ticker` 或 `sector` 对 `market_data_cache` 进行分区，以获得极致性能。
3.  **TimescaleDB**:
    *   将 `OHLCV` 表转换为超表 (hypertable)，用于实时 Tick 级数据摄入。

## 5. 建议 (Recommendation)

**现状 (Status Quo)**: 如果并发用户数保持在 < 5 人，可继续使用 SQLite。
**迁移触发点 (Trigger for Migration)**:
*   部署到云端 (AWS/GCP)。
*   集成 RAG (知识库)。
*   日志中频繁出现 "Database Locked" 错误。
