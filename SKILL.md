---
name: dsh-can-see
description: 让部署在 DSH 里的纯文本模型（GPT、Claude 等）能够看到图片。当用户发来图片、截图、照片、扫描件、图表、UI 稿，而当前模型不支持图像输入时，用本 skill 把图片交给一个视觉模型（DeepSeek / Gemini / GPT-4o / Claude / OpenRouter / 本地 Ollama）识别，拿回文字描述后继续推理。也用于 OCR 提取图中文字、读取图表数据、对比多张图片、批量处理图片目录。触发词：看图、这张图、截图里、识别图片、提取图中文字、OCR、图片内容、describe this image、read this screenshot。
---

# dsh-can-see

给当前模型「装上眼睛」。

当主模型不支持图像输入时，本 skill 把图片转成文字，交回主模型继续处理。

## 什么时候用

- 用户发了图片 / 截图 / 照片，而你看不到图像内容
- 需要 OCR：从截图、扫描件中提取文字
- 需要读图表：从统计图里取数据、看趋势
- 需要对比：两张图有什么差别
- 需要批量：一个目录里几十张图都要过一遍

## 怎么用

**零配置。** 脚本会自动从环境变量或 DSH 凭据库找到可用密钥，
并挑选一个支持视觉的通道，不需要用户提供任何 API Key。

### 命令行

```bash
python vision_provider.py <图片路径> "<你的问题>"
```

完整写法（把 `<skill目录>` 换成本 skill 的安装位置，
Windows 下即 `%USERPROFILE%\.dsh\skills\dsh-can-see`）：

```bash
python "<skill目录>/vision_provider.py" "D:/path/to/image.png" "这张图里有什么？"
```

### Python 调用

```python
from vision_provider import describe_image

answer = describe_image("D:/path/to/image.png", "这张图里有什么？")
print(answer)
```

## 常用例子

```bash
# 一般识别
vision_provider.py photo.jpg "详细描述这张图片"

# OCR 提取文字
vision_provider.py screenshot.png "提取图中所有文字，保持原有排版"

# 读图表
vision_provider.py chart.png "这张图表的趋势是什么？关键数据点有哪些？"

# 看报错截图
vision_provider.py error.png "这个报错说明了什么？怎么解决？"

# 指定走某个提供商（默认 auto 自动选）
vision_provider.py photo.jpg "描述" --provider openai
vision_provider.py photo.jpg "描述" --provider google --model gemini-2.0-flash-exp

# 输出 JSON
vision_provider.py photo.jpg "描述" --output result.json

# 查看可用通道
vision_provider.py --list-providers
```

## 支持的通道

| 提供商 | 环境变量 | 默认视觉模型 |
|--------|---------|------------|
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-v4-flash-vision-exp` |
| `google` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `gemini-2.0-flash-exp` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4o` |
| `custom` | 任意 | 自行指定 |

`auto` 优先级：`deepseek` → `google` → `openai` → `anthropic` → `openrouter`。

## 接入本地或自建模型

Ollama、LocalAI、vLLM、LM Studio、Azure OpenAI 等兼容 OpenAI 接口的服务：

```python
from vision_provider import VisionProvider

VisionProvider.register_custom_provider(
    name="ollama",
    base_url="http://localhost:11434/v1",
    default_model="llava:latest",
    message_format="openai",       # openai / anthropic / google
)

p = VisionProvider(provider="ollama")
print(p.analyze_image("photo.jpg", "描述这张图")["content"])
```

命令行等价写法：

```bash
vision_provider.py photo.jpg "描述" \
    --provider custom \
    --base-url http://localhost:11434/v1 \
    --model llava:latest
```

需要自定义请求头时（如 Azure 用 `api-key` 而非 `Authorization`）：

```bash
vision_provider.py photo.jpg "描述" \
    --provider custom \
    --base-url https://your-resource.openai.azure.com \
    --model gpt-4o \
    --header "api-key:YOUR_KEY"
```

## 批量处理

```python
from vision_provider import VisionProvider

p = VisionProvider(provider="deepseek")
results = p.batch_analyze(
    image_dir="D:/photos",
    prompt="为这张图生成一句标题",
    max_concurrent=3,          # 注意各家的速率限制
)
for r in results:
    print(r["image_path"], "->", r.get("content", r.get("error")))
```

## 返回值

```python
{
    "success": True,
    "content": "模型给出的文字回答",
    "model":   "deepseek-flash",
    "usage":   {"total_tokens": 363, ...},
    "metadata": {"provider": "deepseek", "image_count": 1},
}
```

命令行退出码：`0` 成功，`1` 调用失败，`2` 参数或凭据错误。

## 注意事项

- 单张图片上限 20MB，建议 5MB 以内
- 图片格式：jpg / jpeg / png / gif / webp / bmp
- 密钥不会出现在错误信息里（已做脱敏）
- 这会把图片内容发给第三方服务，涉及隐私的图片先跟用户确认
- 各家速率限制和计费不同，批量任务建议 `max_concurrent` ≤ 3

## 依赖

```
requests >= 2.31.0
pillow   >= 10.0.0
pyyaml   >= 6.0
```

安装：`pip install -r requirements.txt`

更多说明见仓库 `README.md` 与 `references/`。
