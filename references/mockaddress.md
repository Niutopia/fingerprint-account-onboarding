# MockAddress integration notes

Use `https://mockaddress.com/` as the address source when the run requests generated identity/address data.

## Page selection

The site's country paths are slugs, not necessarily ISO codes:

- Japan: `jp-address`
- United States: `usa-address` (not `us-address`)
- United Kingdom: `uk-address`
- Hong Kong: `hk-address`

Read the current country links from the MockAddress home page if a slug is unknown, or pass the exact country page with `--url`.

## Script

```bash
python scripts/generate_mockaddress.py \
  --country <slug> \
  [--subdivision "<state/province/prefecture>"] \
  --count <count> \
  --output <project>/.cache/<run-id>/mockaddress.json
```

The script:

- opens the country page in an isolated helper browser;
- optionally selects a subdivision by visible option text;
- clicks `生成地址` / `Generate Address`;
- waits for a changed `#address-result`;
- reads current `[data-field][data-copy]` values;
- rejects duplicate records and exits non-zero on ambiguity or missing fields.

Known field keys include `lastName`, `firstName`, `gender`, `phone`, `zip`, `street`, `city`, `state`, `county`, `email`, and `fullAddress`.

## Operational rules

- Treat generated emails and phone numbers as generated test data, not contacts for real outreach.
- Do not submit generated data to a service unless the user has explicitly supplied that target and its region.
- Generate a fresh identity per account when the run schedule says so.
- Store the chosen identity in the run ledger only if the user needs it for later completion; do not scatter copies across the workspace.
- Remove temporary browser caches and test output from `.cache/` when the run is complete.
