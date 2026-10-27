---
name: fingerprint-account-onboarding
description: Run authorized multi-account onboarding through a configurable fingerprint browser, including proxy-capacity preflight, region-aware MockAddress identity generation, human verification gates, account/address verification, and restrained warm-up. Use when an operator supplies a provider, region, account batch, and explicit authorization; do not use for generic browser automation.
metadata:
  short-description: Configurable fingerprint-browser account onboarding
---

# Fingerprint Account Onboarding

Run a controlled, auditable onboarding batch for accounts the user is authorized to manage. The workflow is provider-agnostic and region-agnostic: do not hardcode the fingerprint-browser vendor, fingerprint profile, proxy, country, locale, phone prefix, address, or target service.

## Required run contract

Before creating or changing anything, establish:

- Fingerprint-browser provider and any local API or CDP endpoint.
- Explicit authorization for the account/email batch and target services.
- Account-to-profile mapping and which profiles are reusable versus blocked.
- Proxy-capacity source, per-IP limit, and projected usage.
- Country/region, locale, timezone, phone country code, and target-service region.
- MockAddress country slug or URL, plus an optional subdivision filter.
- Which verification steps the user will perform (normally CAPTCHA and SMS/OTP).
- Requested post-actions, such as shipping address, required checkboxes, or warm-up chat.
- Credential reference strategy. Do not put secrets in this skill or in chat summaries.

If a value is not supplied and materially changes the result, ask for it. Never infer a country, phone prefix, billing address, or fingerprint type from the current workspace by accident.

`assets/account-spec.example.json` is a safe input skeleton. Treat `*_ref` fields as references to environment variables or protected files, never as literal credentials.

## Non-negotiable checks

1. **Use the configured provider.** Prefer its local API/CDP interface over GUI automation. Do not silently switch to another browser or vendor.
2. **Fingerprints are configurable, the constraints are not.** Allow provider-generated or newly created fingerprints, but validate the run's requirements before use. If the run requires a desktop environment, reject mobile UA/viewport fingerprints and rebuild or choose another profile.
3. **Use the external proxy pool as capacity truth when specified.** Count existing consumers from that pool, then add expected new usage. Do not substitute the fingerprint browser's attachment count for the external pool bound count.
4. **Stop at human gates.** Never solve image CAPTCHAs, audio CAPTCHAs, or SMS/OTP codes on the user's behalf. Fill the page up to the challenge, keep it open, and hand off. Do not brute-force or repeatedly retry a rejected challenge.
5. **Stop on hard platform blocks.** If the target says an account cannot be created or is rate-limited, record the state and stop that profile. A replacement profile or proxy requires explicit user authorization and must pass capacity checks.
6. **Protect credentials and personal data.** Keep secrets in project `.secrets/` with mode `0600` or in environment variables. Mask identifiers in logs and final reports.
7. **Keep requested resources open.** Do not close a profile, session, or browser if the user asked it to remain open. Preserve blocked profiles unless deletion is explicitly authorized.

## Workflow

### 1. Preflight

- Read the provider's profiles/proxies and the run's external proxy-capacity source.
- Calculate projected usage for every affected exit IP:

```bash
python scripts/check_ip_capacity.py usage.json --limit <per-ip-limit>
```

- Fail before creation if any exit would exceed the limit.
- Resolve workspace-specific safety rules (for example local-only tests and no extra production load) before touching a remote system.
- Write a run ledger with profile ID/number, account reference, exit IP, and status.

### 2. Prepare profiles

- Create or select profiles through the configured provider adapter.
- Prefer newly generated fingerprints unless the user fixes a fingerprint.
- After starting, validate any desktop requirement:

```bash
python scripts/validate_desktop_cdp.py --ws <cdp-websocket> --min-width 900
```

- Verify the actual egress IP matches the intended assignment.
- Restore any provider-stored credentials after temporary login workarounds.
- Never reuse a profile that has a hard platform block without explicit instruction.

### 3. Generate address data

When the run asks for generated addresses, use MockAddress rather than inventing an address:

```bash
python scripts/generate_mockaddress.py \
  --country <mockaddress-country-slug> \
  [--subdivision "<state/prefecture>"] \
  --count <number-of-identities> \
  --output <project>/.cache/<run-id>/mockaddress.json
```

The country slug and subdivision are runtime inputs. Keep the generated identity tied to the account record. Do not reuse a generated address across accounts unless the user asks.

### 4. Complete authorized onboarding

Follow `references/apple-account-workflow.md` when the target is Apple Account. Follow the provider contract in `references/provider-adapters.md` for browser creation and CDP access.

- Use actual field values from the run contract and MockAddress output.
- After changing a region/phone dropdown, wait for dependent fields to settle, then re-read them before submission.
- Preserve user-requested checkbox states.
- At a CAPTCHA or OTP page, stop, keep the browser open, and hand control to the user.
- Verify success from the authenticated account page, not only from a toast or redirect.

### 5. Apply post-actions

For shipping addresses, use the address generated for that account. If the user requires `Copy billing address from default payment method`, set it as the final form action and verify it is checked before saving.

For optional warm-up chat, send one short, natural prompt per account using the requested language and topics. Default to 2–3 sentences, sequential operation, human-like input delay, and at least roughly 20 seconds between accounts. Do not flood or parallelize.

Do not change unrelated settings, including Google preferred-language settings, unless the run explicitly includes them.

### 6. Verify and close out

- Read back account existence, mapped profile, exit IP, address, required checkbox state, and requested post-action state.
- Report masked account identifiers only.
- Leave requested browsers open.
- Remove temporary screenshots, OCR/model assets, downloaded runtimes, and caches under the project `.cache/`.
- Preserve source code, account records, credentials, backups, and any explicitly requested persistent profiles.

## References

- `references/provider-adapters.md`: provider-neutral adapter contract and a tested AdsPower example.
- `references/apple-account-workflow.md`: Apple-specific field order, dynamic defaults, human gates, and shipping-address checks.
- `references/mockaddress.md`: country-slug handling, DOM fields, uniqueness, and cleanup rules.
- `references/recovery-and-status.md`: replacement rules, status model, and final audit checklist.

Read only the references relevant to the active run.
