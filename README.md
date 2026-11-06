# Adaptive Testing for LLM Evaluation: A Psychometric Alternative to Static Benchmarks

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2511.04689"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2511.04689-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| | |
|---|---|
| **Paper ID** | [2511.04689](https://arxiv.org/abs/2511.04689) |

## Summary

This paper proposes ATLAS, an adaptive testing framework for evaluating LLMs with calibrated benchmark item banks. Instead of asking every model every item, ATLAS estimates a model's latent ability and repeatedly chooses high-information items targeted to that estimate.

## Problem

How can an evaluator estimate the benchmark ability of many language models with far fewer administered items than a full static benchmark, while preserving reliable rankings and uncertainty-aware scores?

## The paper's method

ATLAS reframes LLM benchmark evaluation as computerized adaptive testing over calibrated IRT item banks.

## Run it

```bash
pip install sciworld
sw research 2511.04689 --mode innovate --agent claude-code
sw evaluate 2511.04689
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

