# dsh-can-see

**Give text-only models in [DSH](https://github.com/deepseek-ai) the ability to see images.**

[![tests](https://github.com/114514mbnb/dsh-can-see/actions/workflows/tests.yml/badge.svg)](https://github.com/114514mbnb/dsh-can-see/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)

English · [简体中文](README.zh-CN.md)

---

## The problem

DSH lets you plug in any third-party model — GPT, Claude, Gemini, open-weight models
via OpenRouter, or a local Ollama instance. Many of them are text-only.

So when a user pastes a screenshot, a photo, a chart, or a scanned document, the model
is blind. It gets a filename and nothing else.

## The fix

`dsh-can-see` is a DSH skill that gives those models eyes — **without swapping the model
you're already using**.

When you send an image, the skill routes it to a vision-capable model, gets back a text
description, and hands that back to your main model. Your GPT/Claude session keeps its
personality, its context, and its tooling — it just gains sight.

```
用户: [截图.png] 这个报错怎么解决？

  └─ 主模型 (text-only)  ──→  dsh-can-see  ──→  视觉模型
                                                  │
     "根据截图里的报错 `KeyError: 'user_id'`..."  ←┘
```

## Features

- **Zero configuration** — auto-detects credentials from environment variables or the
  DSH credential store (`~/.dsh/.credentials.yaml`). No new API key needed if you
  already have one configured.
- **Auto provider selection** — picks the first available vision channel, no flags required.
- **Six built-in providers** — DeepSeek, Google Gemini, OpenAI, Anthropic, OpenRouter,
  plus any OpenAI-compatible endpoint.
- **Bring your own model** — Ollama, LocalAI, vLLM, LM Studio, Azure OpenAI, or your
  company's internal API.
- **Local-first friendly** — works fully offline with a local vision model.
- **Batch processing** — point it at a directory, get results back concurrently.
- **Secret-safe** — API keys are redacted from all error output.
- **48 unit tests** — plus a hermetic end-to-end test against a mock vision service.

## Install

### As a DSH skill (recommended)

```bash
git clone https://github.com/114514mbnb/dsh-can-see.git \
  ~/.dsh/skills/dsh-can-see

pip install -r ~/.dsh/skills/dsh-can-see/requirements.txt
```

On Windows, `~/.dsh` is `%USERPROFILE%\.dsh`.

DSH discovers skills one level deep, so the path must be
`~/.dsh/skills/dsh-can-see/SKILL.md`.

### Just the library

```bash
pip install -r requirements.txt
```

## Usage

### Ask about an image

```bash
python vision_provider.py screenshot.png "这个报错说明了什么？"
```

No `--provider` flag needed. Output:

```
[auto] using provider: deepseek
============================================================
The screenshot shows a Python KeyError: 'user_id' raised at line 42...
============================================================
```

### From Python

```python
from vision_provider import describe_image

print(describe_image("chart.png", "What's the trend in this chart?"))
```

### Pick a provider explicitly

```bash
python vision_provider.py photo.jpg "Describe this" --provider openai
python vision_provider.py photo.jpg "Describe this" --provider google --model gemini-2.0-flash-exp
python vision_provider.py --list-providers
```

### Batch a directory

```python
from vision_provider import VisionProvider

vp = VisionProvider(provider="deepseek")
for r in vp.batch_analyze("./screenshots", "Summarize this screenshot", max_concurrent=3):
    print(r["image_path"], "->", r.get("content", r.get("error")))
```

## Supported providers

| Provider | Env var | Default vision model |
|----------|---------|---------------------|
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-v4-flash-vision-exp` |
| `google` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `gemini-2.0-flash-exp` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` |
| `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4o` |
| `custom` | any | you choose |

`auto` tries them in that order (DeepSeek first, then Google, OpenAI, Anthropic,
OpenRouter) and uses the first one with a usable credential.

## Bring your own endpoint

Anything that speaks the OpenAI chat-completions format works:

| Service | `base_url` | `message_format` |
|---------|-----------|------------------|
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
      .analyze_image("photo.jpg", "Describe this image")["content"])
```

Or entirely from the CLI:

```bash
python vision_provider.py photo.jpg "Describe this" \
    --provider custom \
    --base-url http://localhost:11434/v1 \
    --model llava:latest
```

Full guide: [`references/providers.md`](references/providers.md)

## Configuration

Credentials are resolved in this order:

1. `--api-key` on the command line
2. Environment variables (`DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`,
   `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`)
3. DSH's credential store, `~/.dsh/.credentials.yaml` (its `refs` section)

Because of step 3, if DSH already knows about a provider, this skill works with no setup.

You can also use a YAML config file — see [`config.example.yaml`](config.example.yaml):

```python
from vision_provider import VisionProvider
vp = VisionProvider.from_config("config.yaml")
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | provider call failed |
| `2` | bad arguments or missing credentials |

Useful for scripting and agent orchestration.

## Security notes

- **Keys are never logged.** Errors are passed through a redaction filter that strips
  `?key=...`, `Bearer ...`, `sk-...`, and `AQ....` patterns before they reach output.
  This matters because Google's API takes the key as a URL query parameter, which would
  otherwise leak into exception messages.
- **No credentials in this repo.** A test suite enforces this.
- **Images leave your machine.** Anything you analyze is sent to whichever provider you
  selected. Don't send sensitive images to a third-party API.

## Requirements

- Python 3.7+
- `requests>=2.31.0`, `pillow>=10.0.0`, `pyyaml>=6.0`

## Tests

```bash
python -m unittest discover -s tests -v
# or
python -m pytest tests/ -v
```

## License

[MIT](LICENSE)
