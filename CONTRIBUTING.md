# Contributing to dsh-can-see

Thanks for wanting to help models see. 🎉

## Quick start

```bash
git clone https://github.com/114514mbnb/dsh-can-see.git
cd dsh-can-see

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m unittest discover -s tests -v
```

All 48 tests should pass. No API keys are required for the test suite — everything
network-related is mocked.

## Project layout

```
dsh-can-see/
├── SKILL.md                    # DSH skill entry point (frontmatter: name, description)
├── vision_provider.py          # core module + CLI
├── requirements.txt
├── config.example.yaml
├── examples/
│   ├── basic_usage.py
│   └── custom_providers.py
├── references/
│   ├── install.md              # install guide incl. mirrors & offline
│   └── providers.md            # provider matrix & custom endpoints
└── tests/
    └── test_vision_provider.py # 48 tests
```

## What we'd love help with

- **More providers** — Qwen-VL, GLM-4V, Mistral Pixtral, Groq, Fireworks, Bedrock.
  Open an issue first so we can agree on the shape.
- **More tests** — edge cases in image encoding, retry/backoff, rate-limit handling.
- **Docs** — worked examples for real tasks (reading a receipt, diffing two UI shots).
- **Translations** — the README currently ships in English and Simplified Chinese.

## Adding a new built-in provider

Four small edits in `vision_provider.py`:

1. Add the name to `SUPPORTED_PROVIDERS`.
2. Add the default vision model to `DEFAULT_MODELS`.
3. Add env var aliases to `ENV_ALIASES` (list every name you want to accept).
4. Add the base URL to the `url_map` inside `_get_base_url()`.

Then route it in `_process_request()` — most providers reuse `openai`,
`anthropic`, or `google` message formats, so it's often just adding the name to an
existing branch.

Finish by adding tests. At minimum: default model, base URL, message format routing,
and env-var resolution. See `TestDeepSeekProvider` for a template.

## House rules

- **Never commit credentials.** Tests compare repo contents against a real credential
  store; keep all fixtures obviously fake (`sk-0000...`, `AQ.FAKE...`).
- **Redact before you print.** Any new error path must go through `redact()`.
- **Keep it dependency-light.** `requests` + `pillow` + `pyyaml` is the budget.
  Adding a fourth needs a good reason.
- **Tests must not touch the network.** Patch `requests.post`.
- **CI must stay green.** It runs on Linux, macOS, and Windows across Python 3.9–3.13.

## Commit messages

Conventional Commits are appreciated, not enforced:

```
feat(provider): add Qwen-VL support
fix(cli): exit with code 2 on missing credentials
docs(readme): clarify DSH skill install path
```

## Reporting bugs

Include: OS, Python version, the command you ran (with keys removed), the full traceback,
and what you expected instead.

For suspected credential leaks, please **do not** open a public issue — email the
maintainer directly.

## License

By contributing you agree your work is released under the [MIT License](LICENSE).
