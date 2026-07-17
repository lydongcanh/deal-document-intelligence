"""Stage 8 — Value normalisation & alias resolution.  [HYBRID]

Normalises values (dates→ISO, money→amount+currency, durations) — locale-aware,
via libraries — and resolves within-document aliases/coreference ("Company" →
"Acme Holdings Inc."). Cross-document resolution is stage 9b (aggregation/).
"""
