# Frontend

Web 前端基于 Next.js App Router，负责登录注册、首页组合概览、个股分析、组合分析、设置中心，以及正在接入中的日历、量化和选股页面。

## 技术基线

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- Axios + OpenAPI 类型

## 本地运行

```bash
cd frontend
npm run dev -- -p 3000
```

如果从仓库根目录统一启动，优先使用：

```bash
./scripts/start.sh dev
```

## 目录约定

- `app/`: 路由与页面编排
- `components/`: 业务组件与通用组件
- `features/`: 领域 API、hooks、状态逻辑
- `lib/`: 基础库与工具函数
- `types/`: OpenAPI 生成类型和本地补充类型

## 开发规则

- 接口调用优先放在 `features/*/api.ts`
- 页面层只做路由和页面编排，不堆复杂业务计算
- 后端契约变更后，同步更新 `types/schema.d.ts`
- 默认以根目录文档为准，不在本目录重复维护全局启动说明
