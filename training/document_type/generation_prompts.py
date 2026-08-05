"""Prompt registry for synthetic document generation (v1 pilot classes + `other`).

TEMPLATE layer only: a future generation runner samples the diversity axes, renders a
prompt per document, and calls an LLM. Prompts are versioned data so runs are
auditable: `prompt_id()` is a content hash, so a stored `prompt_id` reproducibly
identifies the exact rendered prompt.

BEFORE BULK generation (not needed for the disposable smoke test), this must grow:
multiple independent prompt families per non-`other` class, shuffled/optional sections,
explicit hard-confusion pairs, and a runner that samples axes and enforces the
duplication/shortcut thresholds. v1 is single-family per class, which is fine only for
the throwaway smoke test.
"""

from __future__ import annotations

from pydantic import BaseModel

from preprocessing import sha256

REGISTRY_VERSION = "doctype-prompts-v1"

# Diversity axes the runner samples per document, to fight template collapse.
JURISDICTIONS = ["England & Wales", "Delaware USA", "New York USA", "Australia", "Singapore"]
LENGTHS = ["short (1-2 pages)", "medium (3-6 pages)", "long (8-15 pages)"]
REGISTERS = ["formal legal", "plain-English modern", "dense traditional boilerplate"]
# Mostly Markdown, with a plain-text and degraded minority (matches the input plan).
FORMAT_WEIGHTS = {"markdown": 0.6, "plain": 0.25, "noisy_markdown": 0.15}
_FORMAT_INSTRUCTION = {
    "markdown": "Markdown with `#` headings, and tables as `| ... |` where natural.",
    "plain": "plain text only, no Markdown formatting or heading markers.",
    "noisy_markdown": (
        "Markdown but imperfect, as if from an OCR/parser: some broken headings, stray "
        "line breaks, and minor artifacts."
    ),
}

# `other` must be HARD: mostly near-domain documents that could be mistaken for a
# supported class, with easy non-legal negatives a minority.
OTHER_FAMILIES = [
    "a corporate policy (code of conduct, data-protection or expenses policy)",
    "an employee benefit or pension plan document",
    "an IP registration certificate (granted patent or trademark)",
    "a purchase order or an invoice",
    "a routine regulatory filing cover or annual-return receipt",
    "another legal record outside our taxonomy (court docket sheet, power of attorney)",
    "an unrelated non-legal document (news article, product manual, recipe)",  # easy, minority
]


class ClassPrompt(BaseModel):
    label: str  # one of MODEL_LABELS
    summary: str
    sections: list[str]
    realism: list[str]


PROMPTS: dict[str, ClassPrompt] = {
    "nda": ClassPrompt(
        label="nda",
        summary="confidentiality / non-disclosure agreement between two parties",
        sections=[
            "definition of Confidential Information", "permitted use", "exclusions",
            "term and survival", "return/destruction", "remedies", "governing law",
        ],
        realism=["mutual or one-way variants", "a defined-terms section"],
    ),
    "commercial_agreement": ClassPrompt(
        label="commercial_agreement",
        summary="commercial contract between a supplier/vendor and a customer (services, supply, distribution)",
        sections=[
            "scope of services/goods", "pricing and payment", "term and termination",
            "warranties", "limitation of liability", "IP ownership", "governing law",
        ],
        realism=["schedules/annexes for pricing or SOW", "order-of-precedence clause"],
    ),
    "constitutional": ClassPrompt(
        label="constitutional",
        summary="company constitutional document (articles of association / bylaws)",
        sections=[
            "share capital and classes", "transfer of shares", "directors and powers",
            "general meetings and voting", "dividends", "pre-emption rights",
        ],
        realism=["article/section numbering", "references to the Companies Act or DGCL"],
    ),
}


def render(
    label: str, jurisdiction: str, length: str, register: str, fmt: str, other_family: str | None = None
) -> str:
    """Build the full generation prompt for one document from sampled axes."""
    lines = [
        f"Jurisdiction: {jurisdiction}. Length: {length}. Register: {register}.",
        f"Output format: {_FORMAT_INSTRUCTION[fmt]}",
        "",
    ]
    if label == "other":
        family = other_family or OTHER_FAMILIES[0]
        lines[:0] = [
            f"You are generating ONE synthetic {family} for the OUT-OF-TAXONOMY (`other`) "
            "class of a deal-document classifier's TRAINING set.",
            "It must NOT be any deal/contract type (NDA, commercial, acquisition, lease, "
            "financing, IP, employment, constitutional, financial, etc.); it should be a "
            "realistic document that could be mistaken for one but is not.",
        ]
    else:
        spec = PROMPTS[label]
        lines[:0] = [
            f"You are generating ONE synthetic {spec.summary} for a document-type "
            "classifier's TRAINING set.",
        ]
        lines.append("Include, where natural: " + "; ".join(spec.sections) + ".")
        lines += [f"- {r}" for r in spec.realism]

    lines += [
        "",
        "Realism rules:",
        "- Use realistic party names, dates, defined terms, cross-references, boilerplate.",
        "- Vary whether an explicit title naming the document is present; do not make the "
        "class obvious from a single title line alone.",
        "- Do not mention that this is synthetic or reference these instructions.",
        "",
        "Return ONLY the document text.",
    ]
    return "\n".join(lines)


def prompt_id(label: str, rendered: str) -> str:
    """Reproducible id for a rendered prompt: registry version + content hash."""
    return f"{REGISTRY_VERSION}:{label}:{sha256(rendered)[:16]}"
