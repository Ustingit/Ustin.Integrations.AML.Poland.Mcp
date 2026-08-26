"""Client for the Ministry of Finance's "Biała Lista" (White List) VAT taxpayer API.

Endpoint: https://wl-api.mf.gov.pl/api/search/nip/{nip}?date=YYYY-MM-DD
Public, no API key required (rate-limited to 300 requests/day per the ministry's docs).

Also verified: the response includes the subject's KRS number when it has one
(e.g. querying by NIP returns `"krs": "0000028860"`). Since api-krs.ms.gov.pl
only supports lookup *by* KRS number, not by NIP, this is what lets
company_verification.py resolve "I only have a NIP" into a KRS lookup.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from aml_poland_mcp.clients.http import build_client, request_with_retry
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import UpstreamServiceError
from aml_poland_mcp.models import VatStatus

_STATUS_MAP = {
    "Czynny": VatStatus.ACTIVE,
    "Zwolniony": VatStatus.EXEMPT,
}


class WhiteListResult:
    def __init__(
        self, vat_status: VatStatus, bank_accounts: list[str], krs: str | None = None
    ) -> None:
        self.vat_status = vat_status
        self.bank_accounts = bank_accounts
        self.krs = krs


async def check_vat_status(nip: str, settings: Settings) -> WhiteListResult:
    url = f"{settings.white_list_api_base}/nip/{nip}"
    async with build_client(settings) as client:
        response = await request_with_retry(
            client, settings, "GET", url, params={"date": date.today().isoformat()}
        )
    if response.status_code != 200:
        raise UpstreamServiceError(
            "tool.white_list_error", error=f"HTTP {response.status_code}", nip=nip
        )
    return _parse_response(response.json())


def _parse_response(payload: dict[str, Any]) -> WhiteListResult:
    subject = (payload.get("result") or {}).get("subject")
    if subject is None:
        return WhiteListResult(vat_status=VatStatus.NOT_REGISTERED, bank_accounts=[])
    status = _STATUS_MAP.get(subject.get("statusVat", ""), VatStatus.UNKNOWN)
    return WhiteListResult(
        vat_status=status,
        bank_accounts=list(subject.get("accountNumbers") or []),
        krs=subject.get("krs") or None,
    )
