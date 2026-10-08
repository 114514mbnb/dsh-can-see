#!/usr/bin/env python3
"""
dsh-can-see — give text-only models in DSH the ability to see images.

给部署在 DSH 里的纯文本模型（GPT / Claude 等）加上看图能力。

核心思路：模型看不到图片，就把图片交给一个「看得见」的视觉模型，
拿回文字描述，再交回主模型继续推理。

用法：
    python vision_provider.py <图片路径> "<你的问题>"
    from vision_provider import describe_image
    describe_image("photo.jpg", "这张图里有什么？")
"""

import os
import sys
import base64
import json
from typing import List, Dict, Optional, Union, Any
from pathlib import Path
import mimetypes

try:
    import requests
except ImportError:
    print("Missing dependency 'requests'. Install it with: pip install requests")
    raise

try:
    from PIL import Image
except ImportError:
    print("Missing dependency 'Pillow'. Install it with: pip install pillow")
    raise


def _ensure_utf8_output() -> None:
    """
    Switch stdout/stderr to UTF-8.

    Windows consoles default to a legacy code page (cp1252, cp936, ...) that
    cannot encode characters like the check mark or many CJK glyphs. Plain
    print() then raises UnicodeEncodeError and aborts the program mid-output.

    Reconfiguring to UTF-8 makes the worst case render as mojibake instead of
    crashing. Available on Python 3.7+; silently ignored when a stream does not
    support it (redirected or wrapped streams).
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# DSH 凭据自动发现
# ---------------------------------------------------------------------------

# DSH 凭据库的常见位置（按优先级）
_DSH_CREDENTIAL_PATHS = [
    Path(os.path.expanduser("~")) / ".dsh" / ".credentials.yaml",
    Path(os.path.expanduser("~")) / ".dsh" / "credentials.yaml",
]

_dsh_creds_cache = None


def redact(text: str) -> str:
    """
    从错误信息/日志中抹掉疑似密钥的片段。

    典型需要处理的场景：
      - Google API 把密钥放在 URL 上: ?key=AQ.Ab8R...
      - Authorization: Bearer sk-xxxx
    """
    if not text:
        return text
    import re
    # ?key=xxx  /  &key=xxx
    text = re.sub(r"(?i)([?&]key=)[^&\s'\"]+", r"\1***REDACTED***", text)
    # Bearer xxx / api-key: xxx / sk-xxx
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+", r"\1***REDACTED***", text)
    text = re.sub(r"\bsk-[A-Za-z0-9._\-]{12,}", "sk-***REDACTED***", text)
    text = re.sub(r"\bAQ\.[A-Za-z0-9._\-]{12,}", "AQ.***REDACTED***", text)
    return text


def load_dsh_credentials(force_reload: bool = False) -> Dict[str, str]:
    """
    从 DSH 的凭据库 (~/.dsh/.credentials.yaml) 读取 refs 中的 API Key。

    这让 skill 能直接复用用户在 DSH 里已配置好的密钥，
    无需额外设置环境变量。

    Returns:
        {环境变量名: 密钥} 的字典；失败时返回空字典
    """
    global _dsh_creds_cache
    if _dsh_creds_cache is not None and not force_reload:
        return _dsh_creds_cache

    result: Dict[str, str] = {}
    for path in _DSH_CREDENTIAL_PATHS:
        try:
            if not path.is_file():
                continue
            import yaml
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            refs = data.get("refs") or {}
            if isinstance(refs, dict):
                for k, v in refs.items():
                    if isinstance(v, str) and v.strip():
                        result[k] = v.strip()
            if result:
                break
        except Exception:
            # 读取失败不应中断主流程，静默回退到环境变量
            continue

    _dsh_creds_cache = result
    return result


class VisionProvider:
    """视觉模型提供商统一接口（dsh-can-see）"""
    
    SUPPORTED_PROVIDERS = ["deepseek", "openai", "anthropic", "google", "openrouter", "custom"]
    
    DEFAULT_MODELS = {
        # DeepSeek 的视觉模型，DeepSeek 官方 API 兼容 OpenAI 格式
        "deepseek": "deepseek-v4-flash-vision-exp",
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "google": "gemini-2.0-flash-exp",
        "openrouter": "openai/gpt-4o",
    }
    
    # 自定义提供商注册表
    _custom_providers = {}
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        message_format: str = "openai",  # 新增: 消息格式类型
        headers: Optional[Dict[str, str]] = None,  # 新增: 自定义请求头
        **kwargs
    ):
        """
        初始化视觉提供商
        
        Args:
            provider: 提供商名称 (openai, anthropic, google, openrouter, custom 或自定义注册的提供商名)
            api_key: API 密钥
            model: 模型名称，默认使用各提供商的默认视觉模型
            base_url: 自定义 API 端点
            message_format: 消息格式 (openai, anthropic, google, custom)
            headers: 自定义 HTTP 请求头
            **kwargs: 其他配置参数
        """
        # 检查是否为已注册的自定义提供商
        if provider in self._custom_providers:
            custom_config = self._custom_providers[provider]
            self.provider = provider
            self.model = model or custom_config.get("default_model")
            self.base_url = base_url or custom_config.get("base_url")
            self.message_format = message_format or custom_config.get("message_format", "openai")
            self.custom_headers = headers or custom_config.get("headers", {})
            self.api_key = api_key or custom_config.get("api_key") or self._get_api_key_for_custom(provider)
        elif provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"不支持的提供商: {provider}. "
                f"支持的提供商: {self.SUPPORTED_PROVIDERS + list(self._custom_providers.keys())}. "
                f"使用 VisionProvider.register_custom_provider() 注册自定义提供商"
            )
        else:
            self.provider = provider
            self.model = model or self.DEFAULT_MODELS.get(provider)
            self.base_url = base_url
            self.message_format = message_format if provider == "custom" else provider
            self.custom_headers = headers or {}
            self.api_key = api_key or self._get_api_key()
        
        self.config = kwargs
        
        # 只有内置云端提供商强制要求 API Key。
        # 自定义提供商（尤其是 Ollama / LocalAI 等本地服务）允许无 Key。
        if not self.api_key and provider not in self._custom_providers and provider != "custom":
            raise ValueError(f"未提供 API key. 请设置环境变量或传入 api_key 参数")
    
    @classmethod
    def register_custom_provider(
        cls,
        name: str,
        base_url: str,
        default_model: str,
        message_format: str = "openai",
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        注册自定义视觉模型提供商
        
        Args:
            name: 提供商名称（唯一标识）
            base_url: API 基础 URL
            default_model: 默认模型名称
            message_format: 消息格式 (openai, anthropic, google, custom)
            api_key: API 密钥（可选，也可通过环境变量设置）
            headers: 自定义 HTTP 请求头
            **kwargs: 其他配置参数
        
        Example:
            VisionProvider.register_custom_provider(
                name="ollama",
                base_url="http://localhost:11434/v1",
                default_model="llava:latest",
                message_format="openai"
            )
        """
        if name in cls.SUPPORTED_PROVIDERS:
            raise ValueError(f"'{name}' 是保留的提供商名称，请使用其他名称")
        
        cls._custom_providers[name] = {
            "base_url": base_url,
            "default_model": default_model,
            "message_format": message_format,
            "api_key": api_key,
            "headers": headers or {},
            **kwargs
        }
        print(f"[ok] registered custom provider: {name}")
    
    @classmethod
    def list_custom_providers(cls) -> List[str]:
        """列出所有已注册的自定义提供商"""
        return list(cls._custom_providers.keys())
    
    @classmethod
    def unregister_custom_provider(cls, name: str):
        """注销自定义提供商"""
        if name in cls._custom_providers:
            del cls._custom_providers[name]
            print(f"[ok] unregistered custom provider: {name}")
        else:
            print(f"[warn] no such custom provider: {name}")
    
    def _get_api_key_for_custom(self, provider_name: str) -> Optional[str]:
        """为自定义提供商获取 API key"""
        # 尝试 {PROVIDER_NAME}_API_KEY 格式
        env_var = f"{provider_name.upper()}_API_KEY"
        key = os.getenv(env_var)
        if key:
            return key
        # 回退到 DSH 凭据库
        return load_dsh_credentials().get(env_var)

    # 每个提供商可接受的多个环境变量名（按优先级）
    ENV_ALIASES = {
        "deepseek": ["DEEPSEEK_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "custom": ["CUSTOM_API_KEY"],
    }

    def _get_api_key(self) -> Optional[str]:
        """按优先级查找 API key: 环境变量 -> DSH 凭据库 -> ~/.dsh 其他位置"""
        for name in self.ENV_ALIASES.get(self.provider, []):
            key = os.getenv(name)
            if key:
                return key

        creds = load_dsh_credentials()
        for name in self.ENV_ALIASES.get(self.provider, []):
            if creds.get(name):
                return creds[name]

        return None

    @classmethod
    def detect_available_provider(cls) -> Optional[tuple]:
        """
        探测当前环境可用的提供商（按优先级）。
        返回 (provider_name, api_key) 或 None。

        优先级：deepseek > google(Gemini) > openai > anthropic > openrouter
        DeepSeek 排最前，因为它在 OpenAI 兼容接口上提供视觉模型，
        且通常与 DSH 的默认凭据一致。
        """
        order = ["deepseek", "google", "openai", "anthropic", "openrouter"]
        creds = load_dsh_credentials()

        for prov in order:
            for name in cls.ENV_ALIASES.get(prov, []):
                key = os.getenv(name) or creds.get(name)
                if key:
                    return prov, key
        return None
    
    def _get_base_url(self) -> str:
        """获取 API 基础 URL"""
        if self.base_url:
            return self.base_url
        
        url_map = {
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "google": "https://generativelanguage.googleapis.com/v1beta",
            "openrouter": "https://openrouter.ai/api/v1",
        }
        return url_map.get(self.provider, "")
    
    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """
        将图像编码为 base64
        
        Returns:
            (base64_string, mime_type)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        # 检查图像大小
        file_size = image_path.stat().st_size
        max_size = 20 * 1024 * 1024  # 20MB
        if file_size > max_size:
            raise ValueError(f"图像文件过大: {file_size / 1024 / 1024:.2f}MB (最大 20MB)")
        
        # 获取 MIME 类型
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"  # 默认
        
        # 读取并编码
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        
        return encoded, mime_type
    
    def _format_openai_messages(
        self, 
        prompt: str, 
        images: List[Dict[str, str]]
    ) -> List[Dict]:
        """格式化为 OpenAI 消息格式"""
        content = [{"type": "text", "text": prompt}]
        
        for img in images:
            if img["type"] == "base64":
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{img['mime_type']};base64,{img['data']}"
                    }
                })
            else:  # url
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img["url"]}
                })
        
        return [{"role": "user", "content": content}]
    
    def _format_anthropic_messages(
        self,
        prompt: str,
        images: List[Dict[str, str]]
    ) -> List[Dict]:
        """格式化为 Anthropic 消息格式"""
        content = []
        
        for img in images:
            if img["type"] == "base64":
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img["mime_type"],
                        "data": img["data"]
                    }
                })
            else:  # url - Anthropic 需要先下载
                response = requests.get(img["url"])
                encoded = base64.b64encode(response.content).decode("utf-8")
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": encoded
                    }
                })
        
        content.append({"type": "text", "text": prompt})
        
        return [{"role": "user", "content": content}]
    
    def _call_openai_compatible(
        self,
        messages: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """调用 OpenAI 兼容的 API"""
        url = f"{self._get_base_url()}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # 添加认证头
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 添加自定义请求头
        headers.update(self.custom_headers)
        
        # OpenRouter 需要额外的 header
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/your-repo"
            headers["X-Title"] = "DSH Vision Provider"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "success": True,
            "content": data["choices"][0]["message"]["content"],
            "model": data["model"],
            "usage": data.get("usage", {}),
            "metadata": {
                "provider": self.provider,
                "raw_response": data
            }
        }
    
    def _call_anthropic(
        self,
        messages: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """调用 Anthropic API"""
        url = f"{self._get_base_url()}/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "success": True,
            "content": data["content"][0]["text"],
            "model": data["model"],
            "usage": data.get("usage", {}),
            "metadata": {
                "provider": self.provider,
                "raw_response": data
            }
        }
    
    def _call_google(
        self,
        prompt: str,
        images: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """调用 Google Gemini API"""
        url = f"{self._get_base_url()}/models/{self.model}:generateContent?key={self.api_key}"
        
        headers = {"Content-Type": "application/json"}
        
        # 构建 parts
        parts = [{"text": prompt}]
        for img in images:
            if img["type"] == "base64":
                parts.append({
                    "inline_data": {
                        "mime_type": img["mime_type"],
                        "data": img["data"]
                    }
                })
            else:  # url - 下载后编码
                response = requests.get(img["url"])
                encoded = base64.b64encode(response.content).decode("utf-8")
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": encoded
                    }
                })
        
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 1000),
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "success": True,
            "content": data["candidates"][0]["content"]["parts"][0]["text"],
            "model": self.model,
            "usage": data.get("usageMetadata", {}),
            "metadata": {
                "provider": self.provider,
                "raw_response": data
            }
        }
    
    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        分析单张图像
        
        Args:
            image_path: 图像文件路径
            prompt: 提示词
            **kwargs: 其他参数 (max_tokens, temperature 等)
        
        Returns:
            结果字典
        """
        try:
            encoded, mime_type = self._encode_image(image_path)
            images = [{"type": "base64", "data": encoded, "mime_type": mime_type}]
            
            return self._process_request(prompt, images, **kwargs)
        
        except Exception as e:
            return {
                "success": False,
                "error": redact(str(e)),
                "provider": self.provider
            }
    
    def analyze_images(
        self,
        image_paths: List[str],
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        分析多张图像
        
        Args:
            image_paths: 图像文件路径列表
            prompt: 提示词
            **kwargs: 其他参数
        
        Returns:
            结果字典
        """
        try:
            images = []
            for path in image_paths:
                encoded, mime_type = self._encode_image(path)
                images.append({"type": "base64", "data": encoded, "mime_type": mime_type})
            
            return self._process_request(prompt, images, **kwargs)
        
        except Exception as e:
            return {
                "success": False,
                "error": redact(str(e)),
                "provider": self.provider
            }
    
    def analyze_image_url(
        self,
        image_url: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        从 URL 分析图像
        
        Args:
            image_url: 图像 URL
            prompt: 提示词
            **kwargs: 其他参数
        
        Returns:
            结果字典
        """
        try:
            images = [{"type": "url", "url": image_url}]
            return self._process_request(prompt, images, **kwargs)
        
        except Exception as e:
            return {
                "success": False,
                "error": redact(str(e)),
                "provider": self.provider
            }
    
    def _process_request(
        self,
        prompt: str,
        images: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """处理请求并调用相应的 API"""
        # 确定消息格式
        format_type = self.message_format if hasattr(self, 'message_format') else self.provider
        
        # 根据消息格式选择调用方法
        if format_type in ["openai", "openrouter", "deepseek", "custom"]:
            messages = self._format_openai_messages(prompt, images)
            result = self._call_openai_compatible(messages, **kwargs)
        
        elif format_type == "anthropic":
            messages = self._format_anthropic_messages(prompt, images)
            result = self._call_anthropic(messages, **kwargs)
        
        elif format_type == "google":
            result = self._call_google(prompt, images, **kwargs)
        
        else:
            # 对于自定义提供商，默认使用 OpenAI 兼容格式
            if self.provider in self._custom_providers or self.provider == "custom":
                messages = self._format_openai_messages(prompt, images)
                result = self._call_openai_compatible(messages, **kwargs)
            else:
                raise ValueError(f"未实现的提供商或消息格式: {self.provider} / {format_type}")
        
        # 添加图像数量到元数据
        if "metadata" in result:
            result["metadata"]["image_count"] = len(images)
        
        return result
    
    def batch_analyze(
        self,
        image_dir: str,
        prompt: str,
        pattern: str = "*",
        max_concurrent: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量分析文件夹中的图像
        
        Args:
            image_dir: 图像文件夹路径
            prompt: 提示词
            pattern: 文件匹配模式 (如 "*.jpg")
            max_concurrent: 最大并发数
            **kwargs: 其他参数
        
        Returns:
            结果列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        image_dir = Path(image_dir)
        if not image_dir.exists():
            raise ValueError(f"目录不存在: {image_dir}")
        
        # 查找图像文件
        # 注意: 使用 set 去重，因为 Windows/macOS 文件系统大小写不敏感，
        # "*.jpg" 与 "*.JPG" 会命中同一批文件
        exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        seen = {}
        for f in image_dir.glob(pattern):
            if f.is_file() and f.suffix.lower() in exts:
                # 用 resolve() 归一化路径，避免同一文件被多次收集
                key = str(f.resolve()).lower()
                if key not in seen:
                    seen[key] = f

        image_files = sorted(seen.values(), key=lambda p: str(p).lower())

        if not image_files:
            return []
        
        results = []
        
        def process_image(img_path):
            result = self.analyze_image(str(img_path), prompt, **kwargs)
            result["image_path"] = str(img_path)
            return result
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {executor.submit(process_image, img): img for img in image_files}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    img = futures[future]
                    results.append({
                        "success": False,
                        "error": redact(str(e)),
                        "image_path": str(img)
                    })
        
        return results
    
    @classmethod
    def from_config(cls, config_path: str) -> "VisionProvider":
        """从配置文件创建实例"""
        try:
            import yaml
        except ImportError:
            print("Missing dependency 'PyYAML'. Install it with: pip install pyyaml")
            raise
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # 处理环境变量替换
        if "api_key" in config and config["api_key"].startswith("${"):
            env_var = config["api_key"][2:-1]
            config["api_key"] = os.getenv(env_var)
        
        return cls(**config)


def describe_image(
    image_path: str,
    prompt: str = "请详细描述这张图片的内容。",
    provider: str = "auto",
    model: Optional[str] = None,
    **kwargs
) -> str:
    """
    一行调用：给一张图片和问题，返回视觉模型给出的文字回答。

    这是给 agent 用的极简入口——自动探测可用凭据，无需关心提供商细节。

    Args:
        image_path: 图片路径（本地文件）
        prompt:     想问的问题
        provider:   提供商，默认 "auto" 自动探测
        model:      模型名，默认用该提供商的视觉模型
        **kwargs:   透传给底层（max_tokens / temperature 等）

    Returns:
        回答文本；失败时返回以 "错误: " 开头的字符串
    """
    name, key = (provider, None)
    if provider == "auto":
        det = VisionProvider.detect_available_provider()
        if not det:
            return ("错误: 未找到可用的视觉模型凭据。请在环境变量或 "
                    "~/.dsh/.credentials.yaml 中配置 DEEPSEEK_API_KEY / "
                    "GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY / "
                    "OPENROUTER_API_KEY 之一。")
        name, key = det

    vp = VisionProvider(provider=name, api_key=key, model=model)
    result = vp.analyze_image(image_path, prompt, **kwargs)
    if result.get("success"):
        return result["content"]
    return f"错误: {result.get('error')}"


def main():
    """命令行接口"""
    import argparse

    # Windows 控制台默认代码页无法编码中文/符号，先切到 UTF-8 再输出
    _ensure_utf8_output()

    # 允许 CLI 使用「内置提供商 + 已注册的自定义提供商」
    known = VisionProvider.SUPPORTED_PROVIDERS + VisionProvider.list_custom_providers()

    parser = argparse.ArgumentParser(
        description="dsh-can-see - vision for text-only models in DSH",
        epilog="提示: 使用 --register 可先注册一个自定义提供商 (如 Ollama)。",
    )
    parser.add_argument("image", nargs="?", help="图像文件路径或 URL")
    parser.add_argument("prompt", nargs="?", help="提示词")
    parser.add_argument("--provider", default="auto",
                        help=f"提供商名称，默认 auto（自动探测可用通道）。"
                             f"可选: auto, {', '.join(known)}")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--base-url", help="自定义 API 端点")
    parser.add_argument("--message-format", default=None,
                        help="自定义提供商的消息格式: openai / anthropic / google")
    parser.add_argument("--header", action="append", default=[], metavar="K:V",
                        help="自定义请求头，可重复。例如 --header 'api-key:xxx'")
    parser.add_argument("--max-tokens", type=int, default=1000)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--output", help="输出文件路径 (JSON)")

    # 自定义提供商管理
    parser.add_argument("--register", metavar="NAME",
                        help="注册自定义提供商（需配合 --base-url 与 --model）")
    parser.add_argument("--list-providers", action="store_true",
                        help="列出所有可用提供商后退出")

    args = parser.parse_args()

    if args.list_providers:
        print("内置提供商:")
        for p in VisionProvider.SUPPORTED_PROVIDERS:
            print(f"  - {p}  (默认模型: {VisionProvider.DEFAULT_MODELS.get(p, 'n/a')})")
        custom = VisionProvider.list_custom_providers()
        print("\n自定义提供商:")
        if custom:
            for p in custom:
                print(f"  - {p}")
        else:
            print("  (无)")
        return 0

    # 注册自定义提供商
    if args.register:
        if not args.base_url or not args.model:
            print("错误: --register 需要同时提供 --base-url 和 --model")
            return 2
        headers = {}
        for h in args.header:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()
        VisionProvider.register_custom_provider(
            name=args.register,
            base_url=args.base_url,
            default_model=args.model,
            message_format=args.message_format or "openai",
            api_key=args.api_key,
            headers=headers,
        )
        print(f"提供商 '{args.register}' 已注册（仅本次进程有效）")
        print("如需在其他进程中使用，请在代码里调用 register_custom_provider()，")
        print("或使用 config.yaml 持久化配置。")
        return 0

    if not args.image or not args.prompt:
        parser.error("需要提供 image 和 prompt（或使用 --list-providers / --register）")

    # 组装请求头
    headers = {}
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    # provider=auto 时自动探测可用通道
    provider_name = args.provider
    api_key = args.api_key
    if provider_name == "auto":
        det = VisionProvider.detect_available_provider()
        if not det:
            print("错误: 未找到任何可用的视觉模型凭据。")
            print("请设置以下环境变量之一，或确认 ~/.dsh/.credentials.yaml 中有对应密钥：")
            print("  DEEPSEEK_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY /")
            print("  ANTHROPIC_API_KEY / OPENROUTER_API_KEY")
            return 2
        provider_name, api_key = det
        if not args.output:
            print(f"[auto] 使用提供商: {provider_name}", file=sys.stderr)

    # 创建提供商
    try:
        provider = VisionProvider(
            provider=provider_name,
            api_key=api_key,
            model=args.model,
            base_url=args.base_url,
            message_format=args.message_format,
            headers=headers or None,
        )
    except ValueError as e:
        print(f"配置错误: {e}")
        return 2
    
    # 分析图像
    if args.image.startswith("http://") or args.image.startswith("https://"):
        result = provider.analyze_image_url(
            args.image,
            args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        )
    else:
        result = provider.analyze_image(
            args.image,
            args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        )
    
    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {args.output}")
    else:
        if result["success"]:
            print("\n" + "="*60)
            print(result["content"])
            print("="*60)
            print(f"\n模型: {result['model']}")
            print(f"提供商: {result['metadata'].get('provider', args.provider)}")
            print(f"Token 使用: {result['usage']}")
        else:
            print(f"错误: {result['error']}")

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
