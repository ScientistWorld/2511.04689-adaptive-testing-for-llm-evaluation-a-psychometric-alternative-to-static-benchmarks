# Overview

This paper proposes ATLAS, an adaptive testing framework for evaluating LLMs with calibrated benchmark item banks. Instead of asking every model every item, ATLAS estimates a model's latent ability and repeatedly chooses high-information items targeted to that estimate.

This workspace packages a reproduction using the paper's released calibrated item banks and response matrices. The initial run targets the core claim on TruthfulQA, WinoGrande, and HellaSwag: ATLAS should approximate full-bank ability with fewer items than a static 100-item random baseline.
