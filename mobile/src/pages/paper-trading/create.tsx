import { View, Text } from '@tarojs/components'
import './create.scss'

export default function CreateTradePage() {
  return (
    <View className="create-trade-page">
      <View className="coming-soon">
        <Text className="icon">🚧</Text>
        <Text className="title">创建交易</Text>
        <Text className="desc">功能开发中，敬请期待...</Text>
      </View>
    </View>
  )
}
