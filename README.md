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
| UDHR (501 languages) | v3 | 0.225% | 0.148% | 278/501 | 96.0% |
| UDHR | v4.7 | 0.137% | 0.111% | 296/501 | 97.2% |
| MultiPL-E (22 languages) | v3 | 0.059% | 0.061% | 15/22 | 100% |
| MultiPL-E | v4.7 | 0.000% | 0.000% | 22/22 | 100% |
| Rosetta Code (1,741 docs) | v3 | 0.065% | 0.073% | 1552/1741 | 97.7% |
| Rosetta Code | v4.7 | 0.000% | 0.000% | 1741/1741 | 100% |
| Rosetta Code, held out (250) | v4.7 | 0.006% | 0.007% | 249/250 | 99.6% |

**UDHR and MultiPL-E are the held-out gates.** Nothing in the vocabulary is selected, accepted or
rejected because of them; they are read at the end of a campaign to find out whether it worked. Both
Rosetta samples are mining corpora — the 1,741 documents are what every campaign bisects against,
and the 250 are drawn from blocks that sample never touched, so the second rate is out-of-sample for
anything the first chose. A piece is accepted on a membership probe either way; the corpus only ever
decides which candidate gets asked.

No document in either family is now more than 5% off; 15 in each were, before the akshara law (a
mark that closes its orthographic syllable also closes the word, so a conjunct is two words and
carries the boundary markers that say so). What is left is vocabulary rather than structure — the
residual is spread in both directions instead of being a one-sided under-count — and the largest
remaining piece of it is Brahmic and South-East Asian clusters that have not been mined yet.

## License

MIT
