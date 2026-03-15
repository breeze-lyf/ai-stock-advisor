from google import genai
from google.genai import types
from app.core.config import settings
from app.core import security
from app.core.prompts import build_stock_analysis_prompt, build_portfolio_analysis_prompt
import logging
import httpx
import json
import asyncio
import time
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_config import AIModelConfig
from app.models.provider_config import ProviderConfig
from app.models.user import User

# 配置日志
logger = logging.getLogger(__name__)

class AIService:
    _model_config_cache = {}  
    CACHE_TTL = 300  # 缓存 5 分钟
    _provider_cache = [] # 缓存供应商列表
    _provider_cache_time = 0

    @classmethod
    async def get_model_config(cls, model_key: str, db: AsyncSession = None) -> AIModelConfig:
        """获取模型配置的阶梯式查找"""
        if model_key in cls._model_config_cache:
            config, timestamp = cls._model_config_cache[model_key]
            if time.time() - timestamp < cls.CACHE_TTL:
                return config

        if db:
            try:
                stmt = select(AIModelConfig).where(AIModelConfig.key == model_key)
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    cls._model_config_cache[model_key] = (config, time.time())
                    return config
            except Exception as e:
                logger.error(f"查询 AI 模型配置失败: {e}")

        # 兜底回退
        fallback_map = {
            "deepseek-v3": "Pro/deepseek-ai/DeepSeek-V3.2",
            "deepseek-r1": "Pro/deepseek-ai/DeepSeek-R1",
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-235B-A22B-Thinking",
            "gemini-1.5-flash": "gemini-1.5-flash"
        }
        fallback_id = fallback_map.get(model_key, "Pro/deepseek-ai/DeepSeek-V3.2")
        provider = "gemini" if "gemini" in model_key else "siliconflow"
        return AIModelConfig(key=model_key, provider=provider, model_id=fallback_id)

    @staticmethod
    async def _resolve_api_key(provider_key: str, user: Optional[User]) -> Optional[str]:
        """
        统一 API Key 解析器：优先级 用户级加密 Key > 系统级 Key
        """
        if user:
            # 根据供应商动态获取用户表中的字段
            user_key_attr = f"api_key_{provider_key}"
            if hasattr(user, user_key_attr):
                encrypted_key = getattr(user, user_key_attr)
                if encrypted_key:
                    try:
                        return security.decrypt_api_key(encrypted_key)
                    except Exception as e:
                        logger.error(f"解密用户 {provider_key} API Key 失败: {e}")

        # 降级到系统环境变量
        env_key_map = {
            "siliconflow": settings.SILICONFLOW_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY
        }
        return env_key_map.get(provider_key)

    @staticmethod
    async def call_provider(provider_config: Any, model_id: str, prompt: str, api_key: str) -> str:
        """通用供应商调用器"""
        if provider_config.provider_key == "gemini":
            try:
                client = genai.Client(api_key=api_key)
                response = await client.aio.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type='application/json')
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini API Error: {str(e)}")
                raise

        # OpenAI 兼容接口调用 (SiliconFlow, DeepSeek-Direct 等)
        url = f"{provider_config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=provider_config.timeout_seconds, trust_env=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"{provider_config.provider_key} API Error: {response.status_code} | {response.text}")
                # 针对 401/402 不触发重试/切换，直接抛出业务异常
                if response.status_code in [401, 402]:
                    raise ValueError(f"Provider Auth/Balance Error: {response.status_code}")
                response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]

    @classmethod
    async def _dispatch_with_fallback(cls, prompt: str, model_config: AIModelConfig, user: Optional[User], db: AsyncSession) -> str:
        """核心路由：带故障转移的提供商分发"""
        # 1. 获取所有可用的供应商列表，按优先级排序
        if time.time() - cls._provider_cache_time > 600 or not cls._provider_cache:
            stmt = select(ProviderConfig).where(ProviderConfig.is_active == True).order_by(ProviderConfig.priority.asc())
            result = await db.execute(stmt)
            cls._provider_cache = result.scalars().all()
            cls._provider_cache_time = time.time()

        # 2. 确定初始供应商。如果 model_config 指定了 provider，先尝试它。
        providers = list(cls._provider_cache)
        primary_provider = next((p for p in providers if p.provider_key == model_config.provider), None)
        
        # 排序：将指定的 provider 放在第一位
        if primary_provider:
            providers.remove(primary_provider)
            providers.insert(0, primary_provider)

        last_error = "未知错误"
        for provider in providers:
            try:
                # 解析 API Key
                api_key = await cls._resolve_api_key(provider.provider_key, user)
                if not api_key:
                    logger.warning(f"跳过供应商 {provider.provider_key}: 缺少 API Key")
                    continue
                
                # 特殊逻辑：如果是 fallback 到的新 provider，可能需要映射型号 ID
                # 简单处理：如果是非主 provider，直接使用常用型号
                current_model_id = model_config.model_id if provider.provider_key == model_config.provider else (
                    "Pro/deepseek-ai/DeepSeek-V3.2" if provider.provider_key == "siliconflow" else "gemini-1.5-flash"
                )

                logger.info(f"尝试使用供应商 {provider.provider_key} (Model: {current_model_id})")
                return await cls.call_provider(provider, current_model_id, prompt, api_key)

            except ValueError as ve:
                # 认证或余额错误，不再继续尝试该供应商
                last_error = str(ve)
                continue
            except Exception as e:
                logger.warning(f"供应商 {provider.provider_key} 调用失败: {e}")
                last_error = str(e)
                continue

        return f"**Error**: AI 服务暂时不可用 (尝试了 {len(providers)} 个供应商)。最后错误: {last_error}"

    @classmethod
    async def generate_analysis(cls, ticker: str, market_data: dict, portfolio_data: dict, news_data: list = None, 
                                macro_context: str = None, fundamental_data: dict = None, previous_analysis: dict = None, 
                                model: str = "gemini-1.5-flash", db: AsyncSession = None, user_id: str = None) -> str:
        """主方法：生成个股深度诊断 (重构版)"""
        # 1. 获取用户信息（如果提供）以便解析私有 Key
        user = None
        if user_id and db:
            user_stmt = select(User).where(User.id == user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

        # 2. 构建 Prompt (解耦到 prompts.py)
        prompt = build_stock_analysis_prompt(
            ticker=ticker,
            market_data=market_data,
            portfolio_data=portfolio_data,
            fundamental_data=fundamental_data or {},
            news_data=news_data or [],
            macro_context=macro_context,
            previous_analysis=previous_analysis
        )
        logger.info(f"--- AI ANALYSIS PROMPT FOR {ticker} (Length: {len(prompt)}) ---")

        # 3. 分发请求 (带故障转移)
        model_config = await cls.get_model_config(model, db)
        return await cls._dispatch_with_fallback(prompt, model_config, user, db)

    @classmethod
    async def generate_portfolio_analysis(cls, portfolio_items: list, market_news: str = None, macro_context: str = None, 
                                          model: str = "gemini-1.5-flash", db: AsyncSession = None, user_id: str = None) -> str:
        """生成全量持仓健康诊断报告 (重构版)"""
        if not portfolio_items:
            return json.dumps({"error": "暂无持仓数据"})

        user = None
        if user_id and db:
            user_stmt = select(User).where(User.id == user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

        prompt = build_portfolio_analysis_prompt(portfolio_items, market_news, macro_context)
        
        model_config = await cls.get_model_config(model, db)
        return await cls._dispatch_with_fallback(prompt, model_config, user, db)
