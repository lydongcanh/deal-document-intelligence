# Detect language

Work out what language a document is written in, so later stages can pick the
right models. We are multilingual from the start, so this runs early and routes
everything after it.

## What it does

Read the parsed document's text and return the language as an ISO 639-1 code
(for example `en`, `de`, `fr`) with a confidence.

## Why it is its own stage

The language decides which multilingual model and which resources the pipeline
uses downstream. Keeping it as one small, early step means every later stage can
assume the language is known, and we never bake a language assumption into the
parser or the classifier.

## Build or buy

Buy. Language identification is a solved commodity: small, fast, accurate models
already cover 100+ languages. Building our own would be wasted effort and worse
than what exists. We wrap a library behind the `LanguageDetector` interface.

Two common choices:
- lingua: pure Python, bundles its models (no download), strong on short text.
- fastText lid.176: very fast, 176 languages, needs a model file.

For deal documents (long, mostly one language) either works. lingua avoids a
model download, which is convenient given our network constraints. We will pick
one when we implement.

## Input and output

- In: a `ParsedDocument`.
- Out: a `DetectedLanguage` (language code plus confidence).

## Scope for now

Detect one language for the whole document, using the canonical text. Mixed
language documents (for example an English contract with a German annex) can
come later as per-block detection; we keep it simple first.
