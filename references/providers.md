# 提供商指南

## 内置提供商

| 提供商 | 环境变量 | 默认模型 | base URL |
|--------|---------|---------|----------|
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-v4-flash-vision-exp` | `https://api.deepseek.com/v1` |
| `google` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `gemini-2.0-flash-exp` | `https://generativelanguage.googleapis.com/v1beta` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` | `https://api.openai.com/v1` |
| `anthropic` | `ANTHROPIC_API_KEY` / `CLAUDE_API_KEY` | `claude-3-5-sonnet-20241022` | `https://api.anthropic.com/v1` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4o` | `https://openrouter.ai/api/v1` |

各家的密钥格式不同，混用会 401：

- OpenAI / DeepSeek / OpenRouter：`sk-` 开头
- Anthropic：`sk-ant-` 开头
- Google 官方：`AIza` 开头

## 消息格式

不同厂商的 HTTP 请求体结构不同。`message_format` 决定用哪一套：

| 格式 | 请求体形状 | 用于 |
|------|-----------|------|
| `openai` | `messages[].content[] = {type: "text" \| "image_url"}` | OpenAI、DeepSeek、Ollama、LocalAI、vLLM、LM Studio、Azure、Together 等 |
| `anthropic` | `messages[].content[] = {type: "text" \| "image"} + source.base64` | Anthropic Claude API |
| `google` | `contents[].parts[] = {text} \| {inline_data}` | Google Gemini API |

接自定义服务时，先看它文档里给的 curl 示例长什么样，再对上表挑一个。

## 自定义端点

### 通过 Python 注册

```python
from vision_provider import VisionProvider

VisionProvider.register_custom_provider(
    name="ollama",
    base_url="http://localhost:11434/v1",
    default_model="llava:latest",
    message_format="openai",
    api_key=None,              # 本地服务通常不需要
    headers={},                # 自定义请求头
)

# 列出 / 注销
print(VisionProvider.list_custom_providers())
VisionProvider.unregister_custom_provider("ollama")
```

注册是**进程级**的。要在别的进程里用，得在代码里重新注册，或者改用
`--provider custom --base-url ...` 走命令行。

### 通过命令行接入

```bash
python vision_provider.py photo.jpg "描述这张图" \
    --provider custom \
    --base-url http://localhost:11434/v1 \
    --model llava:latest
```

带自定义请求头（Azure 用 `api-key` 而非 `Authorization`）：

```bash
python vision_provider.py photo.jpg "Describe" \
    --provider custom \
    --base-url https://your-resource.openai.azure.com \
    --model gpt-4o \
    --header "api-key:YOUR_KEY"
```

### 常见服务对照表

| 服务 | base_url | message_format | 需要 Key |
|------|----------|----------------|---------|
| Ollama | `http://localhost:11434/v1` | `openai` | 否 |
| LocalAI | `http://localhost:8080/v1` | `openai` | 否 |
| LM Studio | `http://localhost:1234/v1` | `openai` | 否 |
| vLLM | `http://localhost:8000/v1` | `openai` | 否 |
| llama.cpp server | `http://localhost:8080/v1` | `openai` | 否 |
| Azure OpenAI | `https://<res>.openai.azure.com` | `openai` | 是（`api-key` 头） |
| Together AI | `https://api.together.xyz/v1` | `openai` | 是 |
| Fireworks | `https://api.fireworks.ai/inference/v1` | `openai` | 是 |
| Groq | `https://api.groq.com/openai/v1` | `openai` | 是 |
| DeepInfra | `https://api.deepinfra.com/v1/openai` | `openai` | 是 |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `openai` | 是 |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `openai` | 是 |

### 本地模型推荐

想完全离线跑，这些视觉模型在 Ollama 上有现成的：

```bash
ollama pull llava            # 通用图像理解，7B
ollama pull llava:13b        # 更大，更准
ollama pull llama3.2-vision  # Meta 出品
ollama pull qwen2.5vl        # 中文场景表现好
ollama pull minicpm-v        # 小体积，适合低配机器
```

```python
VisionProvider.register_custom_provider(
    name="local",
    base_url="http://localhost:11434/v1",
    default_model="qwen2.5vl",
    message_format="openai",
)
print(VisionProvider(provider="local")
      .analyze_image("中文截图.png", "提取图中所有文字")["content"])
```

## 自动选择逻辑

`--provider auto`（默认）按此顺序找第一个凭据可用的：

```
deepseek → google → openai → anthropic → openrouter
```

DeepSeek 排第一是因为它在 OpenAI 兼容接口上提供视觉模型，
且通常与 DSH 默认凭据一致，成本也低。

想改优先级，见 `VisionProvider.detect_available_provider()` 里的 `order` 列表。

## 成本与速率

- 视觉调用比纯文本贵，按图片计费的厂商尤其注意
- 批量任务把 `max_concurrent` 控制在 3 以内
- 便宜的方案：先用本地模型粗筛，只把难判断的图交给云端
- 各家的速率限制在文档里，超了会返回 429
