# React Native 适配说明

由于 Taro 4.x 的 React Native 支持需要 React Native 0.84+（要求 React 19），
而当前项目使用 React 18，存在依赖冲突。

## 解决方案

### 方案 1：独立 RN 项目（推荐）

1. 在 mobile 同级目录创建独立的 RN 项目：
```bash
npx react-native@latest init AIStockAdvisorRN --template react-native-template-typescript
```

2. 将 Taro 编译输出复制到 RN 项目：
```bash
npm run build:rn
cp -r dist/rn/* ../AIStockAdvisorRN/
```

3. 在 RN 项目中安装 Taro 运行时：
```bash
cd ../AIStockAdvisorRN
npm install @tarojs/taro-rn @tarojs/components-rn
```

### 方案 2：升级 React 版本

等待 Taro 官方支持 React 18，或者升级项目到 React 19（可能导致其他兼容性问题）。

### 方案 3：使用 Expo（简化版）

```bash
npx create-expo-app AIStockAdvisorExpo --template blank-typescript
```

然后使用 Taro 的 Expo 插件适配。

## 当前状态

- ✅ H5 构建：可用
- ✅ 微信小程序构建：可用
- ⚠️ React Native：需要额外配置

## 构建命令

```bash
# H5
npm run build:h5

# 微信小程序
npm run build:weapp

# React Native（需要先完成上述配置）
npm run build:rn
```
