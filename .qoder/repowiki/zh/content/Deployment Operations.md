# 部署操作

<cite>
**本文档引用的文件**
- [deploy.sh](file://deploy.sh)
- [remote_deploy.sh](file://remote_deploy.sh)
- [start.sh](file://start.sh)
- [docker-compose.yml](file://docker-compose.yml)
- [backend/Dockerfile](file://backend/Dockerfile)
- [frontend/Dockerfile](file://frontend/Dockerfile)
- [.env](file://.env)
- [.env.example](file://.env.example)
- [backend/requirements.txt](file://backend/requirements.txt)
- [frontend/package.json](file://frontend/package.json)
- [backend/alembic.ini](file://backend/alembic.ini)
- [backend/scripts/init_db.py](file://backend/scripts/init_db.py)
- [backend/app/main.py](file://backend/app/main.py)
- [backend/app/core/config.py](file://backend/app/core/config.py)
- [backend/app/core/database.py](file://backend/app/core/database.py)
</cite>

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

本文档详细介绍了AI智能投顾系统的部署操作，包括本地开发环境部署、生产环境部署以及远程部署策略。该系统采用前后端分离架构，使用Docker容器化技术，支持多种数据库模式和市场数据提供商。

## 项目结构

AI智能投顾项目采用现代化的全栈架构，包含以下主要组件：

```mermaid
graph TB
subgraph "项目根目录"
ENV[".env 环境配置"]
DC[docker-compose.yml]
DS[deploy.sh]
RDS[remote_deploy.sh]
SS[start.sh]
end
subgraph "后端服务 (backend)"
BD[backend/Dockerfile]
REQ[requirements.txt]
MAIN[app/main.py]
CFG[app/core/config.py]
DB[app/core/database.py]
API[app/api/v1/]
SCRIPTS[scripts/]
end
subgraph "前端服务 (frontend)"
FD[frontend/Dockerfile]
PKG[package.json]
APP[app/]
COMP[components/]
end
subgraph "数据库"
SQLITE[SQLite 数据库]
PG[PostgreSQL 数据库]
REDIS[Redis 缓存]
end
ENV --> CFG
DC --> BD
DC --> FD
BD --> REQ
FD --> PKG
MAIN --> API
API --> DB
DB --> SQLITE
DB --> PG
DB --> REDIS
```

**图表来源**
- [docker-compose.yml](file://docker-compose.yml#L1-L53)
- [backend/Dockerfile](file://backend/Dockerfile#L1-L29)
- [frontend/Dockerfile](file://frontend/Dockerfile#L1-L30)

**章节来源**
- [docker-compose.yml](file://docker-compose.yml#L1-L53)
- [backend/Dockerfile](file://backend/Dockerfile#L1-L29)
- [frontend/Dockerfile](file://frontend/Dockerfile#L1-L30)

## 核心组件

### 部署脚本体系

系统提供了三种主要的部署方式：

1. **本地开发部署** (`start.sh`) - 适合开发者本地环境
2. **生产环境部署** (`deploy.sh`) - 适合服务器环境
3. **远程部署** (`remote_deploy.sh`) - 支持跨主机部署

### 容器编排配置

Docker Compose配置定义了完整的微服务架构：

```mermaid
graph LR
subgraph "网络: stock-network"
subgraph "数据库服务"
DB[PostgreSQL 15]
SQLITE[SQLite 文件]
end
subgraph "缓存服务"
REDIS[Redis 7]
end
subgraph "应用服务"
BACKEND[FastAPI 后端]
FRONTEND[Next.js 前端]
end
end
DB -.-> BACKEND
REDIS -.-> BACKEND
SQLITE -.-> BACKEND
BACKEND --> FRONTEND
```

**图表来源**
- [docker-compose.yml](file://docker-compose.yml#L1-L53)

**章节来源**
- [start.sh](file://start.sh#L1-L61)
- [deploy.sh](file://deploy.sh#L1-L52)
- [remote_deploy.sh](file://remote_deploy.sh#L1-L80)

## 架构概览

系统采用分层架构设计，支持多种部署模式：

```mermaid
graph TB
subgraph "客户端层"
Browser[Web 浏览器]
Mobile[移动应用]
end
subgraph "API 网关层"
API[FastAPI 应用]
CORS[CORS 中间件]
AUTH[认证中间件]
end
subgraph "业务逻辑层"
ROUTES[路由控制器]
SERVICES[业务服务]
INDICATORS[技术指标计算]
MARKET[市场数据聚合]
end
subgraph "数据访问层"
DB[(数据库)]
CACHE[(Redis 缓存)]
FILE[(文件存储)]
end
Browser --> API
Mobile --> API
API --> CORS
API --> AUTH
API --> ROUTES
ROUTES --> SERVICES
SERVICES --> INDICATORS
SERVICES --> MARKET
SERVICES --> DB
SERVICES --> CACHE
SERVICES --> FILE
```

**图表来源**
- [backend/app/main.py](file://backend/app/main.py#L1-L129)
- [backend/app/core/config.py](file://backend/app/core/config.py#L1-L28)
- [backend/app/core/database.py](file://backend/app/core/database.py#L1-L53)

## 详细组件分析

### 本地开发环境部署

本地开发部署脚本提供了完整的开发环境启动流程：

```mermaid
sequenceDiagram
participant Dev as 开发者
participant Start as start.sh
participant Backend as 后端服务
participant Frontend as 前端服务
participant Scripts as 自动刷新脚本
Dev->>Start : 执行本地部署
Start->>Start : 检查依赖 (npm, python3)
Start->>Backend : 启动 FastAPI (端口 8000)
Start->>Scripts : 启动自动刷新脚本
Start->>Frontend : 启动 Next.js (端口 3000)
Backend->>Dev : 提供 API 文档
Frontend->>Dev : 开发界面
Scripts->>Backend : 定时数据更新
```

**图表来源**
- [start.sh](file://start.sh#L1-L61)
- [backend/app/main.py](file://backend/app/main.py#L19-L53)

**章节来源**
- [start.sh](file://start.sh#L1-L61)

### 生产环境部署流程

生产环境部署脚本实现了自动化部署和数据库迁移：

```mermaid
flowchart TD
Start([开始部署]) --> CheckEnv["检查 .env 配置文件"]
CheckEnv --> EnvOK{"配置文件存在?"}
EnvOK --> |否| Error1["退出部署 (错误码 1)"]
EnvOK --> |是| StopOld["停止旧容器"]
StopOld --> BuildNew["构建新镜像并启动"]
BuildNew --> WaitStable["等待服务稳定"]
WaitStable --> CheckBackend{"后端服务正常?"}
CheckBackend --> |否| Error2["查看日志并退出"]
CheckBackend --> |是| RunMigrations["执行数据库迁移"]
RunMigrations --> Cleanup["清理无用镜像"]
Cleanup --> Done([部署完成])
Error1 --> End([结束])
Error2 --> End
Done --> End
```

**图表来源**
- [deploy.sh](file://deploy.sh#L1-L52)

**章节来源**
- [deploy.sh](file://deploy.sh#L1-L52)

### 远程部署机制

远程部署脚本支持跨主机自动化部署：

```mermaid
sequenceDiagram
participant Admin as 管理员
participant Local as 本地主机
participant Remote as 远程服务器
participant Docker as Docker 引擎
Admin->>Local : 执行远程部署脚本
Local->>Remote : rsync 同步文件
Remote->>Remote : 连接远程服务器
Remote->>Docker : 检测 docker compose 版本
Remote->>Docker : 停止旧服务
Remote->>Docker : 构建并启动新服务
Remote->>Docker : 等待服务稳定
Remote->>Docker : 执行数据库迁移
Remote->>Docker : 清理无用镜像
Remote-->>Admin : 返回部署结果
```

**图表来源**
- [remote_deploy.sh](file://remote_deploy.sh#L1-L80)

**章节来源**
- [remote_deploy.sh](file://remote_deploy.sh#L1-L80)

### 容器化配置分析

#### 后端容器配置

后端服务使用Python 3.11 Slim基础镜像，配置了生产环境的高性能设置：

```mermaid
classDiagram
class BackendContainer {
+Python 3.11 Slim
+Gunicorn Web Server
+4个工作进程
+异步Uvicorn Worker
+端口 8000
+生产环境优化
}
class Dependencies {
+FastAPI 0.128.0
+SQLAlchemy 2.0.45
+Alembic 1.18.1
+Asyncpg 0.31.0
+Pydantic 2.12.5
+uvicorn 0.40.0
}
class Environment {
+DATABASE_URL
+REDIS_URL
+SECRET_KEY
+ALPHA_VANTAGE_API_KEY
}
BackendContainer --> Dependencies : 包含
BackendContainer --> Environment : 使用
```

**图表来源**
- [backend/Dockerfile](file://backend/Dockerfile#L1-L29)
- [backend/requirements.txt](file://backend/requirements.txt#L1-L77)

#### 前端容器配置

前端服务使用多阶段构建优化镜像大小：

```mermaid
classDiagram
class FrontendContainer {
+多阶段构建
+Node.js 20 Slim
+生产环境优化
+端口 3000
}
class BuildStage {
+构建阶段
+安装依赖
+编译静态资源
}
class RuntimeStage {
+运行阶段
+轻量级运行时
+启动生产服务
}
FrontendContainer --> BuildStage : 第一阶段
FrontendContainer --> RuntimeStage : 第二阶段
```

**图表来源**
- [frontend/Dockerfile](file://frontend/Dockerfile#L1-L30)
- [frontend/package.json](file://frontend/package.json#L1-L51)

**章节来源**
- [backend/Dockerfile](file://backend/Dockerfile#L1-L29)
- [frontend/Dockerfile](file://frontend/Dockerfile#L1-L30)

### 数据库配置与迁移

系统支持SQLite和PostgreSQL两种数据库模式：

```mermaid
erDiagram
subgraph "数据库配置"
SQLITE_CONFIG {
+sqlite+aiosqlite:///./ai_advisor.db
+WAL 模式
+连接池优化
}
POSTGRES_CONFIG {
+postgresql+asyncpg://user:pass@host:5432/db
+环境变量配置
+Docker 网络访问
}
end
subgraph "迁移系统"
ALEMBIC {
+版本控制
+自动迁移
+回滚支持
}
MIGRATIONS {
+版本化迁移
+数据结构变更
}
end
SQLITE_CONFIG --> ALEMBIC
POSTGRES_CONFIG --> ALEMBIC
ALEMBIC --> MIGRATIONS
```

**图表来源**
- [.env](file://.env#L1-L5)
- [backend/alembic.ini](file://backend/alembic.ini#L1-L148)
- [backend/app/core/database.py](file://backend/app/core/database.py#L1-L53)

**章节来源**
- [.env](file://.env#L1-L5)
- [backend/alembic.ini](file://backend/alembic.ini#L1-L148)
- [backend/app/core/database.py](file://backend/app/core/database.py#L1-L53)

## 依赖关系分析

### 环境配置管理

系统使用分层配置管理策略：

```mermaid
graph TD
subgraph "配置层次"
ENV_EXAMPLE[.env.example 模板]
ENV_LOCAL[.env 本地配置]
ENV_PROD[生产环境变量]
end
subgraph "配置类型"
BACKEND_CFG[后端配置]
FRONTEND_CFG[前端配置]
DB_CFG[数据库配置]
API_CFG[API密钥配置]
end
ENV_EXAMPLE --> ENV_LOCAL
ENV_LOCAL --> ENV_PROD
ENV_LOCAL --> BACKEND_CFG
ENV_LOCAL --> FRONTEND_CFG
ENV_LOCAL --> DB_CFG
ENV_LOCAL --> API_CFG
```

**图表来源**
- [.env](file://.env#L1-L5)
- [.env.example](file://.env.example#L1-L10)
- [backend/app/core/config.py](file://backend/app/core/config.py#L1-L28)

**章节来源**
- [.env](file://.env#L1-L5)
- [.env.example](file://.env.example#L1-L10)
- [backend/app/core/config.py](file://backend/app/core/config.py#L1-L28)

### 依赖包管理

后端依赖包采用精确版本控制：

```mermaid
graph LR
subgraph "核心框架"
FASTAPI[FastAPI 0.128.0]
SQLALCHEMY[SQLAlchemy 2.0.45]
PYDANTIC[Pydantic 2.12.5]
end
subgraph "数据库相关"
AIOSQLITE[aiosqlite 0.22.1]
ASYNC_PG[asyncpg 0.31.0]
ALEMBIC[Alembic 1.18.1]
end
subgraph "数据处理"
NUMPY[NumPy 2.4.1]
PANDAS[pandas 2.3.3]
YFINANCE[yfinance]
AKSHARE[akshare]
end
subgraph "网络请求"
HTTPX[httpx 0.28.1]
REQUESTS[requests 2.32.5]
CURL_CFFI[curl_cffi 0.13.0]
end
FASTAPI --> SQLALCHEMY
SQLALCHEMY --> AIOSQLITE
PYDANTIC --> HTTPX
NUMPY --> PANDAS
YFINANCE --> HTTPX
AKSHARE --> HTTPX
```

**图表来源**
- [backend/requirements.txt](file://backend/requirements.txt#L1-L77)

**章节来源**
- [backend/requirements.txt](file://backend/requirements.txt#L1-L77)

## 性能考虑

### 容器性能优化

系统在容器层面实施了多项性能优化措施：

1. **连接池优化**: SQLite连接池大小限制为5，防止文件锁竞争
2. **WAL模式**: 使用Write-Ahead Logging提升并发性能
3. **预连接检查**: 每次使用前验证连接有效性
4. **Gunicorn配置**: 4个工作进程配合异步worker

### 部署性能策略

```mermaid
flowchart TD
Performance[性能优化] --> Container[容器层面]
Performance --> Network[网络层面]
Performance --> Storage[存储层面]
Container --> PoolSize[连接池大小限制]
Container --> WALMode[WAL日志模式]
Container --> PrePing[预连接检查]
Container --> Gunicorn[Gunicorn进程池]
Network --> CORS[CORS优化]
Network --> Proxy[代理配置]
Network --> LoadBalancing[负载均衡]
Storage --> BusyTimeout[忙等待超时]
Storage --> PoolRecycle[连接回收]
Storage --> JournalMode[日志模式]
```

**章节来源**
- [backend/app/core/database.py](file://backend/app/core/database.py#L6-L33)
- [backend/Dockerfile](file://backend/Dockerfile#L25-L28)

## 故障排除指南

### 常见部署问题

| 问题类型 | 症状 | 解决方案 |
|---------|------|----------|
| 环境变量缺失 | 部署失败或服务启动异常 | 检查 `.env` 文件完整性，参考 `.env.example` |
| 数据库连接失败 | 启动时报数据库错误 | 验证 `DATABASE_URL` 配置正确性 |
| 端口冲突 | 服务无法绑定到指定端口 | 检查端口占用情况，修改端口配置 |
| 依赖安装失败 | pip安装报错 | 清理缓存，重新安装依赖 |

### 日志分析

系统提供多层次的日志输出：

1. **应用日志** (`app.log`): API调用和错误日志
2. **数据库日志** (`backend_debug.log`): 数据库操作日志
3. **启动日志** (`startup.log`): 服务启动过程日志
4. **Docker日志** (`docker-compose logs`): 容器运行状态

**章节来源**
- [backend/app/main.py](file://backend/app/main.py#L13-L25)
- [deploy.sh](file://deploy.sh#L34-L38)

### 调试技巧

```mermaid
flowchart LR
Debug[调试流程] --> Logs[查看日志]
Debug --> Config[检查配置]
Debug --> Network[网络连通性]
Debug --> Dependencies[依赖检查]
Logs --> AppLog[应用日志]
Logs --> DockerLog[Docker日志]
Logs --> DBLog[数据库日志]
Config --> EnvCheck[环境变量检查]
Config --> PortCheck[端口检查]
Config --> DBCheck[数据库配置检查]
Network --> PingTest[Ping测试]
Network --> TelnetTest[Telnet测试]
Network --> DNSResolve[DNS解析]
Dependencies --> PipCheck[pip依赖检查]
Dependencies --> NodeCheck[node依赖检查]
Dependencies --> DockerBuild[Docker构建检查]
```

## 结论

AI智能投顾系统的部署操作具有以下特点：

1. **多环境支持**: 同时支持本地开发、生产环境和远程部署
2. **容器化架构**: 采用Docker容器化技术，确保环境一致性
3. **自动化程度高**: 提供完整的自动化部署脚本
4. **监控完善**: 全面的日志记录和错误处理机制
5. **性能优化**: 在多个层面实施性能优化措施

建议在生产环境中：
- 使用独立的生产环境配置文件
- 配置适当的监控和告警机制
- 定期备份数据库和重要配置
- 制定详细的灾难恢复计划