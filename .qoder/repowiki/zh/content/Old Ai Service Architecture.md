# 旧版AI服务架构

<cite>
**本文档引用的文件**
- [main.py](file://backend/app/main.py)
- [ai_service.py](file://backend/app/services/ai_service.py)
- [config.py](file://backend/app/core/config.py)
- [prompts.py](file://backend/app/core/prompts.py)
- [analysis.py](file://backend/app/api/v1/endpoints/analysis.py)
- [api.py](file://backend/app/api/v1/api.py)
- [ai_config.py](file://backend/app/models/ai_config.py)
- [provider_config.py](file://backend/app/models/provider_config.py)
- [analysis_model.py](file://backend/app/models/analysis.py)
- [market_data.py](file://backend/app/services/market_data.py)
- [database.py](file://backend/app/core/database.py)
- [ai_response_parser.py](file://backend/app/utils/ai_response_parser.py)
- [portfolio.py](file://backend/app/api/v1/endpoints/portfolio.py)
- [README.md](file://README.md)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考虑](#性能考虑)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)

## 简介
本项目是一个工业级AI智能投资顾问后端系统，基于FastAPI构建，集成了多源市场数据与LLM分析能力。旧版AI服务架构围绕AI服务核心组件展开，实现了从数据采集、AI分析到结果持久化的完整闭环。

## 项目结构
后端采用分层架构设计，主要分为以下层次：
- 应用入口层：FastAPI应用初始化与中间件配置
- API接口层：按功能模块划分的路由控制器
- 服务层：核心业务逻辑，包括AI分析、市场数据、通知等服务
- 数据访问层：ORM模型与数据库操作
- 工具层：通用工具函数与解析器

```mermaid
graph TB
subgraph "应用入口层"
Main[main.py<br/>应用初始化]
end
subgraph "API接口层"
APIRouter[api.py<br/>路由聚合]
AnalysisAPI[analysis.py<br/>AI分析接口]
PortfolioAPI[portfolio.py<br/>组合管理接口]
end
subgraph "服务层"
AIService[ai_service.py<br/>AI服务核心]
MarketData[market_data.py<br/>市场数据服务]
Parser[ai_response_parser.py<br/>响应解析器]
end
subgraph "数据访问层"
Models[models/<br/>ORM模型]
Database[database.py<br/>数据库配置]
end
subgraph "配置层"
Config[config.py<br/>系统配置]
Prompts[prompts.py<br/>提示词模板]
end
Main --> APIRouter
APIRouter --> AnalysisAPI
APIRouter --> PortfolioAPI
AnalysisAPI --> AIService
AnalysisAPI --> MarketData
AIService --> Parser
AIService --> Models
MarketData --> Models
AnalysisAPI --> Models
Database --> Models
Config --> AIService
Prompts --> AnalysisAPI
```

**图表来源**
- [main.py:1-146](file://backend/app/main.py#L1-L146)
- [api.py:1-33](file://backend/app/api/v1/api.py#L1-L33)
- [ai_service.py:1-254](file://backend/app/services/ai_service.py#L1-L254)

**章节来源**
- [main.py:1-146](file://backend/app/main.py#L1-L146)
- [api.py:1-33](file://backend/app/api/v1/api.py#L1-L33)

## 核心组件
旧版AI服务架构包含以下核心组件：

### AIService（AI服务核心）
AIService是整个AI分析系统的核心，负责：
- 模型配置管理与缓存
- 供应商API密钥解析与动态URL切换
- 多供应商故障转移机制
- 统一的AI调用接口

### MarketDataService（市场数据服务）
负责从多个数据源获取实时市场数据，包括：
- 股票报价与技术指标
- 基本面数据与估值百分位
- 资金流向与新闻资讯
- 数据缓存与持久化

### Prompt模板系统
提供标准化的AI提示词模板，确保分析质量的一致性：
- 个股分析模板
- 组合分析模板
- 合规免责声明
- 结构化输出约束

### 数据模型层
包含完整的数据模型定义：
- AI模型配置模型
- 分析报告模型
- 供应商配置模型
- 市场数据缓存模型

**章节来源**
- [ai_service.py:22-254](file://backend/app/services/ai_service.py#L22-L254)
- [market_data.py:19-407](file://backend/app/services/market_data.py#L19-L407)
- [prompts.py:1-192](file://backend/app/core/prompts.py#L1-L192)
- [ai_config.py:1-21](file://backend/app/models/ai_config.py#L1-L21)
- [analysis_model.py:1-92](file://backend/app/models/analysis.py#L1-L92)

## 架构总览
旧版AI服务架构采用事件驱动的异步设计，实现了高并发与高可用：

```mermaid
sequenceDiagram
participant Client as 客户端
participant API as API接口
participant AIService as AI服务
participant Provider as 供应商API
participant DB as 数据库
Client->>API : 发送分析请求
API->>API : 验证用户权限
API->>DB : 获取市场数据
DB-->>API : 返回数据
API->>AIService : 调用AI分析
AIService->>AIService : 解析API密钥
AIService->>Provider : 调用供应商API
Provider-->>AIService : 返回AI响应
AIService-->>API : 返回结构化结果
API->>DB : 持久化分析报告
DB-->>API : 确认保存
API-->>Client : 返回分析结果
```

**图表来源**
- [analysis.py:241-626](file://backend/app/api/v1/endpoints/analysis.py#L241-L626)
- [ai_service.py:161-212](file://backend/app/services/ai_service.py#L161-L212)

系统采用多供应商架构，支持故障转移和负载均衡：
- 主供应商：根据用户配置优先选择
- 备用供应商：在主供应商失败时自动切换
- 动态URL：支持自定义API基地址
- 超时控制：每供应商独立超时配置

**章节来源**
- [ai_service.py:161-212](file://backend/app/services/ai_service.py#L161-L212)
- [provider_config.py:12-48](file://backend/app/models/provider_config.py#L12-L48)

## 详细组件分析

### AI服务组件分析

#### AIService类结构
```mermaid
classDiagram
class AIService {
+dict _model_config_cache
+list _provider_cache
+float CACHE_TTL
+float _provider_cache_time
+get_model_config(model_key, db) AIModelConfig
+call_provider(provider_config, model_id, prompt, api_key, custom_url) str
+test_connection(provider_key, api_key, base_url) Tuple[bool, str]
+generate_analysis(ticker, market_data, portfolio_data, ...) str
+generate_portfolio_analysis(items, ...) str
-_resolve_api_key(provider_key, user) Tuple[Optional[str], Optional[str]]
-_dispatch_with_fallback(prompt, model_config, user, db) str
}
class AIModelConfig {
+String id
+String key
+String provider
+String model_id
+Boolean is_active
+String description
+DateTime created_at
+DateTime updated_at
}
class ProviderConfig {
+String id
+String provider_key
+String display_name
+String base_url
+String api_key_env
+Integer priority
+Boolean is_active
+Integer max_retries
+Integer timeout_seconds
}
AIService --> AIModelConfig : 使用
AIService --> ProviderConfig : 依赖
```

**图表来源**
- [ai_service.py:22-254](file://backend/app/services/ai_service.py#L22-L254)
- [ai_config.py:6-21](file://backend/app/models/ai_config.py#L6-L21)
- [provider_config.py:12-48](file://backend/app/models/provider_config.py#L12-L48)

#### AI调用流程
```mermaid
flowchart TD
Start([开始AI调用]) --> LoadConfig["加载模型配置"]
LoadConfig --> GetProviders["获取供应商列表"]
GetProviders --> CheckPrimary{"主供应商可用?"}
CheckPrimary --> |是| ResolveKey["解析API密钥"]
CheckPrimary --> |否| NextProvider["尝试下一个供应商"]
ResolveKey --> CallAPI["调用供应商API"]
CallAPI --> Success{"调用成功?"}
Success --> |是| ParseResponse["解析响应"]
Success --> |否| AuthError{"认证错误?"}
AuthError --> |是| Stop["停止并返回错误"]
AuthError --> |否| NextProvider
NextProvider --> CheckFallback{"用户启用故障转移?"}
CheckFallback --> |是| GetProviders
CheckFallback --> |否| Stop
ParseResponse --> Persist["持久化结果"]
Persist --> Return([返回结果])
Stop --> Return
```

**图表来源**
- [ai_service.py:161-212](file://backend/app/services/ai_service.py#L161-L212)

**章节来源**
- [ai_service.py:22-254](file://backend/app/services/ai_service.py#L22-L254)

### 市场数据服务分析

#### 数据获取策略
MarketDataService采用智能缓存和故障转移策略：

```mermaid
flowchart TD
Request[数据请求] --> CheckCache{检查缓存}
CheckCache --> |新鲜缓存| ReturnCache[返回缓存数据]
CheckCache --> |需要刷新| FetchProviders[获取数据源]
FetchProviders --> PriceOnly{仅价格模式?}
PriceOnly --> |是| QuoteOnly[仅获取报价]
PriceOnly --> |否| FullData[获取完整数据]
QuoteOnly --> ProcessData[处理数据]
FullData --> ProcessData
ProcessData --> CacheData[更新缓存]
CacheData --> ReturnData[返回数据]
ReturnCache --> End([结束])
ReturnData --> End
```

**图表来源**
- [market_data.py:20-66](file://backend/app/services/market_data.py#L20-L66)

#### 数据源集成
系统支持多种数据源，包括：
- AkShare：国内A股数据
- YFinance：美股数据
- 财联社：新闻资讯
- Tavily：搜索支持

**章节来源**
- [market_data.py:67-227](file://backend/app/services/market_data.py#L67-L227)

### API接口层分析

#### 分析接口流程
```mermaid
sequenceDiagram
participant Client as 客户端
participant AnalysisAPI as 分析API
participant MarketData as 市场数据
participant AIService as AI服务
participant Parser as 解析器
participant DB as 数据库
Client->>AnalysisAPI : POST /analysis/{ticker}
AnalysisAPI->>AnalysisAPI : 验证用户权限
AnalysisAPI->>MarketData : 获取市场数据
MarketData-->>AnalysisAPI : 返回技术指标
AnalysisAPI->>Parser : 获取新闻上下文
Parser-->>AnalysisAPI : 返回新闻数据
AnalysisAPI->>AIService : 调用AI分析
AIService-->>AnalysisAPI : 返回AI响应
AnalysisAPI->>Parser : 解析结构化数据
Parser-->>AnalysisAPI : 返回解析结果
AnalysisAPI->>DB : 持久化分析报告
DB-->>AnalysisAPI : 确认保存
AnalysisAPI-->>Client : 返回分析结果
```

**图表来源**
- [analysis.py:241-626](file://backend/app/api/v1/endpoints/analysis.py#L241-L626)

**章节来源**
- [analysis.py:241-626](file://backend/app/api/v1/endpoints/analysis.py#L241-L626)

## 依赖关系分析

### 组件依赖图
```mermaid
graph TB
subgraph "核心依赖"
FastAPI[FastAPI框架]
SQLAlchemy[SQLAlchemy ORM]
AsyncIO[异步I/O]
end
subgraph "AI服务依赖"
GenAI[Google GenAI SDK]
Httpx[HTTP客户端]
Pydantic[数据验证]
end
subgraph "数据源依赖"
AkShare[AkShare库]
YFinance[YFinance库]
Tavily[Tavily API]
end
subgraph "配置依赖"
PydanticSettings[Pydantic Settings]
JWT[JWT认证]
Cryptography[加密库]
end
AIService --> GenAI
AIService --> Httpx
AnalysisAPI --> AIService
AnalysisAPI --> MarketData
MarketData --> AkShare
MarketData --> YFinance
MarketData --> Tavily
AnalysisAPI --> Pydantic
AnalysisAPI --> JWT
AnalysisAPI --> Cryptography
Database --> SQLAlchemy
Database --> AsyncIO
```

**图表来源**
- [ai_service.py:1-12](file://backend/app/services/ai_service.py#L1-L12)
- [analysis.py:1-25](file://backend/app/api/v1/endpoints/analysis.py#L1-L25)
- [database.py:1-69](file://backend/app/core/database.py#L1-L69)

### 数据流依赖
系统采用事件驱动的数据流架构：

```mermaid
flowchart LR
subgraph "数据输入"
MarketData[市场数据]
UserInput[用户输入]
Config[配置数据]
end
subgraph "处理层"
Preprocessing[数据预处理]
AIAnalysis[AI分析引擎]
Postprocessing[结果后处理]
end
subgraph "数据输出"
StructuredData[结构化数据]
Cache[缓存数据]
Reports[分析报告]
end
MarketData --> Preprocessing
UserInput --> Preprocessing
Config --> Preprocessing
Preprocessing --> AIAnalysis
AIAnalysis --> Postprocessing
Postprocessing --> StructuredData
Postprocessing --> Cache
Postprocessing --> Reports
```

**图表来源**
- [analysis.py:277-501](file://backend/app/api/v1/endpoints/analysis.py#L277-L501)
- [ai_response_parser.py:32-100](file://backend/app/utils/ai_response_parser.py#L32-L100)

**章节来源**
- [ai_service.py:1-254](file://backend/app/services/ai_service.py#L1-L254)
- [market_data.py:1-407](file://backend/app/services/market_data.py#L1-L407)

## 性能考虑
旧版AI服务架构在性能方面采用了多项优化措施：

### 缓存策略
- 模型配置缓存：5分钟TTL，减少数据库查询
- 供应商列表缓存：10分钟TTL，支持动态更新
- 市场数据缓存：1分钟TTL，支持价格模式优化

### 异步处理
- 全面采用async/await模式
- 并发任务限制：信号量控制最大并发数
- 超时控制：每供应商独立超时配置

### 数据库优化
- SQLite WAL模式：提升并发读写性能
- 连接池配置：PostgreSQL优化参数
- 原子操作：UPSERT减少查询次数

## 故障排查指南

### 常见问题诊断
1. **AI服务不可用**
   - 检查API密钥配置
   - 验证供应商连接性
   - 查看错误日志

2. **市场数据获取失败**
   - 检查数据源可用性
   - 验证网络连接
   - 查看缓存状态

3. **分析结果异常**
   - 检查提示词模板
   - 验证数据完整性
   - 查看解析器日志

### 调试工具
- 全局异常处理器：捕获未处理异常
- 请求日志：记录请求耗时和用户信息
- 详细错误追踪：包含堆栈信息

**章节来源**
- [main.py:33-47](file://backend/app/main.py#L33-L47)
- [ai_service.py:140-159](file://backend/app/services/ai_service.py#L140-L159)

## 结论
旧版AI服务架构展现了良好的工程实践，具有以下特点：

### 优势
- **模块化设计**：清晰的分层架构，职责分离明确
- **高可用性**：多供应商故障转移机制
- **性能优化**：全面的缓存策略和异步处理
- **扩展性强**：插件化的数据源和供应商支持

### 改进建议
- 增强监控告警机制
- 优化错误恢复策略
- 加强安全防护措施
- 完善测试覆盖

该架构为AI智能投资顾问系统提供了稳定可靠的技术基础，能够满足工业级应用的需求。