"""Company verification orchestration for `verify_company_basic`.

Resolves a NIP and/or KRS number into one CompanyBasicInfo by combining three
independent registries:

1. White List (by NIP) -- gives VAT status, bank accounts, and (verified
   against the live API) the subject's KRS number if it has one.
2. KRS (by KRS number only -- the public API has no NIP-based lookup, which
   is why step 1 matters even when the caller only has a NIP).
3. CEIDG (by NIP) as a fallback for sole traders, who have no KRS entry.
"""

from __future__ import annotations

from aml_poland_mcp.clients import ceidg_client, krs_client, white_list_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import AmlError, NotFoundError
from aml_poland_mcp.models import CompanyBasicInfo
from aml_poland_mcp.validators import require_valid_krs, require_valid_nip

SkippedSource = tuple[str, dict[str, str]]


async def verify_company(
    settings: Settings, *, nip: str | None = None, krs: str | None = None
) -> tuple[CompanyBasicInfo, list[SkippedSource]]:
    if not nip and not krs:
        raise NotFoundError("tool.missing_identifier")

    nip = require_valid_nip(nip) if nip else None
    krs = require_valid_krs(krs) if krs else None
    skipped: list[SkippedSource] = []

    vat_status = None
    bank_accounts: list[str] = []
    if nip:
        white_list = await white_list_client.check_vat_status(nip, settings)
        vat_status, bank_accounts = white_list.vat_status, white_list.bank_accounts
        krs = krs or white_list.krs

    company: CompanyBasicInfo | None = None
    if krs:
        company = await krs_client.fetch_company_by_krs(krs, settings)

    if company is None and nip:
        try:
            company = await ceidg_client.fetch_company_by_nip(nip, settings)
        except AmlError as exc:
            skipped.append((exc.translation_key, _stringify(exc.params)))

    if company is None:
        raise NotFoundError("tool.company_not_found", identifier=krs or nip or "")

    if vat_status is not None:
        company.vat_status = vat_status
        company.bank_accounts = bank_accounts

    if any("*" in rep.first_name or "*" in rep.last_name for rep in company.representatives):
        skipped.append(("tool.krs_names_masked", {}))

    return company, skipped


def _stringify(params: dict[str, object]) -> dict[str, str]:
    return {k: str(v) for k, v in params.items()}
