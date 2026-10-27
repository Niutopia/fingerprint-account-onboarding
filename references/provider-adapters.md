# Provider adapters

The workflow must work with any fingerprint browser that exposes a supported local API/CDP path. Implement a thin adapter with the contract below; do not put provider-specific assumptions in the main workflow.

## Adapter contract

```text
create_profile(spec) -> {profile_id, profile_no}
start_profile(profile_id, headless, keep_tabs) -> {cdp_ws, debug_port}
active_profile(profile_id) -> {status, cdp_ws}
stop_profile(profile_id) -> ok
list_profiles() -> [{profile_id, profile_no, name, proxy_ref, status}]
list_proxies() -> [{proxy_id, host, port, label, exit_ip}]
```

Required adapter behavior:

- Return a stable CDP/webdriver endpoint after launch.
- Preserve browser state when a profile is stopped unless deletion is explicitly requested.
- Distinguish profile creation failure, launch failure, and target-site account block.
- Put provider-specific response parsing in the adapter, not the runbook.

## AdsPower tested example

This is an example adapter, not a requirement to use AdsPower.

### Authentication

```http
Authorization: Bearer <value from an environment variable or .secrets file>
```

Never place the key in a skill, command echo, repository file, or final report.

### Example endpoint map

| Operation | Method | Path |
|---|---|---|
| List profiles | GET | `/api/v1/user/list?page=1&page_size=100` |
| Create profile v2 | POST | `/api/v2/browser-profile/create` |
| Update profile v2 | POST | `/api/v2/browser-profile/update` |
| Start profile v2 | POST | `/api/v2/browser-profile/start` |
| Active/state v2 | GET | `/api/v2/browser-profile/active?profile_id=<id>` |
| Stop profile v2 | POST | `/api/v2/browser-profile/stop` |
| List proxy library | POST | `/api/v2/proxy-list/list` |

Confirm endpoints against the installed provider version before a batch. Do not assume an API path from another machine.

### Minimal create payload

```json
{
  "name": "<run>-<account-key>",
  "group_id": "0",
  "platform": "google.com",
  "username": "<account email>",
  "password": "<injected from a protected secret source>",
  "proxyid": "<provider-proxy-id>",
  "fingerprint_config": {
    "automatic_timezone": "1",
    "language": ["en-US", "en"],
    "flash": "block",
    "fonts": ["all"],
    "webrtc": "proxy",
    "scan_port_type": "1",
    "screen_resolution": "1440_900",
    "hardware_concurrency": "8",
    "device_memory": "8",
    "browser_kernel_config": {"type": "chrome", "version": "latest"}
  }
}
```

Do not write a real password into a script or example file. The adapter should read it from a protected source and send it only to the configured provider.

Fingerprint fields are intentionally not pinned. If the run requires desktop, set or validate a desktop UA/viewport after the provider finishes generating the profile. A mobile UA is a hard failure for that run.

### Launch settings observed to matter

- Launch in visible/headful mode when a human will solve a CAPTCHA or OTP.
- Use the provider's CDP websocket; attach with Playwright or another CDP client.
- Do not use a second unrelated browser as a fallback unless the user explicitly changes the provider.
- After launch, verify the real exit IP through the browser, not only the provider's stored proxy label.
- `browser_kernel_config.version` may accept `latest` for updates even when `ua_auto` is rejected by a particular API version; verify the returned UA.

## Provider profile replacement

When the user explicitly asks to redo a blocked environment:

1. Keep the old profile closed and recorded; do not delete it.
2. Recalculate external proxy usage before assigning a new exit.
3. Prefer a fresh profile/fingerprint over reusing a blocked session.
4. If the provider has a profile-count limit, update an authorized existing profile as a full reset instead of creating past the limit.
5. Do not perform repeated replacements without user direction; a hard target block is a stopping condition.
