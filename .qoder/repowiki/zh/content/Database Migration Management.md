# 数据库迁移管理

<cite>
**本文档引用的文件**
- [backend/migrations/env.py](file://backend/migrations/env.py)
- [backend/alembic.ini](file://backend/alembic.ini)
- [backend/migrations/script.py.mako](file://backend/migrations/script.py.mako)
- [backend/app/core/database.py](file://backend/app/core/database.py)
- [backend/app/core/config.py](file://backend/app/core/config.py)
- [backend/app/models/__init__.py](file://backend/app/models/__init__.py)
- [backend/scripts/db/migrate_db.py](file://backend/scripts/db/migrate_db.py)
- [backend/scripts/db/init_db.py](file://backend/scripts/db/init_db.py)
- [backend/scripts/db/init_db_tables.py](file://backend/scripts/db/init_db_tables.py)
- [backend/scripts/db/sync_db.py](file://backend/scripts/db/sync_db.py)
- [backend/migrations/versions/35a834f440ba_baseline.py](file://backend/migrations/versions/35a834f440ba_baseline.py)
- [backend/migrations/versions/052e88ccdfbf_sync_schema_with_models.py](file://backend/migrations/versions/052e88ccdfbf_sync_schema_with_models.py)
- [backend/migrations/versions/261c72d24d12_initial_migration.py](file://backend/migrations/versions/261c72d24d12_initial_migration.py)
- [backend/app/models/user.py](file://backend/app/models/user.py)
- [backend/app/models/stock.py](file://backend/app/models/stock.py)
- [backend/app/models/portfolio.py](file://backend/app/models/portfolio.py)
- [backend/app/models/analysis.py](file://backend/app/models/analysis.py)
- [backend/app/main.py](file://backend/app/main.py)
- [backend/scripts/entrypoint.sh](file://backend/scripts/entrypoint.sh)
- [backend/scripts/migrate_db.py](file://backend/scripts/migrate_db.py)
- [backend/scripts/init_db.py](file://backend/scripts/init_db.py)
</cite>

## 更新摘要
**变更内容**
- 更新了迁移执行流程，从应用启动时内联迁移改为通过入口点脚本统一处理
- 新增了数据库脚本的统一管理结构（backend/scripts/db/）
- 移除了应用启动时的数据库同步逻辑
- 更新了迁移架构图以反映新的执行流程

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构概览](#架构概览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考虑](#性能考虑)
8. [故障排除指南](#故障排除指南)
9. [结论](#结论)

## 简介

本项目采用Alembic作为数据库迁移管理工具，结合SQLAlchemy ORM实现数据库版本控制。系统支持SQLite和PostgreSQL两种数据库后端，具备完整的迁移脚本生成、执行和回滚机制。通过结构化的迁移文件组织，实现了从初始数据库结构到复杂业务表的演进管理。

**重要变更**：系统现在通过入口点脚本统一处理数据库迁移，移除了应用启动时的内联迁移逻辑，实现了更清晰的职责分离和更好的启动性能。

## 项目结构

项目采用分层架构设计，数据库迁移相关文件主要分布在以下目录：

```mermaid
graph TB
subgraph "迁移管理结构"
A[backend/migrations/] --> B[versions/]
A --> C[env.py]
A --> D[script.py.mako]
E[backend/alembic.ini] --> A
end
subgraph "应用核心"
F[backend/app/core/] --> G[database.py]
F --> H[config.py]
end
subgraph "模型定义"
I[backend/app/models/] --> J[__init__.py]
I --> K[user.py]
I --> L[stock.py]
I --> M[portfolio.py]
I --> N[analysis.py]
end
subgraph "统一脚本管理"
O[backend/scripts/] --> P[migrate_db.py]
O --> Q[init_db.py]
O --> R[entrypoint.sh]
end
subgraph "新脚本目录"
S[backend/scripts/db/] --> T[migrate_db.py]
S --> U[init_db.py]
S --> V[init_db_tables.py]
S --> W[sync_db.py]
end
A --> I
G --> I
H --> A
R --> A
```

**图表来源**
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)
- [backend/alembic.ini:1-148](file://backend/alembic.ini#L1-L148)
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)

**章节来源**
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)
- [backend/alembic.ini:1-148](file://backend/alembic.ini#L1-L148)
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)

## 核心组件

### Alembic配置管理

系统使用Alembic作为主要的数据库迁移框架，配置文件位于`alembic.ini`中，支持多种数据库后端的配置管理。

### 数据库引擎配置

`database.py`文件定义了异步数据库引擎配置，支持SQLite和PostgreSQL两种数据库类型，并针对不同数据库进行了优化配置。

### 模型定义系统

应用模型通过SQLAlchemy ORM定义，包括用户、股票、投资组合、分析报告等核心业务实体，每个模型都定义了完整的字段结构和关系映射。

### 统一迁移执行

**新增** 系统现在通过入口点脚本统一处理数据库迁移，移除了应用启动时的内联迁移逻辑，提高了启动性能和职责分离。

**章节来源**
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)
- [backend/app/core/config.py:1-28](file://backend/app/core/config.py#L1-L28)
- [backend/app/models/__init__.py:1-6](file://backend/app/models/__init__.py#L1-L6)
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)

## 架构概览

系统采用三层架构设计，实现了数据库迁移的完整生命周期管理。**重要变更**：现在通过入口点脚本统一处理迁移，应用启动时只负责业务逻辑。

```mermaid
graph TB
subgraph "入口点执行层"
A[entrypoint.sh<br/>统一迁移执行]
B[alembic upgrade head<br/>数据库迁移]
end
subgraph "配置层"
C[alembic.ini<br/>配置文件]
D[env.py<br/>环境配置]
E[config.py<br/>应用配置]
end
subgraph "模型层"
F[models/__init__.py<br/>模型导入]
G[user.py<br/>用户模型]
H[stock.py<br/>股票模型]
I[portfolio.py<br/>投资组合模型]
J[analysis.py<br/>分析报告模型]
end
subgraph "迁移层"
K[versions/<br/>迁移脚本]
L[script.py.mako<br/>模板生成]
M[env.py<br/>运行时配置]
end
subgraph "应用启动层"
N[app.main.py<br/>FastAPI应用]
O[startup事件<br/>业务初始化]
end
A --> B --> M
C --> D --> M
E --> D
F --> G
F --> H
F --> I
F --> J
M --> K
L --> K
A --> N
N --> O
```

**图表来源**
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)
- [backend/app/core/config.py:1-28](file://backend/app/core/config.py#L1-L28)
- [backend/app/models/__init__.py:1-6](file://backend/app/models/__init__.py#L1-L6)

## 详细组件分析

### 迁移环境配置

迁移环境配置文件`env.py`负责协调数据库连接、模型元数据管理和迁移执行流程。

```mermaid
sequenceDiagram
participant Entrypoint as "入口点脚本"
participant Alembic as "Alembic"
participant Env as "env.py"
participant Config as "config.py"
participant Models as "models/__init__.py"
participant DB as "database.py"
Entrypoint->>Alembic : alembic upgrade head
Alembic->>Env : 读取配置
Env->>Config : 读取DATABASE_URL
Env->>Models : 导入所有模型
Models->>DB : 获取Base.metadata
Env->>Env : run_migrations_offline/online
Env->>DB : 建立数据库连接
Env->>Alembic : 执行迁移
Alembic->>Entrypoint : 迁移完成
```

**图表来源**
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)
- [backend/app/core/config.py:1-28](file://backend/app/core/config.py#L1-L28)
- [backend/app/models/__init__.py:1-6](file://backend/app/models/__init__.py#L1-L6)

**章节来源**
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)

### 应用启动流程变更

**更新** 应用启动时不再执行数据库迁移，只负责业务逻辑初始化。

```mermaid
sequenceDiagram
participant App as "FastAPI应用"
participant Main as "app.main.py"
participant DB as "数据库"
App->>Main : 启动应用
Main->>Main : 初始化日志和中间件
Main->>Main : 挂载路由
Main->>Main : startup事件
Main->>DB : 确保系统AI注册表
Main->>App : 返回应用实例
```

**图表来源**
- [backend/app/main.py:142-158](file://backend/app/main.py#L142-L158)

**章节来源**
- [backend/app/main.py:142-158](file://backend/app/main.py#L142-L158)

### 数据库引擎配置

数据库引擎配置针对不同数据库类型提供了专门的优化参数：

```mermaid
classDiagram
class DatabaseEngine {
+DATABASE_URL : str
+is_postgresql : bool
+connect_args : dict
+engine : AsyncEngine
+SessionLocal : sessionmaker
+Base : declarative_base
+get_db() AsyncGenerator
}
class SQLiteConfig {
+journal_mode : WAL
+synchronous : NORMAL
+busy_timeout : 30000
+pool_size : 5
}
class PostgreSQLConfig {
+ssl : require
+command_timeout : 60
+pool_size : 10
+max_overflow : 20
}
DatabaseEngine --> SQLiteConfig : "sqlite配置"
DatabaseEngine --> PostgreSQLConfig : "postgresql配置"
```

**图表来源**
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)

**章节来源**
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)

### 模型关系设计

系统的核心数据模型通过外键关系建立了清晰的业务关联：

```mermaid
erDiagram
USERS {
string id PK
string email UK
string hashed_password
boolean is_active
string membership_tier
string preferred_data_source
datetime created_at
datetime last_login
}
STOCKS {
string ticker PK
string name
string sector
string industry
float market_cap
float pe_ratio
float forward_pe
float eps
float dividend_yield
float beta
float fifty_two_week_high
float fifty_two_week_low
string exchange
string currency
}
PORTFOLIOS {
string id PK
string user_id FK
string ticker FK
float quantity
float avg_cost
float target_price
float stop_loss_price
datetime created_at
datetime updated_at
}
ANALYSIS_REPORTS {
string id PK
string user_id FK
string ticker FK
json input_context_snapshot
text ai_response_markdown
string sentiment_score
string model_used
datetime created_at
}
MARKET_DATA_CACHE {
string ticker PK
float current_price
float change_percent
float rsi_14
float ma_20
float ma_50
float ma_200
string market_status
datetime last_updated
}
STOCK_NEWS {
string id PK
string ticker FK
string title
string publisher
string link
datetime publish_time
string summary
string sentiment
}
USERS ||--o{ PORTFOLIOS : "拥有"
USERS ||--o{ ANALYSIS_REPORTS : "创建"
STOCKS ||--|| MARKET_DATA_CACHE : "对应"
STOCKS ||--o{ PORTFOLIOS : "被持有"
STOCKS ||--o{ ANALYSIS_REPORTS : "被分析"
STOCKS ||--o{ STOCK_NEWS : "相关新闻"
```

**图表来源**
- [backend/app/models/user.py:1-64](file://backend/app/models/user.py#L1-L64)
- [backend/app/models/stock.py:1-116](file://backend/app/models/stock.py#L1-L116)
- [backend/app/models/portfolio.py:1-33](file://backend/app/models/portfolio.py#L1-L33)
- [backend/app/models/analysis.py:1-66](file://backend/app/models/analysis.py#L1-L66)

**章节来源**
- [backend/app/models/user.py:1-64](file://backend/app/models/user.py#L1-L64)
- [backend/app/models/stock.py:1-116](file://backend/app/models/stock.py#L1-L116)
- [backend/app/models/portfolio.py:1-33](file://backend/app/models/portfolio.py#L1-L33)
- [backend/app/models/analysis.py:1-66](file://backend/app/models/analysis.py#L1-L66)

### 迁移脚本演进

系统通过一系列迁移脚本实现了数据库结构的逐步演进：

```mermaid
flowchart TD
A[baseline.py<br/>初始结构] --> B[initial_migration.py<br/>结构调整]
B --> C[sync_schema_with_models.py<br/>模型同步]
C --> D[技术指标扩展]
D --> E[业务功能增强]
E --> F[性能优化]
subgraph "迁移类型"
G[DDL变更]
H[数据迁移]
I[索引优化]
J[约束调整]
end
A --> G
B --> H
C --> I
D --> J
```

**图表来源**
- [backend/migrations/versions/35a834f440ba_baseline.py:1-128](file://backend/migrations/versions/35a834f440ba_baseline.py#L1-L128)
- [backend/migrations/versions/261c72d24d12_initial_migration.py:1-37](file://backend/migrations/versions/261c72d24d12_initial_migration.py#L1-L37)
- [backend/migrations/versions/052e88ccdfbf_sync_schema_with_models.py:1-115](file://backend/migrations/versions/052e88ccdfbf_sync_schema_with_models.py#L1-L115)

**章节来源**
- [backend/migrations/versions/35a834f440ba_baseline.py:1-128](file://backend/migrations/versions/35a834f440ba_baseline.py#L1-L128)
- [backend/migrations/versions/261c72d24d12_initial_migration.py:1-37](file://backend/migrations/versions/261c72d24d12_initial_migration.py#L1-L37)
- [backend/migrations/versions/052e88ccdfbf_sync_schema_with_models.py:1-115](file://backend/migrations/versions/052e88ccdfbf_sync_schema_with_models.py#L1-L115)

## 依赖关系分析

系统各组件之间的依赖关系如下：

```mermaid
graph TB
subgraph "配置依赖"
A[alembic.ini] --> B[env.py]
C[config.py] --> D[database.py]
D --> E[models]
end
subgraph "迁移依赖"
F[env.py] --> G[versions/]
H[script.py.mako] --> G
I[models/__init__.py] --> F
end
subgraph "执行依赖"
J[entrypoint.sh] --> K[alembic迁移]
L[app.main.py] --> M[业务初始化]
N[migrate_db.py] --> O[ai_advisor.db]
P[init_db.py] --> Q[数据库表创建]
end
A --> F
C --> D
D --> F
F --> G
H --> G
I --> F
J --> F
L --> M
N --> O
P --> Q
```

**图表来源**
- [backend/alembic.ini:1-148](file://backend/alembic.ini#L1-L148)
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)
- [backend/app/core/config.py:1-28](file://backend/app/core/config.py#L1-L28)
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)

**章节来源**
- [backend/alembic.ini:1-148](file://backend/alembic.ini#L1-L148)
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)

## 性能考虑

系统在数据库性能方面采用了多项优化策略：

### SQLite优化
- 启用WAL模式提升并发性能
- 调整同步级别和超时设置
- 优化连接池配置

### PostgreSQL优化
- 针对Neon服务的SSL强制要求
- 调整连接池大小和溢出配置
- 设置命令超时时间

### 迁移性能
- 使用批量操作减少迁移时间
- 优化索引创建顺序
- 合理的数据类型选择

### 启动性能优化
**新增** 通过入口点脚本统一处理迁移，移除了应用启动时的内联迁移逻辑，显著提升了应用启动速度。

## 故障排除指南

### 常见问题及解决方案

1. **数据库连接失败**
   - 检查DATABASE_URL配置
   - 验证数据库服务状态
   - 确认网络连接可用

2. **迁移执行失败**
   - 查看详细的错误日志
   - 检查模型定义完整性
   - 验证数据库权限设置

3. **数据迁移异常**
   - 确认数据类型兼容性
   - 检查外键约束关系
   - 验证索引完整性

4. **应用启动缓慢**
   - **新增** 检查入口点脚本是否正确执行迁移
   - 确认数据库连接池配置
   - 验证迁移脚本执行时间

**章节来源**
- [backend/migrations/env.py:1-86](file://backend/migrations/env.py#L1-L86)
- [backend/app/core/database.py:1-69](file://backend/app/core/database.py#L1-L69)
- [backend/scripts/entrypoint.sh:1-16](file://backend/scripts/entrypoint.sh#L1-L16)

## 结论

本项目的数据库迁移管理系统具有以下特点：

1. **完整的生命周期管理**：从初始建模到持续演进的完整流程
2. **多数据库支持**：灵活适配SQLite和PostgreSQL的不同需求
3. **结构化组织**：通过版本化脚本实现可追溯的变更管理
4. **性能优化**：针对不同数据库类型的专门优化配置
5. **可靠性保障**：完善的错误处理和回滚机制
6. **职责分离**：通过入口点脚本统一处理迁移，提升应用启动性能

**重要变更总结**：
- 迁移执行流程从应用启动时内联处理改为通过入口点脚本统一处理
- 新增了专门的数据库脚本目录（backend/scripts/db/）用于管理各种数据库操作
- 移除了应用启动时的数据库同步逻辑，提高了启动速度和稳定性
- 实现了更清晰的职责分离，使应用启动专注于业务逻辑

系统通过标准化的迁移流程和严格的版本控制，确保了数据库结构演进的可控性和安全性，为AI股票顾问应用的长期发展奠定了坚实的基础设施基础。