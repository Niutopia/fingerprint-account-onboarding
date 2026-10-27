# Apple Account onboarding

Use this reference only when the target is Apple Account creation or Apple Account post-setup.

## Inputs

Keep these in the run contract rather than this document:

- Apple Account email and authorized credential reference.
- Birth date.
- Account country/region.
- Phone country code and phone number reference.
- MockAddress country slug/URL and optional subdivision.
- Whether the account's marketing checkboxes must be selected.
- Which profile is authorized to be replaced if Apple blocks creation.

The account region, phone code, and address region are independent inputs. Do not derive one from another unless the user explicitly says so.

## Create the account

1. Open the target's create-account URL in the assigned fingerprint browser.
2. Generate one identity per account with `scripts/generate_mockaddress.py` using the configured country and subdivision. Do not handcraft or reuse an address unless instructed.
3. Fill the form in this order or equivalent:
   - Last name and first name from the generated identity.
   - Account country/region from the run contract.
   - Birth date from the account spec.
   - Email and password.
   - Phone country code and phone number from the account spec.
   - Required marketing/terms checkboxes exactly as requested.
4. After selecting a country or phone-country dropdown, wait 3–5 seconds and re-read dependent fields. Some forms asynchronously reset the phone prefix or dependent choices.
5. Enter the image challenge only if the user has supplied the correct value. Otherwise leave the challenge and browser open for the user.
6. Submit once. On success, move to email verification. On failure, inspect the exact target message before trying anything else.

### Human gates

Do not solve or guess:

- image/audio CAPTCHA;
- SMS one-time codes;
- additional identity challenges.

Keep the page open and explicitly tell the user which field or page needs their action. Do not submit repeated guesses. If the target reports an account-creation block such as `Your account cannot be created at this time`, mark the profile blocked and stop.

## Verify email

When the target sends an email verification code and the browser profile is signed into the email account:

1. Open the mailbox in the same profile.
2. Search for the newest target message.
3. Read only the verification code needed for this run.
4. Enter the code with real keyboard events if the form is stateful.
5. Confirm the page advances to phone/identity verification.

Never print the code in the final report.

## Phone verification

The user normally enters the SMS code. The agent may prepare the page and verify that the field is ready, but must not automate the human gate.

If the user says the phone prefix must be `+86`, verify the select still displays `+86 (China mainland)` after the form has settled. If it resets, set it again as the final mutation and re-read it after 4–5 seconds.

## Payment & shipping

After the account reaches the authenticated Payment & Shipping page:

1. Choose `Add a shipping address`.
2. Fill the name, street, city, postal code, and state/province from the same MockAddress identity.
3. Select only the country/region specified in the run contract.
4. If the run requires it, set `Copy billing address from default payment method` **after all text fields are populated**.
5. Verify the checkbox is checked immediately before clicking `Save Changes`.
6. Save and re-open/read the shipping card to confirm the address persisted.

A successful save is not enough; verify the displayed address string on the account page.

## Known failure handling

- If the account is signed out, log in only with the authorized password. A trusted-phone 2FA prompt is a human gate.
- If a browser is signed in as a different account, stop and report the mismatch instead of overwriting the session.
- If the user asks to rebuild a blocked profile, use a fresh fingerprint/provider profile only when capacity allows. Do not keep retrying the same rejected form.
- If the provider creates a mobile fingerprint when the run requires desktop, stop and correct the profile before entering account data.
