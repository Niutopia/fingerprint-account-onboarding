# Recovery and status model

Use one run ledger to make resumptions and handoffs deterministic. Store only masked identifiers unless the user explicitly requires a protected credential file.

## Status model

| Status | Meaning | Allowed next action |
|---|---|---|
| `planned` | Assignment exists, no browser mutation | Preflight and create/select profile |
| `ready` | Profile is prepared and desktop constraints pass | Open target and fill allowed data |
| `awaiting_user_captcha` | Page is waiting for a human image/audio challenge | Hand off; do not guess |
| `awaiting_user_sms` | Page is waiting for a human SMS/OTP | Hand off |
| `email_verified` | Email code accepted | Continue to phone/address |
| `created` | Target confirms account creation | Verify profile and apply post-actions |
| `address_saved` | Shipping address is visible after save | Final audit |
| `blocked` | Target returned a hard block or account mismatch | Stop; replacement only with explicit user direction |
| `error` | Provider/network/local failure | Diagnose without repeated external attempts |

## Replacement rules

A replacement is a new attempt, not a retry loop.

Before replacing:

- Confirm the user asked for a replacement.
- Record the old profile ID/number and reason; close it if requested but do not delete it.
- Recompute external proxy capacity.
- Choose a fresh fingerprint and a different safe IP when possible.
- Do not create more profiles than the provider allows; update an authorized existing profile if the limit is reached.
- After one hard target block on the replacement, stop and report rather than cycling through more profiles.

## Final audit

Verify from page state, not only from logs:

- account exists or target explicitly reports success;
- profile ID/number and masked email mapping;
- egress IP;
- required region and phone prefix;
- address is displayed after save;
- required checkbox was checked before save;
- requested chat/action exists and is in the intended language;
- requested browsers remain open;
- temporary files are removed and persistent account/credential records are protected.

Report unresolved items explicitly. Never say the batch is complete when a profile is blocked, signed into the wrong account, or still waiting for a human gate.
