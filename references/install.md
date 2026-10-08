# 安装指南

## 环境要求

- Python 3.7 或更高（CI 覆盖 3.9 – 3.13）
- pip
- 至少一个视觉模型的凭据（见下）

## 作为 DSH skill 安装

DSH 的 skill 目录是 `~/.dsh/skills/`，在 Windows 上是 `%USERPROFILE%\.dsh\skills\`。

```bash
git clone https://github.com/114514mbnb/dsh-can-see.git \
  ~/.dsh/skills/dsh-can-see
```

要求最终路径形如：

```
~/.dsh/skills/dsh-can-see/SKILL.md
```

**DSH 只扫描一层目录。** 如果你 clone 出来多套了一层
（例如 `~/.dsh/skills/dsh-can-see/dsh-can-see/SKILL.md`），DSH 不会发现它。
把里层内容提到 `~/.dsh/skills/dsh-can-see/` 即可。

装完装依赖：

```bash
pip install -r ~/.dsh/skills/dsh-can-see/requirements.txt
```

## 国内网络加速

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

其他镜像：

```bash
# 阿里云
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
# 腾讯云
pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple/
# 中科大
pip install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
```

设为默认，省得每次打 `-i`：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config list          # 确认
pip config unset global.index-url   # 改回官方源
```

## 离线安装

企业网络、代理或安全软件可能拦截 pip，典型症状是 `403 Forbidden`，或者
`Could not find a version that satisfies the requirement ...`。

### 办法 A：先下载 wheel 再离线装

```bash
pip download -r requirements.txt -d ./wheels \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

pip install --no-index --find-links ./wheels requests pillow pyyaml
```

### 办法 B：用 curl 抓包再离线装

有时 pip 被拦而 curl 正常（本项目作者就遇到过：pip 全部 403，curl 与
Python urllib 却畅通）。这时用 curl 下载：

```bash
# 从镜像索引页找到目标 wheel 的直链，例如：
#   https://pypi.tuna.tsinghua.edu.cn/packages/.../requests-2.34.2-py3-none-any.whl
curl -sL -o wheels/requests-2.34.2-py3-none-any.whl "<直链>"

pip install --no-index --find-links ./wheels requests pillow pyyaml
```

选 wheel 文件名的规则：

- Windows 64 位 + Python 3.13 → `cp313-cp313-win_amd64.whl`
- 纯 Python 包 → `py3-none-any.whl`

### 办法 C：临时关掉代理

```bash
# Linux / macOS
env -u http_proxy -u https_proxy pip install -r requirements.txt

# Windows CMD
set http_proxy=
set https_proxy=
pip install -r requirements.txt
```

## 配置凭据

本 skill 按以下顺序查找密钥，**任一命中即可**：

1. 命令行 `--api-key`
2. 环境变量
3. DSH 凭据库 `~/.dsh/.credentials.yaml` 的 `refs` 段

### 环境变量

```bash
# Linux / macOS
export DEEPSEEK_API_KEY="..."
export GEMINI_API_KEY="..."
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export OPENROUTER_API_KEY="..."
```

```powershell
# Windows PowerShell（永久）
[System.Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', '...', 'User')
```

```cmd
:: Windows CMD（永久）
setx DEEPSEEK_API_KEY "..."
```

### DSH 凭据库

如果 DSH 里已经配过某个 provider，通常什么都不用做。skill 会自动读取
`~/.dsh/.credentials.yaml`：

```yaml
version: 1
records: { ... }
refs:
  DEEPSEEK_API_KEY: "sk-..."
  GEMINI_API_KEY: "..."
```

> 注意：该文件包含明文密钥，请勿提交到任何仓库，也不要截图外发。

## 验证安装

```bash
# 1. 依赖
python -c "import requests, PIL, yaml; print('deps OK')"

# 2. 单元测试（不需要密钥）
python -m unittest discover -s tests -v

# 3. 看有哪些通道可用
python vision_provider.py --list-providers

# 4. 真实调用
python vision_provider.py your-image.png "描述这张图片"
```

## 常见问题

**`ModuleNotFoundError: No module named 'vision_provider'`**
在仓库根目录运行，或确认 `examples/`、`tests/` 下的脚本已把父目录加入
`sys.path`（仓库内置脚本已经处理）。

**`未找到可用的视觉模型凭据`**
三种凭据来源都没命中。检查环境变量是否在当前 shell 生效
（`echo $DEEPSEEK_API_KEY`），或确认 `~/.dsh/.credentials.yaml` 存在且
`refs` 段有对应键。

**401 / 403**
密钥无效或无权访问该模型。注意不同服务的 key 格式不同 —— 例如 Google 官方
API 的 key 是 `AIza` 开头，别的服务发的 key 拿去调 Gemini 会 401。

**`safety filter` / 内容被拒**
部分提供商对某些图像有内容策略限制，换一个提供商重试。

**图片太大**
单张上限 20 MB，建议 5 MB 以内。可以用 Pillow 压缩：

```python
from PIL import Image
img = Image.open("huge.jpg")
img.thumbnail((1920, 1080))
img.save("small.jpg", quality=85)
```
