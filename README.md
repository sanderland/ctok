# ctok

**C**laude **T**okenizer **O**ffline, **K**inda — reproduces Claude's token *counts* with no API
call, no network and no dependencies.

Unofficial, not affiliated with Anthropic. Everything here was derived by probing `count_tokens`, so
counts are reproduced but token boundaries are approximate. Write-up: [TODO: substack link].

```python
from ctok import token_count, tokenize

token_count("hello, world")         # 10
token_count("hello, world", 4.7)    # 15 — a different tokenizer family

tokenize("NASA likes tokenizers")   # token_count is len() of this
# ['⟨pad⟩' ×7, '⟨caps⟩⟨bow⟩nasa⟨eow⟩', '⟨bow⟩likes⟨eow⟩', '⟨bow⟩token', 'izers⟨eow⟩']
```

Tokens carry their structure in-line: `⟨bow⟩`/`⟨eow⟩` word boundaries, `⟨shift⟩`/`⟨caps⟩` case,
`⟨0xNN⟩` sub-character bytes, and `⟨pad⟩` for the single-message frame. There is a CLI too:
`ctok "hello, world"`.

## Versions

| version | family | reconstructs |
|---|---|---|
| `3.0` – `4.6` (default) | v3 | Claude 3 … Opus 4.5/4.6 |
| `4.7` – `4.9` | v4.7 | Opus 4.7+ |
| anything else | — | `NotImplementedError` |

Versions are decimals, so `4.10` means 4.1. A model id also routes:
`token_count(text, "claude-opus-4-7")`.

## Accuracy

Scored offline against recorded `count_tokens` values over two parallel corpora — the same content
in every language, so only the language varies. UDHR is one declaration in 501 natural languages;
[MultiPL-E](https://huggingface.co/datasets/nuprl/MultiPL-E) is 25 HumanEval problems in 22
programming languages. Both run from committed fixtures: `uv run pytest`.

| corpus | family | error mass | mean \|rel err\| | exact | within 1% |
|---|---|---:|---:|---:|---:|
| UDHR (501 languages) | v3 | 0.917% | 0.408% | 263/501 | 92.6% |
| UDHR | v4.7 | 0.879% | 0.465% | 240/501 | 90.4% |
| MultiPL-E (22 languages) | v3 | 0.069% | 0.073% | 11/22 | 100% |
| MultiPL-E | v4.7 | 0.498% | 0.499% | 1/22 | 81.8% |

Largest known residual: an under-count in Brahmic and South-East Asian scripts, where the vocabulary
has no pieces and the byte floor is the entire model.

## License

MIT
