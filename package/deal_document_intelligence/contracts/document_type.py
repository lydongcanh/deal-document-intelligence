"""Kind of deal document (detected at stage 3) — routes downstream processing."""

from __future__ import annotations

from enum import StrEnum


class DocumentType(StrEnum):
    NDA = "nda"
    SHARE_PURCHASE = "share_purchase"
    ASSET_PURCHASE = "asset_purchase"
    MERGER = "merger"
    SHAREHOLDERS = "shareholders"
    EMPLOYMENT = "employment"
    LEASE = "lease"
    LICENSE = "license"
    SERVICES = "services"
    DISTRIBUTION = "distribution"
    LOAN = "loan"
    OTHER = "other"
    UNKNOWN = "unknown"
