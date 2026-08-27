# AML Poland MCP

*Five registries. One prompt.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MCP server](https://img.shields.io/badge/MCP-server-6b46c1)

A Polish accounting firm (*biuro rachunkowe*) is an obligated institution under the Polish AML
Act — same legal category as a bank, just smaller. Before onboarding any client it must check the
company register, VAT status, beneficial ownership, and sanctions/PEP lists, then produce and
file a documented risk assessment. Done by hand, that's five different registries, most of them
across separate tabs, and realistically **60–90 minutes per client** if you do it properly.

**AML Poland MCP** puts all five checks behind an AI assistant. Ask once, get back registry
status, VAT status, beneficial owners, sanctions/PEP screening, and a signable AML risk card
(Markdown or PDF) — sourced live from KRS, CEIDG, the Ministry of Finance's White List, CRBR, and
sanctions lists, not a cached copy.

- **For an independent accounting firm** — install it once in Claude Desktop or Claude Code; every
  new client afterwards is one prompt instead of a half hour of clicking through registries.
- **For an accounting-software vendor** — the code is MIT-licensed and embeddable as an
  integration inside a platform like Comarch Optima, inFakt, or wFirma.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/). Clone the repo, then point your MCP client at it.

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "aml-poland": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/Ustin.Integrations.AML.Poland.Mcp", "run", "aml-poland-mcp"]
    }
  }
}
```

**Claude Code**, from inside the repo:

```bash
claude mcp add aml-poland -- uv run aml-poland-mcp
```

That's it for public-data checks (KRS, White List, MSWiA) — no API keys needed. See
[Configuration](#configuration) below to unlock CEIDG and international sanctions screening.

## Example

```
> Check client NIP 7740001454 for AML and generate a risk card.

Checking the court register, the VAT list, the beneficial-owners registry, and
sanctions lists. Here's the summary:

  Name              ORLEN SPÓŁKA AKCYJNA
  Registry status   Active
  VAT status        Active payer
  Beneficial owners manual check required (CAPTCHA)

  Risk level        Medium
  Procedure         Standard due diligence
  Document          risk_card.pdf
```

The numbers and statuses above are real — this is what `generate_aml_risk_card` actually returned
for that NIP, checked live against the public registries; the surrounding chat framing is
illustrative.

## Tools

| Tool | Purpose |
|---|---|
| `verify_company_basic` | Registry status (KRS or CEIDG) + VAT payer status and bank accounts (Biała Lista) |
| `fetch_crbr_beneficiaries` | Beneficial owners (UBOs) from the Central Register of Beneficial Owners (CRBR) |
| `screen_sanctions_and_pep` | Screen a person against sanctions lists (EU/UN/OFAC via OpenSanctions, plus the Polish national MSWiA list) and PEP status |
| `generate_aml_risk_card` | Runs the full pipeline and renders the risk card as Markdown and/or PDF |

Plus a resource, `aml://rules/aml-checklist` (Polish) / `aml://rules/aml-checklist/en`, describing
the mandatory due-diligence steps under the Act.

Server code, comments, and this document are in English. Report and tool-response content shown
to the end client defaults to **Polish** and can be switched to **English** per call (see the
`language` parameter on every tool).

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

## Running standalone

For development, or to run the server outside an MCP client's own process management:

```bash
uv sync
cp .env.example .env  # optional: add API keys, override endpoints
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

## Adopters

Using AML Poland MCP at your firm or inside your product? Open a PR adding yourself below —
genuinely happy to hear how it's being used.

*(nobody yet — be the first)*

## Disclaimer

This tool supports the AML risk assessment process; it does not replace the judgment of a
designated AML/compliance officer at the obligated institution. Generated risk cards and their
supporting records must still be retained for 5 years per Art. 49 of the Act — this server does
not persist anything itself.

## License

[MIT](LICENSE)
