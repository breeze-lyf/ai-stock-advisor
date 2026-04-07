#!/bin/bash
# 更新服务器 AI API Key 配置脚本
# 用法：./update_server_api_key.sh <your_siliconflow_api_key>

if [ -z "$1" ]; then
    echo "用法：$0 <你的 SiliconFlow API Key>"
    echo "例如：$0 sk-abcdefghijk..."
    exit 1
fi

NEW_API_KEY="$1"
SSH_KEY=~/.ssh/key.pem
SERVER=root@47.100.109.73

echo "正在更新服务器 API Key..."

# 方法 1: 直接更新数据库中的 provider_config 表
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "docker exec stock_backend python << 'PYEOF'
import asyncio
import asyncpg

async def update():
    conn = await asyncpg.connect(
        'postgresql://ai_stock_app:KfZpdJdl7PsVlEJfij7oBZLb@host.docker.internal:5432/ai_stock_advisor'
    )

    # 更新 siliconflow provider 的 base_url（如果不存在则创建）
    await conn.execute('''
        INSERT INTO provider_config (provider_key, base_url, display_name, priority, is_active, timeout_seconds, created_at, updated_at)
        VALUES ('siliconflow', 'https://api.siliconflow.cn/v1', 'SiliconFlow', 1, true, 300, NOW(), NOW())
        ON CONFLICT (provider_key) DO UPDATE SET
            base_url = 'https://api.siliconflow.cn/v1',
            is_active = true,
            updated_at = NOW()
    ''')

    print('Provider config updated successfully')

    # 验证
    r = await conn.fetchval('SELECT base_url FROM provider_config WHERE provider_key = \\'siliconflow\\'')
    print(f'SiliconFlow base_url: {r}')

    await conn.close()

asyncio.run(update())
PYEOF
"

echo "服务器 API Key 配置已更新！"
echo "请重启容器以生效：ssh -i ~/.ssh/key.pem root@47.100.109.73 'docker restart stock_backend'"
