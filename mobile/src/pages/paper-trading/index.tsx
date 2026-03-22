import { View, Text } from '@tarojs/components'
import './index.scss'

export default function PaperTradingPage() {
  return (
    <View className="paper-trading-page">
      <View className="coming-soon">
        <Text className="icon">🚧</Text>
        <Text className="title">模拟交易</Text>
        <Text className="desc">功能开发中，敬请期待...</Text>
      </View>
    </View>
  )
}
