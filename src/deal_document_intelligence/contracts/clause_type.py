"""Controlled vocabulary of clause types (seeded from CUAD's 41 categories).

Seeded from CUAD because that's the concrete, lawyer-validated taxonomy we have;
it can grow to match Ansarada's own taxonomy later. `UNKNOWN` covers a segmented
clause not (yet) classified into a known type.
"""

from __future__ import annotations

from enum import StrEnum


class ClauseType(StrEnum):
    AFFILIATE_LICENSE_LICENSEE = "Affiliate License-Licensee"
    AFFILIATE_LICENSE_LICENSOR = "Affiliate License-Licensor"
    AGREEMENT_DATE = "Agreement Date"
    ANTI_ASSIGNMENT = "Anti-Assignment"
    AUDIT_RIGHTS = "Audit Rights"
    CAP_ON_LIABILITY = "Cap On Liability"
    CHANGE_OF_CONTROL = "Change Of Control"
    COMPETITIVE_RESTRICTION_EXCEPTION = "Competitive Restriction Exception"
    COVENANT_NOT_TO_SUE = "Covenant Not To Sue"
    DOCUMENT_NAME = "Document Name"
    EFFECTIVE_DATE = "Effective Date"
    EXCLUSIVITY = "Exclusivity"
    EXPIRATION_DATE = "Expiration Date"
    GOVERNING_LAW = "Governing Law"
    INSURANCE = "Insurance"
    IP_OWNERSHIP_ASSIGNMENT = "Ip Ownership Assignment"
    IRREVOCABLE_OR_PERPETUAL_LICENSE = "Irrevocable Or Perpetual License"
    JOINT_IP_OWNERSHIP = "Joint Ip Ownership"
    LICENSE_GRANT = "License Grant"
    LIQUIDATED_DAMAGES = "Liquidated Damages"
    MINIMUM_COMMITMENT = "Minimum Commitment"
    MOST_FAVORED_NATION = "Most Favored Nation"
    NO_SOLICIT_OF_CUSTOMERS = "No-Solicit Of Customers"
    NO_SOLICIT_OF_EMPLOYEES = "No-Solicit Of Employees"
    NON_COMPETE = "Non-Compete"
    NON_DISPARAGEMENT = "Non-Disparagement"
    NON_TRANSFERABLE_LICENSE = "Non-Transferable License"
    NOTICE_PERIOD_TO_TERMINATE_RENEWAL = "Notice Period To Terminate Renewal"
    PARTIES = "Parties"
    POST_TERMINATION_SERVICES = "Post-Termination Services"
    PRICE_RESTRICTIONS = "Price Restrictions"
    RENEWAL_TERM = "Renewal Term"
    REVENUE_PROFIT_SHARING = "Revenue/Profit Sharing"
    ROFR_ROFO_ROFN = "Rofr/Rofo/Rofn"
    SOURCE_CODE_ESCROW = "Source Code Escrow"
    TERMINATION_FOR_CONVENIENCE = "Termination For Convenience"
    THIRD_PARTY_BENEFICIARY = "Third Party Beneficiary"
    UNCAPPED_LIABILITY = "Uncapped Liability"
    UNLIMITED_ALL_YOU_CAN_EAT_LICENSE = "Unlimited/All-You-Can-Eat-License"
    VOLUME_RESTRICTION = "Volume Restriction"
    WARRANTY_DURATION = "Warranty Duration"
    UNKNOWN = "unknown"
