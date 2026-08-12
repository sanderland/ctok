# ctok

`ctok` reconstructs Claude token counts offline, with no API call, network access, or runtime
dependencies. It is unofficial and is not affiliated with Anthropic.

The reconstruction targets counts. Claude does not expose token boundaries, so `tokenize()` returns
one valid minimum-cost tiling, not a claim about Anthropic's exact segmentation. The research behind
the model is described in [On the biology of Claude's tokenizer](https://tokencontributions.substack.com/p/on-the-biology-of-claudes-tokenizer).

## Quick start

```python
from ctok import token_count, tokenize

token_count("hello, world")         # 10, using the v3 family
token_count("hello, world", 4.7)    # 15
token_count("hello, world", 5.0)    # 10

tokens = tokenize("NASA likes tokenizers")
assert len(tokens) == token_count("NASA likes tokenizers")
```

The command-line interface prints the marked stream and its tiling:

```bash
ctok "hello, world"
```

## Supported families

| requested version | family | model generation |
|---|---|---|
| `3.0 <= version < 4.7` | v3, the default | Claude 3 through Opus 4.6 |
| `4.7 <= version < 5.0` | v4.7 | Opus 4.7 through 4.9 |
| `version >= 5.0` | v5 | Opus 5 and Sonnet 5 |

Model IDs such as `"claude-opus-4-7"` are accepted too. Versions are decimal values, so `4.10`
means `4.1`.

v5 has its own measured six-token message frame and uses the v4.7 vocabulary. Opus 5 and Sonnet 5
matched on all 80 comparison texts. No v5-specific piece has been measured, so a future vocabulary
difference would require a separate reconstruction.

## How it works

For one user message, `ctok`:

1. normalizes the text, including NFC and family-specific quote folding;
2. rewrites it into a stream with word, case, and byte markers;
3. finds a minimum-cost tiling over the measured vocabulary and UTF-8 byte fallback;
4. adds the measured message frame.

`token_count(text)` is `len(tokenize(text))`. The output notation makes internal structure visible:

| notation | meaning |
|---|---|
| `⟨bow⟩`, `⟨eow⟩` | word boundaries |
| `⟨shift⟩`, `⟨caps⟩` | case rewrites |
| `⟨0xNN⟩` | a byte-fallback token |
| `⟨pad⟩` | part of the single-message frame |

## Measured accuracy

These results compare `ctok` with recorded `count_tokens` responses:

| corpus | role | v3 exact | v4.7 exact |
|---|---|---:|---:|
| Goldfish, 350 languages and 350,000 rows | mining | 350,000 | 350,000 |
| MultiPL-E, 22 programming languages | held out | 22 | 22 |
| Rosetta Code, 1,741 documents | mining | 1,741 | 1,741 |
| Rosetta Code, separate 250 documents | mining | not measured | 250 |
| UDHR, 501 languages | held out | 493 | 500 |

Every UDHR document is within 1%; the worst v3 document is `+0.1%`. v5 has the same content result as
v4.7 because it uses the same vocabulary.

The stored measurement sets contain no under-counts: 0 of 1,664,940 v3 texts and 0 of 1,722,961
v4.7 texts. This is an empirical result, not a guarantee for arbitrary input. Goldfish and Rosetta
may select candidates. UDHR and MultiPL-E never do.

Run the public gates with:

```bash
uv run pytest
uv run python tests/gates.py --markdown
```

## Vocabulary evidence

The two vocabulary files contain 48,632 v3 pieces and 15,237 v4.7 pieces. Every entry has a fixed
membership witness or is one of the structural marker atoms checked by the test suite.

```python
from ctok import pieces, witness

len(pieces(4.7))                         # 15237
witness("⟨bow⟩the⟨eow⟩", 4.7)
# {'probe': 'the', 'raw': 12, 'kind': 'raw'}
```

A witness says that one marked piece costs one token in a calibrated probe. It does not prove the
encoder rewrite or resolve ties between equal-cost tilings. `tests/test_witness.py` checks every
published witness and requires complete witnessed-or-special coverage.

See [LIMITS.md](LIMITS.md) for message types outside the model, known risky input shapes, and how to
interpret the validation results.

## License

MIT
