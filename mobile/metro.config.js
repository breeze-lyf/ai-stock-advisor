/**
 * Metro configuration for React Native
 * https://github.com/facebook/react-native
 *
 * @format
 */
const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

const defaultConfig = getDefaultConfig(__dirname);

/**
 * Taro Metro Config
 * 注意：需要先初始化 RN 项目才能使用
 * 执行: npx react-native init AIStockAdvisorRN
 */
const config = {
  transformer: {
    babelTransformerPath: require.resolve('react-native-sass-transformer'),
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true,
      },
    }),
  },
  resolver: {
    sourceExts: [
      ...defaultConfig.resolver.sourceExts,
      'scss',
      'sass',
      'css',
    ],
    // Taro 别名配置
    extraNodeModules: {
      '@tarojs/components': require.resolve('@tarojs/components-rn'),
      '@tarojs/taro': require.resolve('@tarojs/taro-rn'),
    },
  },
  watchFolders: [
    // 监听 src 目录
    `${__dirname}/src`,
  ],
};

module.exports = mergeConfig(defaultConfig, config);
