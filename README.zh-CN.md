# dsh-can-see

**让部署在 DSH 里的纯文本模型（GPT、Claude 等）能够看到图片。**

[English](README.md) · 简体中文

---

## 解决什么问题

DSH 允许接入任意第三方模型 —— GPT、Claude、Gemini、通过 OpenRouter 的开源模型，
或者本地的 Ollama。其中很多是纯文本模型。

于是当用户丢来一张截图、照片、图表或扫描件时，模型什么也看不见。
它只拿到一个文件名。

## 怎么解决

`dsh-can-see` 是一个 DSH skill，给这些模型装上眼睛，**而无需更换你正在用的模型**。

收到图片后，skill 把它转给一个支持视觉的模型，拿回文字描述，
再交还给你的主模型。你的 GPT / Claude 会话保留它的人格、上下文和工具链，
只是多了「看得见」这项能力。

```
用户: [截图.png] 这个报错怎么解决？

  └─ 主模型 (纯文本)  ──→  dsh-can-see  ──→  视觉模型
                                              │
     "根据截图里的报错 `KeyError: 'user_id'`..." ←┘
```

## 特性

- **零配置** —— 自动从环境变量或 DSH 凭据库（`~/.dsh/.credentials.yaml`）发现密钥。
  已经配过的 provider，不需要任何新 API Key。
- **自动挑选通道** —— 不带任何参数，脚本自己选一个可用的视觉通道。
- **内置 6 种提供商** —— DeepSeek、Google Gemini、OpenAI、Anthropic、OpenRouter，
  以及任意 OpenAI 兼容端点。
- **支持本地模型** —— Ollama、LocalAI、vLLM、LM Studio、Azure OpenAI、公司内部 API。
- **可完全离线** —— 配一个本地视觉模型即可全程不出网。
- **批量处理** —— 指向一个目录，并发跑完。
- **密钥安全** —— 错误输出中的密钥会被自动脱敏。
- **48 项单元测试** —— 另含一个针对 mock 视觉服务的端到端测试。

## 安装

### 作为 DSH skill（推荐）

```bash
git clone https://github.com/114514mbnb/dsh-can-see.git \
  ~/.dsh/skills/dsh-can-see

pip install -r ~/.dsh/skills/dsh-can-see/requirements.txt
```

Windows 上 `~/.dsh` 即 `%USERPROFILE%\.dsh`。

DSH 只扫描一层目录，所以路径必须是 `~/.dsh/skills/dsh-can-see/SKILL.md`。

国内网络建议用镜像加速：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

详见 [`references/install.md`](references/install.md)。

### 只用库

```bash
pip install -r requirements.txt
```

## 使用

### 问一张图

```bash
python vision_provider.py 截图.png "这个报错说明了什么？"
```

不需要 `--provider` 参数。输出：

```
[auto] 使用提供商: deepseek
============================================================
截图中显示了一个 Python 的 KeyError: 'user_id'，抛出位置在第 42 行……
============================================================
```

### Python 调用

```python
from vision_provider import describe_image

print(describe_image("图表.png", "这张图的趋势是什么？"))
```

### 指定提供商

```bash
python vision_provider.py photo.jpg "描述这张图" --provider openai
python vision_provider.py photo.jpg "描述这张图" --provider google --model gemini-2.0-flash-exp
python vision_provider.py --list-providers
```

### 批量处理

```python
from vision_provider import VisionProvider

vp = VisionProvider(provider="deepseek")
for r in vp.batch_analyze("./截图", "概括这张截图的内容", max_concurrent=3):
    print(r["image_path"], "->", r.get("content", r.get("error")))
```

## 支持的提供商

| 提供商 | 环境变量 | 默认视觉模型 |
|--------|---------|------------|
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-v4-flash-vision-exp` |
| `google` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `gemini-2.0-flash-exp` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4o` |
| `custom` | 任意 | 自行指定 |

`auto` 按上表顺序尝试，取第一个凭据可用的通道。

## 接入自己的端点

任何兼容 OpenAI chat-completions 格式的服务都能接：

| 服务 | `base_url` | `message_format` |
|------|-----------|------------------|
| Ollama | `http://localhost:11434/v1` | `openai` |
| LocalAI | `http://localhost:8080/v1` | `openai` |
| LM Studio | `http://localhost:1234/v1` | `openai` |
| vLLM | `http://localhost:8000/v1` | `openai` |
| Azure OpenAI | `https://<res>.openai.azure.com` | `openai` |
| Together AI | `https://api.together.xyz/v1` | `openai` |

```python
from vision_provider import VisionProvider

VisionProvider.register_custom_provider(
    name="ollama",
    base_url="http://localhost:11434/v1",
    default_model="llava:latest",
    message_format="openai",
)

print(VisionProvider(provider="ollama")
      .analyze_image("photo.jpg", "描述这张图")["content"])
```

纯命令行也能接：

```bash
python vision_provider.py photo.jpg "描述这张图" \
    --provider custom \
    --base-url http://localhost:11434/v1 \
    --model llava:latest
```

完整指南：[`references/providers.md`](references/providers.md)

## 配置

凭据按以下顺序解析：

1. 命令行的 `--api-key`
2. 环境变量（`DEEPSEEK_API_KEY`、`GEMINI_API_KEY`、`OPENAI_API_KEY`、
   `ANTHROPIC_API_KEY`、`OPENROUTER_API_KEY`）
3. DSH 凭据库 `~/.dsh/.credentials.yaml` 的 `refs` 段

因为第 3 条，只要 DSH 里已经配过某个提供商，本 skill 开箱即用。

也可以用 YAML 配置文件，见 [`config.example.yaml`](config.example.yaml)：

```python
from vision_provider import VisionProvider
vp = VisionProvider.from_config("config.yaml")
```

## 退出码

| 码 | 含义 |
|----|------|
| `0` | 成功 |
| `1` | 调用失败 |
| `2` | 参数错误或凭据缺失 |

便于脚本和 agent 编排。

## 安全说明

- **密钥不会进入日志。** 所有错误信息会经过脱敏过滤器，抹掉 `?key=...`、
  `Bearer ...`、`sk-...`、`AQ....` 等模式。这一点很关键 ——
  Google 的 API 把密钥放在 URL 查询参数里，否则会随异常信息一起泄露。
- **本仓库不含任何凭据。** 有测试用例在守这条线。
- **图片会离开你的机器。** 发给第三方 API 就意味着内容外传，
  敏感图片请先确认。

## 环境要求

- Python 3.7+
- `requests>=2.31.0`、`pillow>=10.0.0`、`pyyaml>=6.0`

## 测试

```bash
python -m unittest discover -s tests -v
# 或
python -m pytest tests/ -v
```

## 许可证

[MIT](LICENSE)
