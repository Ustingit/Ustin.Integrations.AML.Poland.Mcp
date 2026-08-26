# AML Poland MCP

An [MCP](https://modelcontextprotocol.io) server that automates AML/KYB customer due diligence
for Polish accounting firms (*biura rachunkowe*), which are obligated institutions
(*instytucje obowiązane*) under the Polish AML Act (*Ustawa o przeciwdziałaniu praniu pieniędzy
oraz finansowaniu terroryzmu*).

It aggregates the checks a firm is required to run on a new business client — company registry
status, VAT payer status, beneficial ownership, sanctions and PEP screening — into four MCP
tools, and generates the client-facing AML risk assessment card (*Karta Oceny Ryzyka Klienta*)
as Markdown or PDF.

Server code, comments, and this document are in English. Report and tool-response content shown
to the end client defaults to **Polish** and can be switched to **English** per call (see
`language` parameter on every tool).

## Tools

| Tool | Purpose |
|---|---|
| `verify_company_basic` | Registry status (KRS or CEIDG) + VAT payer status and bank accounts (Biała Lista) |
| `fetch_crbr_beneficiaries` | Beneficial owners (UBOs) from the Central Register of Beneficial Owners (CRBR) |
| `screen_sanctions_and_pep` | Screen a person against sanctions lists (EU/UN/OFAC via OpenSanctions, plus the Polish national MSWiA list) and PEP status |
| `generate_aml_risk_card` | Runs the full pipeline and renders the risk card as Markdown and/or PDF |

Plus a resource, `aml://rules/aml-checklist` (Polish) / `aml://rules/aml-checklist/en`, describing
the mandatory due-diligence steps under the Act.

## Data sources and their real-world limitations

Every integration below was verified against the live API/page, not assumed from documentation.
Some have hard limitations that shape the tool's behavior — they're not bugs:

- **KRS** (`api-krs.ms.gov.pl`) — public, no API key. Lookup is by KRS number only; there is no
  NIP-based search. `verify_company_basic` works around this by resolving NIP → KRS via the White
  List response (see below) when the caller only has a NIP.
  **The API redacts representatives' personal data** (e.g. a board member's name comes back as
  `"J*****"`). Full identification must come from the client's own KYC documents, as the Act
  requires anyway — that's what `additional_persons_to_screen` on `generate_aml_risk_card` is for.
- **CEIDG** (sole traders) — requires a JWT bearer token (`AML_CEIDG_API_KEY`); there is no
  anonymous tier. Without a key, `verify_company_basic` skips CEIDG and returns KRS-only results,
  with a note explaining why.
- **Biała Lista / White List (VAT)** (`wl-api.mf.gov.pl`) — public, no API key, rate-limited to
  300 requests/day by the ministry.
- **CRBR** (beneficial owners, `crbr.podatki.gov.pl`) — the public search UI is protected by an
  invisible Google reCAPTCHA v3 token. A request without one is rejected with a generic
  "Niepoprawny NIP" error regardless of whether the NIP is valid. **This server does not attempt
  to solve or bypass that CAPTCHA.** `fetch_crbr_beneficiaries` recognizes that response and
  returns `manual_verification_required` with a link to the official search UI instead. If your
  firm has a licensed CRBR data reseller agreement, point `AML_CRBR_API_BASE` at that provider's
  compliant API.
- **OpenSanctions** (EU/UN/OFAC sanctions + global PEP data) — the hosted API requires an API key
  (`AML_OPENSANCTIONS_API_KEY`, `Authorization: ApiKey <key>`). A self-hosted
  [yente](https://github.com/opensanctions/yente) instance works without one — point
  `AML_OPENSANCTIONS_API_BASE` at it.
- **MSWiA** (Polish national sanctions list) — no API or downloadable file is published; the
  ministry renders it as an HTML table on a gov.pl page. This is scraped directly and cached
  in-process for an hour.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync
cp .env.example .env  # optional: add API keys, override endpoints
```

Run the server (stdio transport, for use with an MCP client like Claude Desktop or Claude Code):

```bash
uv run aml-poland-mcp
```

### Docker

```bash
docker build -t aml-poland-mcp .
docker run --rm -i --env-file .env aml-poland-mcp
```

## Configuration

All settings are environment variables (prefix `AML_`) or a `.env` file — see
[.env.example](.env.example) for the full list with defaults. Nothing is required to run with
public-only data (KRS, White List, MSWiA); `AML_CEIDG_API_KEY` and `AML_OPENSANCTIONS_API_KEY`
unlock CEIDG and OpenSanctions respectively.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src/
```

## Disclaimer

This tool supports the AML risk assessment process; it does not replace the judgment of a
designated AML/compliance officer at the obligated institution. Generated risk cards and their
supporting records must still be retained for 5 years per Art. 49 of the Act — this server does
not persist anything itself.

## License

[MIT](LICENSE)
