export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/login/index',
    'pages/register/index',
    'pages/portfolio/index',
    'pages/portfolio/add',
    'pages/stock/detail',
    'pages/analysis/index',
    'pages/analysis/portfolio',
    'pages/macro/index',
    'pages/paper-trading/index',
    'pages/paper-trading/create',
    'pages/alerts/index',
    'pages/settings/index',
    'pages/settings/password',
    'pages/settings/ai-models/index',
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#1a1a2e',
    navigationBarTitleText: 'AI 智能投顾',
    navigationBarTextStyle: 'white',
  },
  tabBar: {
    color: '#999999',
    selectedColor: '#6366f1',
    backgroundColor: '#1a1a2e',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/index/index',
        text: '首页',
      },
      {
        pagePath: 'pages/portfolio/index',
        text: '持仓',
      },
      {
        pagePath: 'pages/macro/index',
        text: '宏观',
      },
      {
        pagePath: 'pages/settings/index',
        text: '我的',
      },
    ],
  },
})
