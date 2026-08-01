# ctok

**C**laude **T**okenizer **O**ffline, **K**inda — reproduces Claude's token *counts* with no API
call, no network and no dependencies.

Unofficial, not affiliated with Anthropic. Everything here was derived by probing `count_tokens`, so
counts are reproduced but token boundaries are approximate. Write-up [here](https://open.substack.com/pub/tokencontributions/p/on-the-biology-of-claudes-tokenizer
).

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

Scored offline against recorded `count_tokens` values, all from committed fixtures: `uv run pytest`.

Two corpora are *parallel* — the same content in every language, so only the language varies. UDHR
is one declaration in 501 natural languages; [MultiPL-E](https://huggingface.co/datasets/nuprl/MultiPL-E)
is 25 HumanEval problems in 22 programming languages. The third is the opposite: real, unedited
[Rosetta Code](https://huggingface.co/datasets/christopher/rosetta-code) source in hundreds of
languages, which varies everything at once.

| corpus | family | error mass | mean \|rel err\| | exact | within 1% |
|---|---|---:|---:|---:|---:|
| UDHR (501 languages) | v3 | 0.894% | 0.394% | 273/501 | 92.4% |
| UDHR | v4.7 | 0.806% | 0.396% | 287/501 | 92.2% |
| MultiPL-E (22 languages) | v3 | 0.059% | 0.061% | 15/22 | 100% |
| MultiPL-E | v4.7 | 0.000% | 0.000% | 22/22 | 100% |
| Rosetta Code (1,741 docs) | v3 | 0.065% | 0.073% | 1552/1741 | 97.7% |
| Rosetta Code | v4.7 | 0.000% | 0.000% | 1741/1741 | 100% |
| Rosetta Code, held out (250) | v4.7 | 0.013% | 0.012% | 247/250 | 99.6% |

**Read the held-out row, not the one above it.** The 1,741-document sample is the one every mining
campaign bisects against: pieces are accepted on membership probes rather than on documents, but
the documents choose which candidates get probed, so its rate is in-sample. The held-out sample is
drawn from blocks that one never touched, and nothing in the vocabulary was probed because of it.

Largest known residual: an under-count in Brahmic and South-East Asian scripts, where the vocabulary
has no pieces and the byte floor is the entire model — and, the same problem in another script
family, marks whose cost belongs to the base+mark pair rather than to the mark.

## License

MIT
