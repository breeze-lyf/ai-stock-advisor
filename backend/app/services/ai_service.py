# 设置代理环境变量（解决 Python 3.14 + httpx 兼容性问题）
import os
from app.core.config import settings
if settings.HTTP_PROXY:
    os.environ.setdefault("HTTP_PROXY", settings.HTTP_PROXY)
    os.environ.setdefault("HTTPS_PROXY", settings.HTTP_PROXY)

from app.core import security
from app.core.prompts import build_stock_analysis_prompt, build_portfolio_analysis_prompt
import logging
import httpx
import json
import asyncio
import time
from datetime import datetime
from typing import Optional, List, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_config import AIModelConfig
from app.models.provider_config import ProviderConfig
from app.models.user import User
from app.models.user_ai_model import UserAIModel
from app.models.user_provider_credential import UserProviderCredential
from app.schemas.ai_config import AIModelRuntimeConfig, ProviderRuntimeConfig

# 配置日志
logger = logging.getLogger(__name__)
# AI 调用専用 logger：所有 prompt 和计时数据写入 ai_calls.log
ai_call_logger = logging.getLogger("app.ai_calls")

class AIService:
    _model_config_cache = {}  
    CACHE_TTL = 300  # 缓存 5 分钟
    _provider_cache = [] # 缓存供应商列表
    _provider_cache_time = 0

    @staticmethod
    def _normalize_user_model_base_url(raw_base_url: str | None) -> str:
        normalized = (raw_base_url or "").strip().rstrip("/")
        normalized = normalized.replace("/models", "").replace("/chat/completions", "")
        return normalized

    @classmethod
    async def get_user_ai_model(
        cls,
        model_key: str,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[UserAIModel]:
        if not db:
            return None

        stmt = select(UserAIModel).where(
            UserAIModel.user_id == user_id,
            UserAIModel.key == model_key,
            UserAIModel.is_active == True,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def call_user_ai_model(cls, model: UserAIModel, prompt: str) -> str:
        if not model.encrypted_api_key:
            raise ValueError("User AI model missing API key")

        api_key = security.decrypt_api_key(model.encrypted_api_key)
        base_url = cls._normalize_user_model_base_url(model.base_url)
        provider_note = (model.provider_note or "").lower()
        is_gemini = "gemini" in provider_note or "googleapis.com" in base_url or "generativelanguage" in base_url

        provider_config = type(
            "TempProvider",
            (),
            {
                "provider_key": "gemini" if is_gemini else "custom",
                "base_url": base_url,
                "timeout_seconds": 300,
            },
        )()
        return await cls.call_provider(provider_config, model.model_id, prompt, api_key, base_url)

    @classmethod
    async def get_default_model_for_provider(cls, provider_key: str, db: Optional[AsyncSession] = None) -> str:
        if db:
            try:
                stmt = (
                    select(AIModelConfig)
                    .where(AIModelConfig.provider == provider_key, AIModelConfig.is_active == True)
                    .order_by(AIModelConfig.updated_at.desc(), AIModelConfig.created_at.desc())
                    .limit(1)
                )
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    return config.model_id
            except Exception as e:
                logger.warning(f"查询供应商 {provider_key} 默认模型失败: {e}")

        provider_defaults = {
            "siliconflow": "deepseek-ai/DeepSeek-V3",
            "deepseek": "deepseek-chat",
            "dashscope": "qwen3.5-plus",
        }
        return provider_defaults.get(provider_key, "gpt-4o-mini")

    @classmethod
    async def get_model_config(cls, model_key: str, db: AsyncSession = None) -> AIModelRuntimeConfig:
        """获取模型配置的阶梯式查找，返回解耦的 Pydantic 模型"""
        if model_key in cls._model_config_cache:
            config_data, timestamp = cls._model_config_cache[model_key]
            if time.time() - timestamp < cls.CACHE_TTL:
                return AIModelRuntimeConfig(**config_data)

        if db:
            try:
                stmt = select(AIModelConfig).where(AIModelConfig.key == model_key)
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    # 立即转换为字典保存到缓存，避免 Session 关闭后无法访问
                    config_data = {
                        "key": config.key,
                        "provider": config.provider,
                        "model_id": config.model_id,
                        "description": config.description
                    }
                    cls._model_config_cache[model_key] = (config_data, time.time())
                    return AIModelRuntimeConfig(**config_data)
            except Exception as e:
                logger.error(f"查询 AI 模型配置失败: {e}")

        # 兜底回退
        fallback_map = {
            "deepseek-v3": "Pro/deepseek-ai/DeepSeek-V3.2",
            "deepseek-r1": "Pro/deepseek-ai/DeepSeek-R1",
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-235B-A22B-Thinking",
        }
        fallback_id = fallback_map.get(model_key, "Pro/deepseek-ai/DeepSeek-V3.2")
        provider = "dashscope" if ("qwen" in model_key or "dashscope" in model_key) else "siliconflow"
        return AIModelRuntimeConfig(key=model_key, provider=provider, model_id=fallback_id)

    @staticmethod
    async def _resolve_api_key(
        provider_key: str,
        user: Optional[User],
        db: Optional[AsyncSession] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        统一 API Key & URL 解析器：优先级 用户级加密 Key > 系统级 Key
        返回: (api_key, custom_base_url)
        """
        custom_base_url = None
        
        if user:
            # 0. 优先从统一凭据表中读取
            if db:
                try:
                    credential_stmt = select(UserProviderCredential).where(
                        UserProviderCredential.user_id == user.id,
                        UserProviderCredential.provider_key == provider_key,
                        UserProviderCredential.is_enabled == True,
                    )
                    credential_result = await db.execute(credential_stmt)
                    credential = credential_result.scalar_one_or_none()
                    if credential:
                        decrypted_key = None
                        if credential.encrypted_api_key:
                            try:
                                decrypted_key = security.decrypt_api_key(credential.encrypted_api_key)
                            except Exception as e:
                                logger.error(f"解密用户 {provider_key} 统一凭据失败: {e}")
                        if decrypted_key or credential.base_url:
                            return decrypted_key, credential.base_url
                except Exception as e:
                    logger.warning(f"查询用户 {user.id} 的统一 Provider 凭据失败: {e}")

            # 1. 尝试从 api_configs JSON 中解析自定义配置
            if user.api_configs:
                try:
                    configs = json.loads(user.api_configs)
                    if provider_key in configs:
                        custom_base_url = configs[provider_key].get("base_url")
                except Exception as e:
                    logger.warning(f"解析用户 {user.id} 的 api_configs 失败: {e}")

            # 2. 从用户表获取加密的 Key
            user_key_attr = f"api_key_{provider_key}"
            if hasattr(user, user_key_attr):
                encrypted_key = getattr(user, user_key_attr)
                if encrypted_key:
                    try:
                        return security.decrypt_api_key(encrypted_key), custom_base_url
                    except Exception as e:
                        logger.error(f"解密用户 {provider_key} API Key 失败: {e}")

        # 3. 降级到系统环境变量
        env_key_map = {
            "siliconflow": settings.SILICONFLOW_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "dashscope": settings.DASHSCOPE_API_KEY,
        }
        return env_key_map.get(provider_key), None

    @staticmethod
    async def call_provider(
        provider_config: Any, 
        model_id: str, 
        prompt: str, 
        api_key: str, 
        custom_url: str = None,
        require_json: bool = True
    ) -> str:
        """通用供应商调用器"""
        call_start = time.monotonic()
        provider_key = provider_config.provider_key

        # 将完整 prompt 写入专用日志，不打终端
        ai_call_logger.info(
            f"[PROMPT] {provider_key}/{model_id}",
            extra={
                "provider": provider_key,
                "model": model_id,
                "prompt_len": len(prompt),
                "prompt": prompt,          # 完整 prompt
                "phase": "request",
            }
        )
        logger.info(f"[AI] 调用 {provider_key}/{model_id} (prompt {len(prompt)}字符)")

        base_url = custom_url or provider_config.base_url
        # 移除硬编码的 60s 限制，推理模型建议 300s
        timeout = provider_config.timeout_seconds or 300

        # OpenAI 兼容接口
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async def _do_call(use_json: bool):
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            if use_json:
                payload["response_format"] = {"type": "json_object"}

            client_kwargs = {
                "timeout": httpx.Timeout(timeout, connect=10.0),
                "trust_env": True
            }
            t_send = time.monotonic()
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(url, json=payload, headers=headers)
            t_recv = time.monotonic()
            ai_call_logger.debug(
                f"[HTTP] {provider_key} http={response.status_code}",
                extra={
                    "provider": provider_key, "phase": "http",
                    "http_status": response.status_code,
                    "request_s": round(t_recv - t_send, 3),
                    "total_s": round(t_recv - call_start, 3),
                }
            )
            return response

        try:
            response = await _do_call(use_json=require_json)
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - call_start
            ai_call_logger.error(
                f"[TIMEOUT] {provider_key}: {e}",
                extra={"provider": provider_key, "phase": "timeout", "total_s": round(elapsed, 3)}
            )
            logger.warning(f"[AI] 请求超时 ({provider_key}, {elapsed:.1f}s)")
            raise
        except Exception:
            raise

        if response.status_code == 400 and require_json:
            error_data = {}
            try:
                if response.headers.get("content-type") == "application/json":
                    error_data = response.json()
            except Exception:
                pass
            error_msg = error_data.get("error", {}).get("message", "").lower()
            if "response_format" in error_msg or "json_object" in error_msg:
                logger.info(f"[AI] 降级重试 (no json_object)...")
                response = await _do_call(use_json=False)

        if response.status_code != 200:
            error_text = response.text
            elapsed = time.monotonic() - call_start
            ai_call_logger.error(
                f"[FAIL] {provider_key} HTTP {response.status_code}",
                extra={"provider": provider_key, "phase": "error",
                       "http_status": response.status_code,
                       "response_body": error_text[:500],
                       "total_s": round(elapsed, 3)}
            )
            logger.warning(f"[AI] {provider_key} 返回 {response.status_code} ({elapsed:.1f}s)")
            if response.status_code in [401, 402]:
                raise ValueError(f"Auth Error: {response.status_code}")
            raise

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        elapsed = time.monotonic() - call_start
        ai_call_logger.info(
            f"[DONE] {provider_key}/{model_id}",
            extra={
                "provider": provider_key, "model": model_id, "phase": "done",
                "total_s": round(elapsed, 3),
                "response_len": len(content),
                "response": content,  # 记录完整回答
            }
        )
        logger.info(f"[AI] {provider_key} 完成 ✔  {elapsed:.1f}s | {len(content)}字符")
        return content

    @classmethod
    async def call_siliconflow(
        cls,
        prompt: str,
        api_key: str,
        model: str = "deepseek-v3",
        db: Optional[AsyncSession] = None,
        base_url: Optional[str] = None,
    ) -> str:
        """兼容现有宏观服务调用的 SiliconFlow 快捷入口。"""
        model_config = await cls.get_model_config(model, db)
        provider_config = ProviderRuntimeConfig(
            provider_key="siliconflow",
            base_url=base_url or "https://api.siliconflow.cn/v1",
            timeout_seconds=300,
        )
        return await cls.call_provider(
            provider_config,
            model_config.model_id,
            prompt,
            api_key,
            base_url,
        )

    @classmethod
    async def test_connection(
        cls,
        provider_key: str,
        api_key: str,
        base_url: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        model_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """测试 AI 供应商连接性"""
        try:
            # 构造临时供应商配置对象
            default_url = base_url or ""
            if not default_url and db:
                try:
                    stmt = select(ProviderConfig).where(ProviderConfig.provider_key == provider_key)
                    result = await db.execute(stmt)
                    provider = result.scalar_one_or_none()
                    if provider:
                        default_url = provider.base_url
                except Exception as e:
                    logger.warning(f"查询供应商 {provider_key} 默认地址失败: {e}")

            if not default_url:
                default_url = "https://api.siliconflow.cn/v1" if provider_key == "siliconflow" else ""

            provider_config = ProviderRuntimeConfig(
                provider_key=provider_key,
                base_url=default_url,
                timeout_seconds=10
            )
            
            test_prompt = "Say ok"
            # 根据供应商选择一个轻量模型进行测试
            test_model = model_id or await cls.get_default_model_for_provider(provider_key, db)
            
            print(f"\n[AI_DEBUG] 开始测试连接: {provider_key}")
            await cls.call_provider(provider_config, test_model, test_prompt, api_key, base_url, require_json=False)
            print(f"[AI_DEBUG] 测试连接成功")
            return True, "连接成功"
        except httpx.ReadTimeout:
            logger.warning(f"AI 供应商 {provider_key} 连接测试超时 (10s)")
            return False, "连接失败: 请求超时 (10s)，供应商无响应"
        except Exception as e:
            error_msg = str(e) or e.__class__.__name__
            logger.warning(f"AI 供应商 {provider_key} 连接测试失败: {error_msg}")
            return False, f"连接失败: {error_msg}"

    @staticmethod
    def infer_provider_key(base_url: Optional[str] = None, provider_hint: Optional[str] = None) -> str:
        hint = (provider_hint or "").strip().lower()
        url = (base_url or "").strip().lower()

        combined = f"{hint} {url}"
        if any(token in combined for token in ["gemini", "googleapis.com", "generativelanguage"]):
            return "gemini"
        if "siliconflow" in combined:
            return "siliconflow"
        if "deepseek" in combined:
            return "deepseek"
        if "dashscope" in combined or "aliyuncs.com" in combined or "qwen" in combined:
            return "dashscope"
        if "minimax" in combined:
            return "minimax"
        if "anthropic" in combined or "claude" in combined:
            return "anthropic"
        if "openrouter" in combined:
            return "openrouter"
        return "openai-compatible"

    @classmethod
    async def _dispatch_with_fallback(cls, prompt: str, model_config: AIModelRuntimeConfig, user: Optional[User], db: AsyncSession) -> str:
        """核心路由：带故障转移的提供商分发"""
        
        # 1. 获取所有可用的供应商列表，按优先级排序
        # 注意：缓存时提取属性值，避免 ORM 对象在 session 关闭后无法访问
        try:
            if time.time() - cls._provider_cache_time > 600 or not cls._provider_cache:
                stmt = select(ProviderConfig).where(ProviderConfig.is_active == True).order_by(ProviderConfig.priority.asc())
                result = await db.execute(stmt)
                raw_providers = result.scalars().all()
                # 提取关键属性，避免 ORM 对象在 session 关闭后失效
                cls._provider_cache = [
                    {
                        'provider_key': p.provider_key,
                        'base_url': p.base_url,
                        'timeout_seconds': p.timeout_seconds or 120,
                    }
                    for p in raw_providers
                ]
                cls._provider_cache_time = time.time()
        except Exception as e:
            logger.warning(f"获取供应商配置失败: {e}，使用内存缓存的供应商列表")
            if not cls._provider_cache:
                return f"**Error**: AI 服务暂时不可用 (无法获取供应商配置: {e})"
        
        if not cls._provider_cache:
            return f"**Error**: AI 服务暂时不可用 (没有可用的 AI 供应商)"

        # 2. 确定目标供应商
        provider = next((p for p in cls._provider_cache if p['provider_key'] == model_config.provider), None)
        
        if not provider:
            # 如果没找到匹配的供应商，尝试列表中的第一个（通常是 SiliconFlow）
            if cls._provider_cache:
                provider = cls._provider_cache[0]
            else:
                return f"**Error**: AI 服务暂时不可用 (没有找到匹配供应商 {model_config.provider})"

        try:
            # 解析 API Key & Custom URL
            api_key, custom_url = await cls._resolve_api_key(provider['provider_key'], user, db)
            
            if not api_key:
                return f"**Error**: 供应商 {provider['provider_key']} 缺少 API Key"
            
            current_model_id = (
                model_config.model_id
                if provider['provider_key'] == model_config.provider
                else await cls.get_default_model_for_provider(provider['provider_key'], db)
            )

            logger.info(f"使用供应商 {provider['provider_key']} (Model: {current_model_id}) URL: {custom_url or 'default'}")
            
            # 使用 Pydantic 模型传递配置
            provider_config = ProviderRuntimeConfig(
                provider_key=provider['provider_key'],
                base_url=custom_url or provider['base_url'],
                timeout_seconds=provider.get('timeout_seconds', 300),
            )
            
            return await cls.call_provider(provider_config, current_model_id, prompt, api_key, custom_url)

        except Exception as e:
            logger.error(f"供应商 {provider['provider_key']} 调用失败: {e}")
            return f"**Error**: AI 调用失败 ({provider['provider_key']})。错误: {e}"

    @classmethod
    async def generate_analysis(cls, ticker: str, market_data: dict, news_data: list = None, 
                                macro_context: str = None, fundamental_data: dict = None, previous_analysis: dict = None, 
                                model: str = "deepseek-v3", db: AsyncSession = None, user_id: str = None) -> str:
        """主方法：生成个股深度诊断"""
        
        user = None
        if user_id and db:
            try:
                user_stmt = select(User).where(User.id == user_id)
                user_result = await db.execute(user_stmt)
                user = user_result.scalar_one_or_none()
            except Exception as e:
                logger.warning(f"获取用户信息失败: {e}")

        prompt = build_stock_analysis_prompt(
            ticker=ticker,
            market_data=market_data,
            fundamental_data=fundamental_data or {},
            news_data=news_data or [],
            macro_context=macro_context,
            previous_analysis=previous_analysis
        )

        if user and db:
            user_model = await cls.get_user_ai_model(model, user.id, db)
            if user_model:
                try:
                    return await cls.call_user_ai_model(user_model, prompt)
                except Exception as e:
                    logger.warning(f"用户自定义模型 {model} 调用失败: {e}")
                    if not user:
                        return f"**Error**: AI 调用失败。错误: {e}"
                    # 即使失败也不再回滚
                    return f"**Error**: 用户自定义模型 {model} 调用失败。错误: {e}"

        model_config = await cls.get_model_config(model, db)
        return await cls._dispatch_with_fallback(prompt, model_config, user, db)

    @classmethod
    async def generate_portfolio_analysis(cls, portfolio_items: list, market_news: str = None, macro_context: str = None, 
                                          model: str = "deepseek-v3", db: AsyncSession = None, user_id: str = None) -> str:
        """生成全量持仓健康诊断报告"""
        if not portfolio_items:
            return json.dumps({"error": "暂无持仓数据"})

        user = None
        if user_id and db:
            user_stmt = select(User).where(User.id == user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

        prompt = build_portfolio_analysis_prompt(portfolio_items, market_news, macro_context)

        if user and db:
            user_model = await cls.get_user_ai_model(model, user.id, db)
            if user_model:
                try:
                    return await cls.call_user_ai_model(user_model, prompt)
                except Exception as e:
                    logger.warning(f"用户自定义组合模型 {model} 调用失败: {e}")
                    return json.dumps({"error": f"AI 服务暂时不可用: {e}"})

        model_config = await cls.get_model_config(model, db)
        return await cls._dispatch_with_fallback(prompt, model_config, user, db)


ai_service = AIService
