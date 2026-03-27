
import os
import sys
from dotenv import load_dotenv

# 1. 检查当前工作目录
print(f"Current Working Directory: {os.getcwd()}")

# 2. 检查 .env 文件是否存在
env_path = os.path.join(os.getcwd(), ".env")
print(f".env exists: {os.path.exists(env_path)}")

# 3. 手动加载并检查
load_dotenv(env_path)
print(f"DATABASE_URL from os.environ: {os.environ.get('DATABASE_URL')}")

# 4. 检查 app.core.config 的加载结果
sys.path.append(os.path.abspath(os.getcwd()))
try:
    from app.core.config import settings
    print(f"settings.DATABASE_URL: {settings.DATABASE_URL}")
except Exception as e:
    print(f"Error loading settings: {e}")
