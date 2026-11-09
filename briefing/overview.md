# Overview

This paper proposes ATLAS, an adaptive testing framework for evaluating LLMs with calibrated
benchmark item banks. Instead of asking every model every item, ATLAS estimates a model's latent
ability and repeatedly chooses high-information items targeted to that estimate.

This workspace packages a reproduction on the paper's released calibrated item banks and response
matrices for TruthfulQA, WinoGrande, HellaSwag, GSM8K and ARC. Methods are item-selection policies
queried through an evaluator-owned response oracle; at three evaluator-fixed item budgets per
benchmark they are scored on how closely their ability estimates match whole-bank abilities of
held-out models, how well raw accuracy can be reconstructed, and how concentrated their item use is.
The reproduced ATLAS recovers whole-bank ability with fewer than 100 items far better than a static
100-item random subset.
