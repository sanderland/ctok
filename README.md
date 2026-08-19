# ctok

`ctok` reconstructs Claude token counts offline, with no API call, network access, or runtime
dependencies. It is unofficial and is not affiliated with Anthropic.

The reconstruction targets counts. Claude does not expose token boundaries, so `tokenize()` returns
one valid minimum-cost tiling, not a claim about Anthropic's exact segmentation. The research behind
the model is described in [On the biology of Claude's tokenizer](https://tokencontributions.substack.com/p/on-the-biology-of-claudes-tokenizer).

## Install

```bash
pip install ctok
```

## Quick start

```python
from ctok import token_count, tokenize

token_count("hello, world")           # 10, using the v3 family
token_count("hello, world", "4.7")    # 15
token_count("hello, world", "5.0")    # 10

tokens = tokenize("NASA likes tokenizers")
assert len(tokens) == token_count("NASA likes tokenizers")
```

The command-line interface prints the marked stream and its tiling:

```bash
ctok "hello, world"
```

## Supported families

`version` is a string such as `"4.7"`. Components are compared as integers, so `"4.10"` sorts
after `"4.9"`. Python reads the float literal `4.10` as `4.1`, so passing a non-string version
raises `TypeError`.

| requested version | family | model generation |
|---|---|---|
| `"3.0" <= version < "4.7"` | v3, the default | Claude 3 through Opus 4.6 |
| `"4.7" <= version < "5.0"` | v4.7 | Opus 4.7 through 4.9 |
| `version >= "5.0"` | v5 | Opus 5 and Sonnet 5 |

v5 uses the v4.7 vocabulary with a different message frame.

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
| Goldfish, 350 languages and 962,054 rows | mining | 962,053 | 962,054 |
| MultiPL-E, 22 programming languages | held out | 22 | 22 |
| Rosetta Code, 1,741 documents | mining | 1,741 | 1,741 |
| Rosetta Code, separate 250 documents | held out | 250 | 250 |
| UDHR, 501 languages | mining (in-sample since 2026-08-12) | 501 | 501 |

v5 is omitted from the table because its deviation from recorded counts matches v4.7's on every
gated document. Separate API tests cover its message-frame rules.

The stored measurement sets contain no under-counts: 0 of 2,276,929 v3 texts and 0 of 2,328,425
v4.7 texts. This does not guarantee the result for arbitrary input. Goldfish, the main Rosetta
sample, and UDHR informed piece selection. MultiPL-E and the separate Rosetta sample did not.

Run the public gates with:

```bash
uv run pytest
uv run python tests/gates.py
```

## Vocabulary evidence

The two vocabulary files contain 48,706 v3 pieces and 15,256 v4.7 pieces. Every entry has a fixed
membership witness or is one of the structural marker atoms checked by the test suite.

```python
from ctok import pieces, witness

len(pieces("4.7"))                       # 15256
witness("⟨bow⟩the⟨eow⟩", "4.7")
# {'probe': 'the', 'raw': 12, 'kind': 'raw'}
```

A witness says that one marked piece costs one token in a calibrated probe. It does not prove the
encoder rewrite or resolve ties between equal-cost tilings. `tests/test_witness.py` checks every
published witness and requires complete witnessed-or-special coverage.

## License

MIT
