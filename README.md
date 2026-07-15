# deal-document-intelligence

Learning project: building AI models that extract
structured information - **clauses**, **entities**, and related signals - from
deal / contract documents.

## Roadmap

1. **[you are here] Minimal reproducible repo + explore CUAD** — see real
   input→output examples before choosing a model.
2. Fine-tune a baseline encoder (DeBERTa-v3 / Legal-BERT) on CUAD.
3. Evaluate properly (per-clause F1 / AUPR).
4. Publish weights + a model card to the HF Hub.
5. Branch out: entity extraction (NER), then a *private* Ansarada adaptation.

## Setup

```bash
# One-time: point Poetry at Python 3.12
poetry env use 3.12

# Install the light exploration stack (no torch yet)
poetry install

# Explore the CUAD dataset — prints a few annotated clauses
poetry run python scripts/explore_cuad.py
```

The heavier training stack is installed separately when we need it:

```bash
poetry install --with training
```
