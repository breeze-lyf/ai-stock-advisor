import { defineConfig, type UserConfigExport } from '@tarojs/cli'

import path from 'path'

export default defineConfig<'webpack5'>(async (merge) => {
  const baseConfig: UserConfigExport<'webpack5'> = {
    projectName: 'ai-stock-advisor-mobile',
    date: '2025-3-22',
    designWidth: 750,
    deviceRatio: {
      640: 2.34 / 2,
      750: 1,
      375: 2,
      828: 1.81 / 2,
    },
    sourceRoot: 'src',
    outputRoot: `dist/${process.env.TARO_ENV}`,
    plugins: [
      '@tarojs/plugin-platform-weapp',
      '@tarojs/plugin-platform-alipay',
      '@tarojs/plugin-platform-h5',
    ],
    defineConstants: {},
    copy: {
      patterns: [],
      options: {},
    },
    framework: 'react',
    compiler: {
      type: 'webpack5',
      prebundle: {
        enable: false,
      },
    },
    cache: {
      enable: false,
    },
    alias: {
      '@': path.resolve(__dirname, '..', 'src'),
      '@/components': path.resolve(__dirname, '..', 'src/components'),
      '@/services': path.resolve(__dirname, '..', 'src/services'),
      '@/store': path.resolve(__dirname, '..', 'src/store'),
      '@/hooks': path.resolve(__dirname, '..', 'src/hooks'),
      '@/utils': path.resolve(__dirname, '..', 'src/utils'),
      '@/types': path.resolve(__dirname, '..', 'src/types'),
    },
    mini: {
      postcss: {
        pxtransform: {
          enable: true,
          config: {},
        },
        cssModules: {
          enable: false,
          config: {
            namingPattern: 'module',
            generateScopedName: '[name]__[local]___[hash:base64:5]',
          },
        },
      },
      miniCssExtractPluginOption: {
        ignoreOrder: true,
      },
      webpackChain(chain) {
        chain.resolve.extensions.prepend('.tsx').prepend('.ts')
      },
    },
    h5: {
      publicPath: '/',
      staticDirectory: 'static',
      miniCssExtractPluginOption: {
        ignoreOrder: true,
        filename: 'css/[name].[hash].css',
        chunkFilename: 'css/[name].[chunkhash].css',
      },
      postcss: {
        autoprefixer: {
          enable: true,
          config: {},
        },
        cssModules: {
          enable: false,
          config: {
            namingPattern: 'module',
            generateScopedName: '[name]__[local]___[hash:base64:5]',
          },
        },
      },
      webpackChain(chain) {
        chain.resolve.extensions.prepend('.tsx').prepend('.ts')
      },
    },
    rn: {
      appName: 'AIStockAdvisor',
      postcss: {
        cssModules: {
          enable: false,
        },
      },
    },
  }

  if (process.env.NODE_ENV === 'development') {
    return merge({}, baseConfig, {
      env: {
        NODE_ENV: '"development"',
      },
      defineConstants: {},
      mini: {},
      h5: {},
    })
  }

  return merge({}, baseConfig, {
    env: {
      NODE_ENV: '"production"',
    },
    defineConstants: {},
    mini: {},
    h5: {
      enableExtract: true,
      miniCssExtractPluginOption: {
        ignoreOrder: true,
        filename: 'css/[name].[hash].css',
        chunkFilename: 'css/[name].[chunkhash].css',
      },
    },
  })
})
