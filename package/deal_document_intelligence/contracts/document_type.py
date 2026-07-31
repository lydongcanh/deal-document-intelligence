from __future__ import annotations

from enum import StrEnum


class DocumentType(StrEnum):
    """Kind of deal document"""

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
