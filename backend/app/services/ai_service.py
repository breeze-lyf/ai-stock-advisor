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
from typing import Optional, List, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_config import AIModelConfig
from app.models.provider_config import ProviderConfig
from app.models.user import User
from app.models.user_ai_model import UserAIModel
from app.models.user_provider_credential import UserProviderCredential

# 配置日志
logger = logging.getLogger(__name__)

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
                "timeout_seconds": 30,
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
            "gemini": "gemini-1.5-flash",
            "dashscope": "qwen3.5-plus",
        }
        return provider_defaults.get(provider_key, "gpt-4o-mini")

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
            "gemini-1.5-flash": "gemini-1.5-flash",
            "qwen3.5-plus": "qwen3.5-plus",
        }
        fallback_id = fallback_map.get(model_key, "Pro/deepseek-ai/DeepSeek-V3.2")
        provider = "dashscope" if ("qwen" in model_key or "dashscope" in model_key) else ("gemini" if "gemini" in model_key else "siliconflow")
        return AIModelConfig(key=model_key, provider=provider, model_id=fallback_id)

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
            "gemini": settings.GEMINI_API_KEY,
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
        # 确定最终基地址
        base_url = custom_url or provider_config.base_url

        if provider_config.provider_key == "gemini":
            try:
                # Gemini SDK 暂时不支持动态 base_url（除非通过环境变量或特殊配置），此处主要适配 Key
                client = genai.Client(api_key=api_key)
                config_params = {}
                if require_json:
                    config_params['response_mime_type'] = 'application/json'
                
                response = await client.aio.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_params)
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini API Error: {str(e)}")
                raise

        # OpenAI 兼容接口调用 (SiliconFlow, DeepSeek-Direct 等)
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
                "timeout": provider_config.timeout_seconds,
                "trust_env": True
            }
            if settings.HTTP_PROXY:
                client_kwargs["proxy"] = settings.HTTP_PROXY
            
            print(f"\n[AI_DEBUG] >>> 发起请求")
            print(f"[AI_DEBUG] URL: {url}")
            print(f"[AI_DEBUG] Proxy: {settings.HTTP_PROXY or 'None'}")
            print(f"[AI_DEBUG] Model: {model_id}")
            print(f"[AI_DEBUG] Payload: {json.dumps(payload, ensure_ascii=False)}")
            
            start_time = time.time()
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(url, json=payload, headers=headers)
            
            duration = time.time() - start_time
            print(f"[AI_DEBUG] <<< 收到响应 (耗时: {duration:.2f}s)")
            print(f"[AI_DEBUG] Status: {response.status_code}")
            if response.status_code != 200:
                print(f"[AI_DEBUG] Error Body: {response.text}")
            
            return response

        try:
            response = await _do_call(use_json=require_json)
        except Exception:
            raise
        
        # 如果强制 JSON 失败（通常报 400 invalid_parameter），尝试降级
        if response.status_code == 400 and require_json:
            error_data = {}
            try:
                if response.headers.get("content-type") == "application/json":
                    error_data = response.json()
            except Exception:
                pass
            
            error_msg = error_data.get("error", {}).get("message", "").lower()
            if "response_format" in error_msg or "json_object" in error_msg:
                logger.info(f"Provider {provider_config.provider_key} 不支持 json_object，降级调用...")
                response = await _do_call(use_json=False)

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"{provider_config.provider_key} API Error: {response.status_code} | {error_text}")
            # 针对 401/402 不触发重试/切换，直接抛出业务异常
            if response.status_code in [401, 402]:
                raise ValueError(f"Provider Auth/Balance Error: {response.status_code} | {error_text}")
            response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]

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
        provider_config = type(
            "TempProvider",
            (),
            {
                "provider_key": "siliconflow",
                "base_url": base_url or "https://api.siliconflow.cn/v1",
                "timeout_seconds": 30,
            },
        )()
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

            provider_config = type('TempProvider', (), {
                'provider_key': provider_key,
                'base_url': default_url,
                'timeout_seconds': 10
            })()
            
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
    async def _dispatch_with_fallback(cls, prompt: str, model_config: AIModelConfig, user: Optional[User], db: AsyncSession) -> str:
        """核心路由：带故障转移的提供商分发"""
        # 1. 获取所有可用的供应商列表，按优先级排序
        if time.time() - cls._provider_cache_time > 600 or not cls._provider_cache:
            stmt = select(ProviderConfig).where(ProviderConfig.is_active == True).order_by(ProviderConfig.priority.asc())
            result = await db.execute(stmt)
            cls._provider_cache = result.scalars().all()
            cls._provider_cache_time = time.time()

        # 2. 确定初始供应商链
        providers = list(cls._provider_cache)
        primary_provider = next((p for p in providers if p.provider_key == model_config.provider), None)
        
        if primary_provider:
            providers.remove(primary_provider)
            providers.insert(0, primary_provider)

        last_error = "未知错误"
        for i, provider in enumerate(providers):
            try:
                # 解析 API Key & Custom URL
                api_key, custom_url = await cls._resolve_api_key(provider.provider_key, user, db)
                
                # 如果是后续降级链路，且用户关闭了全局 Fallback，则终止（除非该供应商是用户选定的主供应商）
                is_fallback = i > 0
                if is_fallback and user and not user.fallback_enabled:
                    logger.info(f"用户禁用故障转移，停止切换到供应商 {provider.provider_key}")
                    break

                if not api_key:
                    logger.warning(f"跳过供应商 {provider.provider_key}: 缺少 API Key")
                    continue
                
                current_model_id = (
                    model_config.model_id
                    if provider.provider_key == model_config.provider
                    else await cls.get_default_model_for_provider(provider.provider_key, db)
                )

                logger.info(f"尝试使用供应商 {provider.provider_key} (Model: {current_model_id}) URL: {custom_url or 'default'}")
                return await cls.call_provider(provider, current_model_id, prompt, api_key, custom_url)

            except ValueError as ve:
                last_error = str(ve)
                # 授权错误通常不可重试，但如果有备用供应商，可以尝试备用
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
        """主方法：生成个股深度诊断"""
        user = None
        if user_id and db:
            user_stmt = select(User).where(User.id == user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

        prompt = build_stock_analysis_prompt(
            ticker=ticker,
            market_data=market_data,
            portfolio_data=portfolio_data,
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
                    if not user.fallback_enabled:
                        return f"**Error**: AI 服务暂时不可用。错误: {e}"
                    fallback_model = await cls.get_model_config("gemini-1.5-flash", db)
                    return await cls._dispatch_with_fallback(prompt, fallback_model, user, db)

        model_config = await cls.get_model_config(model, db)
        return await cls._dispatch_with_fallback(prompt, model_config, user, db)

    @classmethod
    async def generate_portfolio_analysis(cls, portfolio_items: list, market_news: str = None, macro_context: str = None, 
                                          model: str = "gemini-1.5-flash", db: AsyncSession = None, user_id: str = None) -> str:
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
                    if not user.fallback_enabled:
                        return json.dumps({"error": f"AI 服务暂时不可用: {e}"})
                    fallback_model = await cls.get_model_config("gemini-1.5-flash", db)
                    return await cls._dispatch_with_fallback(prompt, fallback_model, user, db)

        model_config = await cls.get_model_config(model, db)
        return await cls._dispatch_with_fallback(prompt, model_config, user, db)


ai_service = AIService
