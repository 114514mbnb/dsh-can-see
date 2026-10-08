#!/usr/bin/env python3
"""
dsh-can-see 单元测试

运行方式（在仓库根目录）：
    python -m unittest discover -s tests -v
    python -m pytest tests/ -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 让测试可以 import 到仓库根目录下的 vision_provider 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vision_provider import VisionProvider


class TestVisionProvider(unittest.TestCase):
    """测试 VisionProvider 类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_api_key = "test-api-key"
    
    def test_init_openai(self):
        """测试 OpenAI 初始化"""
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key
        )
        self.assertEqual(provider.provider, "openai")
        self.assertEqual(provider.model, "gpt-4o")
        self.assertEqual(provider.api_key, self.test_api_key)
    
    def test_init_anthropic(self):
        """测试 Anthropic 初始化"""
        provider = VisionProvider(
            provider="anthropic",
            api_key=self.test_api_key
        )
        self.assertEqual(provider.provider, "anthropic")
        self.assertEqual(provider.model, "claude-3-5-sonnet-20241022")
    
    def test_init_google(self):
        """测试 Google 初始化"""
        provider = VisionProvider(
            provider="google",
            api_key=self.test_api_key
        )
        self.assertEqual(provider.provider, "google")
        self.assertEqual(provider.model, "gemini-2.0-flash-exp")
    
    def test_invalid_provider(self):
        """测试无效的提供商"""
        with self.assertRaises(ValueError):
            VisionProvider(
                provider="invalid",
                api_key=self.test_api_key
            )
    
    def test_missing_api_key(self):
        """测试缺少 API key"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                VisionProvider(provider="openai")
    
    def test_get_base_url_openai(self):
        """测试获取 OpenAI base URL"""
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key
        )
        self.assertEqual(
            provider._get_base_url(),
            "https://api.openai.com/v1"
        )
    
    def test_get_base_url_custom(self):
        """测试自定义 base URL"""
        custom_url = "https://custom.api.com/v1"
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key,
            base_url=custom_url
        )
        self.assertEqual(provider._get_base_url(), custom_url)
    
    def test_encode_image_not_found(self):
        """测试编码不存在的图像"""
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key
        )
        with self.assertRaises(FileNotFoundError):
            provider._encode_image("nonexistent.jpg")
    
    @patch('vision_provider.Path.exists')
    @patch('vision_provider.Path.stat')
    @patch('builtins.open', create=True)
    def test_encode_image_too_large(self, mock_open, mock_stat, mock_exists):
        """测试编码过大的图像"""
        mock_exists.return_value = True
        mock_stat.return_value = Mock(st_size=25 * 1024 * 1024)  # 25MB
        
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key
        )
        
        with self.assertRaises(ValueError):
            provider._encode_image("large.jpg")
    
    def test_format_openai_messages(self):
        """测试格式化 OpenAI 消息"""
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key
        )
        
        images = [{
            "type": "base64",
            "data": "base64data",
            "mime_type": "image/jpeg"
        }]
        
        messages = provider._format_openai_messages("test prompt", images)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(len(messages[0]["content"]), 2)
        self.assertEqual(messages[0]["content"][0]["type"], "text")
        self.assertEqual(messages[0]["content"][1]["type"], "image_url")
    
    def test_format_anthropic_messages(self):
        """测试格式化 Anthropic 消息"""
        provider = VisionProvider(
            provider="anthropic",
            api_key=self.test_api_key
        )
        
        images = [{
            "type": "base64",
            "data": "base64data",
            "mime_type": "image/jpeg"
        }]
        
        messages = provider._format_anthropic_messages("test prompt", images)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(len(messages[0]["content"]), 2)
        self.assertEqual(messages[0]["content"][0]["type"], "image")
        self.assertEqual(messages[0]["content"][1]["type"], "text")
    
    @patch('vision_provider.requests.post')
    def test_call_openai_compatible(self, mock_post):
        """测试调用 OpenAI 兼容 API"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "test response"}
            }],
            "model": "gpt-4o",
            "usage": {"total_tokens": 100}
        }
        mock_post.return_value = mock_response
        
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key
        )
        
        messages = [{"role": "user", "content": "test"}]
        result = provider._call_openai_compatible(messages)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "test response")
        self.assertEqual(result["model"], "gpt-4o")
    
    @patch('vision_provider.requests.post')
    def test_call_anthropic(self, mock_post):
        """测试调用 Anthropic API"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [{"text": "test response"}],
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 50, "output_tokens": 50}
        }
        mock_post.return_value = mock_response
        
        provider = VisionProvider(
            provider="anthropic",
            api_key=self.test_api_key
        )
        
        messages = [{"role": "user", "content": "test"}]
        result = provider._call_anthropic(messages)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "test response")
    
    def test_analyze_image_url_format(self):
        """测试 URL 图像分析"""
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key
        )
        
        with patch.object(provider, '_process_request') as mock_process:
            mock_process.return_value = {"success": True, "content": "test"}
            
            result = provider.analyze_image_url(
                "https://example.com/image.jpg",
                "test prompt"
            )
            
            # 验证调用参数
            call_args = mock_process.call_args
            images = call_args[0][1]
            
            self.assertEqual(len(images), 1)
            self.assertEqual(images[0]["type"], "url")
            self.assertEqual(images[0]["url"], "https://example.com/image.jpg")
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_env_api_key(self):
        """测试从环境变量读取 API key"""
        provider = VisionProvider(provider="openai")
        self.assertEqual(provider.api_key, "test-key")
    
    def test_custom_model(self):
        """测试自定义模型"""
        provider = VisionProvider(
            provider="openai",
            api_key=self.test_api_key,
            model="gpt-4-vision-preview"
        )
        self.assertEqual(provider.model, "gpt-4-vision-preview")


class TestBatchProcessing(unittest.TestCase):
    """测试批量处理功能"""
    
    @patch.object(VisionProvider, 'analyze_image')
    def test_batch_analyze(self, mock_analyze):
        """测试批量分析（使用真实临时目录）"""
        import tempfile

        mock_analyze.return_value = {
            "success": True,
            "content": "test result"
        }

        provider = VisionProvider(
            provider="openai",
            api_key="test-key"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 3 个图像文件 + 1 个非图像文件
            for i in range(3):
                Path(tmpdir, f"image{i}.jpg").write_bytes(b"fake")
            Path(tmpdir, "notes.txt").write_text("ignore me")

            results = provider.batch_analyze(
                image_dir=tmpdir,
                prompt="test prompt",
                max_concurrent=2
            )

        # 应只处理 3 个图像，且不重复（含大小写不敏感去重）
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertTrue(result["success"])

    @patch.object(VisionProvider, 'analyze_image')
    def test_batch_analyze_dedup_case_insensitive(self, mock_analyze):
        """测试批量分析对大小写扩展名的去重"""
        import tempfile

        mock_analyze.return_value = {"success": True, "content": "r"}

        provider = VisionProvider(provider="openai", api_key="test-key")

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.jpg").write_bytes(b"fake")
            Path(tmpdir, "b.JPG").write_bytes(b"fake")
            Path(tmpdir, "c.PnG").write_bytes(b"fake")

            results = provider.batch_analyze(
                image_dir=tmpdir,
                prompt="p",
                max_concurrent=2
            )

        self.assertEqual(len(results), 3)

    @patch.object(VisionProvider, 'analyze_image')
    def test_batch_analyze_empty_dir(self, mock_analyze):
        """测试空目录返回空列表"""
        import tempfile

        provider = VisionProvider(provider="openai", api_key="test-key")

        with tempfile.TemporaryDirectory() as tmpdir:
            results = provider.batch_analyze(image_dir=tmpdir, prompt="p")

        self.assertEqual(results, [])
        mock_analyze.assert_not_called()

    def test_batch_analyze_missing_dir(self):
        """测试不存在的目录抛出异常"""
        provider = VisionProvider(provider="openai", api_key="test-key")
        with self.assertRaises(ValueError):
            provider.batch_analyze(image_dir="./definitely_not_here", prompt="p")


class TestConfigLoading(unittest.TestCase):
    """测试配置加载"""
    
    @patch('builtins.open', create=True)
    @patch('yaml.safe_load')
    def test_from_config(self, mock_yaml_load, mock_open):
        """测试从配置文件加载"""
        mock_yaml_load.return_value = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "test-key",
            "max_tokens": 500
        }
        
        provider = VisionProvider.from_config("config.yaml")
        
        self.assertEqual(provider.provider, "openai")
        self.assertEqual(provider.model, "gpt-4o")
        self.assertEqual(provider.api_key, "test-key")
    
    @patch('builtins.open', create=True)
    @patch('yaml.safe_load')
    @patch.dict(os.environ, {"TEST_API_KEY": "env-key"})
    def test_from_config_env_var(self, mock_yaml_load, mock_open):
        """测试配置文件中的环境变量替换"""
        mock_yaml_load.return_value = {
            "provider": "openai",
            "api_key": "${TEST_API_KEY}"
        }
        
        provider = VisionProvider.from_config("config.yaml")
        
        self.assertEqual(provider.api_key, "env-key")


class TestCustomProviders(unittest.TestCase):
    """测试自定义提供商功能"""

    def tearDown(self):
        """每个测试后清理已注册的自定义提供商"""
        for name in list(VisionProvider.list_custom_providers()):
            VisionProvider.unregister_custom_provider(name)

    def test_register_and_use(self):
        """测试注册并使用自定义提供商"""
        VisionProvider.register_custom_provider(
            name="test_local",
            base_url="http://localhost:11434/v1",
            default_model="llava:latest",
            message_format="openai",
            api_key="local-key"
        )

        self.assertIn("test_local", VisionProvider.list_custom_providers())

        provider = VisionProvider(provider="test_local")
        self.assertEqual(provider.provider, "test_local")
        self.assertEqual(provider.model, "llava:latest")
        self.assertEqual(provider.base_url, "http://localhost:11434/v1")
        self.assertEqual(provider.message_format, "openai")
        self.assertEqual(provider.api_key, "local-key")

    def test_register_rejects_reserved_name(self):
        """测试不能使用保留名称注册"""
        with self.assertRaises(ValueError):
            VisionProvider.register_custom_provider(
                name="openai",
                base_url="http://x",
                default_model="m"
            )

    def test_unregister(self):
        """测试注销自定义提供商"""
        VisionProvider.register_custom_provider(
            name="temp_prov",
            base_url="http://localhost:1234/v1",
            default_model="m",
        )
        self.assertIn("temp_prov", VisionProvider.list_custom_providers())

        VisionProvider.unregister_custom_provider("temp_prov")
        self.assertNotIn("temp_prov", VisionProvider.list_custom_providers())

        # 注销后不能再使用
        with self.assertRaises(ValueError):
            VisionProvider(provider="temp_prov")

    def test_override_model(self):
        """测试创建实例时覆盖默认模型"""
        VisionProvider.register_custom_provider(
            name="multi",
            base_url="http://localhost:11434/v1",
            default_model="llava:7b",
            api_key="k"
        )

        p1 = VisionProvider(provider="multi")
        p2 = VisionProvider(provider="multi", model="llava:13b")

        self.assertEqual(p1.model, "llava:7b")
        self.assertEqual(p2.model, "llava:13b")

    @patch.dict(os.environ, {"MYPROV_API_KEY": "from-env"})
    def test_api_key_from_env(self):
        """测试自定义提供商的 API Key 从环境变量读取"""
        VisionProvider.register_custom_provider(
            name="myprov",
            base_url="http://x/v1",
            default_model="m",
        )

        provider = VisionProvider(provider="myprov")
        self.assertEqual(provider.api_key, "from-env")

    def test_custom_headers_stored(self):
        """测试自定义请求头被保存"""
        VisionProvider.register_custom_provider(
            name="withheaders",
            base_url="http://x/v1",
            default_model="m",
            api_key="k",
            headers={"api-key": "azure-style"}
        )

        provider = VisionProvider(provider="withheaders")
        self.assertEqual(provider.custom_headers.get("api-key"), "azure-style")

    @patch('vision_provider.requests.post')
    def test_custom_provider_call_uses_base_url(self, mock_post):
        """测试自定义提供商调用时使用正确的 URL 和请求头"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "hi"}}],
            "model": "m",
            "usage": {}
        }
        mock_post.return_value = mock_response

        VisionProvider.register_custom_provider(
            name="ollama",
            base_url="http://localhost:11434/v1",
            default_model="llava:latest",
            message_format="openai",
            api_key="k"
        )

        provider = VisionProvider(provider="ollama")
        result = provider._process_request(
            "describe",
            [{"type": "base64", "data": "AAA", "mime_type": "image/jpeg"}]
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["content"], "hi")

        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "http://localhost:11434/v1/chat/completions")

    @patch('vision_provider.requests.post')
    def test_custom_provider_without_api_key(self, mock_post):
        """测试无需 API Key 的本地服务（如 Ollama）"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "model": "m",
            "usage": {}
        }
        mock_post.return_value = mock_response

        VisionProvider.register_custom_provider(
            name="localkeyless",
            base_url="http://localhost:11434/v1",
            default_model="llava",
            message_format="openai"
        )

        provider = VisionProvider(provider="localkeyless")
        result = provider._process_request("hi", [])

        self.assertTrue(result["success"])
        # 无 api_key 时不应发送 Authorization 头
        headers = mock_post.call_args[1]["headers"]
        self.assertNotIn("Authorization", headers)


class TestDeepSeekProvider(unittest.TestCase):
    """测试 DeepSeek 视觉通道（DSH 场景下的默认通道）"""

    def test_deepseek_is_supported(self):
        self.assertIn("deepseek", VisionProvider.SUPPORTED_PROVIDERS)

    def test_deepseek_default_model(self):
        self.assertEqual(
            VisionProvider.DEFAULT_MODELS["deepseek"],
            "deepseek-v4-flash-vision-exp",
        )

    def test_deepseek_base_url(self):
        p = VisionProvider(provider="deepseek", api_key="k")
        self.assertEqual(p._get_base_url(), "https://api.deepseek.com/v1")

    def test_deepseek_uses_openai_message_format(self):
        p = VisionProvider(provider="deepseek", api_key="k")
        msgs = p._format_openai_messages(
            "hi", [{"type": "base64", "data": "AAA", "mime_type": "image/png"}]
        )
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[0]["content"][1]["type"], "image_url")

    def test_deepseek_env_alias(self):
        self.assertIn("DEEPSEEK_API_KEY", VisionProvider.ENV_ALIASES["deepseek"])

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "ds-key"})
    def test_deepseek_key_from_env(self):
        p = VisionProvider(provider="deepseek")
        self.assertEqual(p.api_key, "ds-key")


class TestRedact(unittest.TestCase):
    """测试密钥脱敏（防止错误信息泄露密钥）"""

    def test_redact_url_key(self):
        from vision_provider import redact
        # 完全虚构的示例密钥，仅用于验证脱敏逻辑
        fake = "AQ.FAKEKEYFORTESTONLY000000000000000000000000000000"
        s = ("GET https://generativelanguage.googleapis.com/v1beta/"
             f"models/x:generateContent?key={fake} failed")
        out = redact(s)
        self.assertNotIn("AQ.FAKEKEY", out)
        self.assertNotIn(fake, out)
        self.assertIn("REDACTED", out)

    def test_redact_bearer(self):
        from vision_provider import redact
        out = redact("Authorization: Bearer sk-abc123def456ghi")
        self.assertNotIn("abc123def456", out)

    def test_redact_sk_token(self):
        from vision_provider import redact
        # 完全虚构的示例密钥，仅用于验证脱敏逻辑
        fake = "sk-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd"
        out = redact(f"key is {fake} ok")
        self.assertNotIn("0123456789abcdef", out)
        self.assertIn("REDACTED", out)

    def test_redact_handles_empty(self):
        from vision_provider import redact
        self.assertEqual(redact(""), "")
        self.assertIsNone(redact(None))


class TestCredentialDiscovery(unittest.TestCase):
    """测试 DSH 凭据自动发现"""

    def test_load_from_custom_path(self):
        import tempfile
        import vision_provider as vp

        with tempfile.TemporaryDirectory() as d:
            cred_path = Path(d) / ".credentials.yaml"
            cred_path.write_text(
                "version: 1\nrefs:\n  DEEPSEEK_API_KEY: test-ds-key\n"
                "  GEMINI_API_KEY: test-gem-key\n",
                encoding="utf-8",
            )
            saved = vp._DSH_CREDENTIAL_PATHS
            saved_cache = vp._dsh_creds_cache
            try:
                vp._DSH_CREDENTIAL_PATHS = [cred_path]
                vp._dsh_creds_cache = None
                creds = vp.load_dsh_credentials()
                self.assertEqual(creds.get("DEEPSEEK_API_KEY"), "test-ds-key")
                self.assertEqual(creds.get("GEMINI_API_KEY"), "test-gem-key")
            finally:
                vp._DSH_CREDENTIAL_PATHS = saved
                vp._dsh_creds_cache = saved_cache

    def test_missing_file_returns_empty(self):
        import vision_provider as vp
        saved = vp._DSH_CREDENTIAL_PATHS
        saved_cache = vp._dsh_creds_cache
        try:
            vp._DSH_CREDENTIAL_PATHS = [Path("./no_such_cred_file.yaml")]
            vp._dsh_creds_cache = None
            self.assertEqual(vp.load_dsh_credentials(), {})
        finally:
            vp._DSH_CREDENTIAL_PATHS = saved
            vp._dsh_creds_cache = saved_cache

    def test_detect_prefers_deepseek(self):
        import vision_provider as vp
        with patch.object(vp, "load_dsh_credentials",
                          return_value={"DEEPSEEK_API_KEY": "d",
                                        "OPENAI_API_KEY": "o"}):
            det = VisionProvider.detect_available_provider()
            self.assertEqual(det[0], "deepseek")

    def test_detect_falls_back_when_no_deepseek(self):
        import vision_provider as vp
        with patch.object(vp, "load_dsh_credentials",
                          return_value={"OPENAI_API_KEY": "o"}):
            det = VisionProvider.detect_available_provider()
            self.assertEqual(det[0], "openai")

    def test_detect_returns_none_when_empty(self):
        import vision_provider as vp
        with patch.object(vp, "load_dsh_credentials", return_value={}):
            with patch.dict(os.environ, {}, clear=True):
                self.assertIsNone(VisionProvider.detect_available_provider())


class TestDescribeImage(unittest.TestCase):
    """测试一行式 describe_image 入口"""

    def test_returns_error_string_when_no_credentials(self):
        import vision_provider as vp
        with patch.object(VisionProvider, "detect_available_provider",
                          return_value=None):
            out = vp.describe_image("whatever.png", "描述")
            self.assertTrue(out.startswith("错误:"))
            self.assertIn("凭据", out)

    def test_returns_content_on_success(self):
        import vision_provider as vp
        with patch.object(VisionProvider, "detect_available_provider",
                          return_value=("deepseek", "k")):
            with patch.object(VisionProvider, "analyze_image",
                              return_value={"success": True,
                                            "content": "一只猫"}):
                out = vp.describe_image("cat.png", "这是什么")
                self.assertEqual(out, "一只猫")

    def test_returns_error_on_failure(self):
        import vision_provider as vp
        with patch.object(VisionProvider, "detect_available_provider",
                          return_value=("deepseek", "k")):
            with patch.object(VisionProvider, "analyze_image",
                              return_value={"success": False,
                                            "error": "boom"}):
                out = vp.describe_image("x.png", "描述")
                self.assertEqual(out, "错误: boom")


class TestConsoleEncoding(unittest.TestCase):
    """
    确保在非 UTF-8 控制台下不会因 print 崩溃。

    背景：Windows 默认控制台代码页（cp1252 / cp936）无法编码 ✓ 或部分中文，
    直接 print 会抛 UnicodeEncodeError 并中断程序。CI 在 windows-latest 上
    曾因此失败，这里把该场景固化成回归测试。
    """

    def _cp1252_stream(self):
        import io
        raw = io.BytesIO()
        # errors="strict" 才能复现真实控制台的行为
        return io.TextIOWrapper(raw, encoding="cp1252", errors="strict")

    def test_library_prints_survive_non_utf8_console(self):
        """注册/注销时的提示输出必须能在 cp1252 下完成"""
        import contextlib

        stream = self._cp1252_stream()
        try:
            with contextlib.redirect_stdout(stream):
                VisionProvider.register_custom_provider(
                    name="enc_test",
                    base_url="http://localhost:1234/v1",
                    default_model="m",
                )
                self.assertIn("enc_test", VisionProvider.list_custom_providers())
                VisionProvider.unregister_custom_provider("enc_test")
                # 警告分支也要覆盖
                VisionProvider.unregister_custom_provider("does_not_exist")
            stream.flush()
        finally:
            try:
                stream.detach()
            except Exception:
                pass

    def test_ensure_utf8_output_is_safe_on_odd_streams(self):
        """_ensure_utf8_output 遇到不可 reconfigure 的对象必须静默跳过"""
        import io
        import contextlib
        from vision_provider import _ensure_utf8_output

        class NoReconfigure:
            encoding = "cp1252"
            def write(self, *_a, **_k): pass
            def flush(self): pass

        with contextlib.redirect_stdout(NoReconfigure()):
            with contextlib.redirect_stderr(NoReconfigure()):
                # 不应抛异常
                _ensure_utf8_output()

    def test_ensure_utf8_output_upgrades_piped_stream(self):
        """管道/重定向场景下应能把编码切到 UTF-8"""
        import io
        import contextlib
        from vision_provider import _ensure_utf8_output

        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
        try:
            with contextlib.redirect_stdout(stream):
                _ensure_utf8_output()
                # 切换后应能正常输出中文
                print("中文输出")
            stream.flush()
            self.assertIn("中文".encode("utf-8"), raw.getvalue())
        finally:
            try:
                stream.detach()
            except Exception:
                pass

    def test_source_has_no_non_ascii_in_library_prints(self):
        """
        库内部的状态提示必须是纯 ASCII。

        这些 print 可能在用户代码里被调用，无法依赖 CLI 的 UTF-8 重配置，
        所以必须自身编码安全。
        """
        import re
        from pathlib import Path as _P

        src = (_P(__file__).resolve().parent.parent / "vision_provider.py").read_text(
            encoding="utf-8"
        )
        # 找出库实现部分（main() 之前）的 print 语句
        lib_part = src.split("def main(", 1)[0]
        offenders = []
        for line in lib_part.splitlines():
            stripped = line.strip()
            if stripped.startswith("print("):
                if any(ord(ch) > 127 for ch in stripped):
                    offenders.append(stripped)
        self.assertEqual(
            offenders, [],
            f"库内 print 含非 ASCII 字符，会在非 UTF-8 控制台下崩溃: {offenders}",
        )


def run_tests():
    """运行所有测试"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
