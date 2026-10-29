# Security design

This is a frontend customization, not an authentication or security component.

- No network client, telemetry, remote import, subprocess, external executable,
  configuration API, WebSocket endpoint, or token access exists in the integration.
- One public read-only icon endpoint serves only generated in-memory PNGs for
  active branding. It cannot read arbitrary filenames, receive uploads, change
  settings, return source files, or expose credentials. Unknown/inactive icons
  return 404; non-GET methods are not registered.
- Native HA config entry/options flows manage settings with HA's own access
  controls. There is no separate configuration API to secure.
- The integration reads only simple PNG basenames from a dedicated directory
  inside the configuration directory. It rejects paths and URLs and opens both
  the asset directory and final file with Linux no-follow flags.
- Only regular files are accepted. Input size is bounded before decoding and
  dimensions before pixel loading. Pillow, already required by Core, verifies
  and decodes PNGs; output is generated from a fresh pixel image. Metadata,
  animation, embedded profiles and trailing payloads are not copied.
- Both original and re-encoded files are capped at 2 MiB. Each dimension is
  capped at 2048 pixels. Animated PNGs and SVGs are rejected.
- Names are HTML escaped and JSON serialized for their separate output contexts.
  Script literals escape HTML delimiters. Settings are inserted only after the
  original Jinja template has finished rendering.
- No credentials are read or logged. Branding is public index content, so it
  must not contain secrets.
- Source code, metadata, documentation and supplied interface strings are
  English-only. Language is not used as a substitute for a source/security review.

## Trust boundary

Custom integrations execute inside HA Core with its permissions. Install only
code you trust. This implementation minimizes its own operations but does not
sandbox itself or other custom components. Local administrators who can replace
asset files or Python source are already trusted HA administrators.

## Known compatibility risk

The instance template cache and static login route handler slot are private HA APIs. A future frontend/Core update can
require an integration update. Guards reject changed markers at setup, runtime
failure falls back to original HTML, and unload restores the previous template.
See COMPATIBILITY.md for both exact hooks and the recovery path.

## Reporting a problem

Open an issue at https://github.com/hubertpi/HA-Rebrand/issues with versions and
sanitized logs. Do not post tokens, passwords, full `.storage` files or private
HA configuration. For a security issue, describe the affected behavior without
posting working credentials or other private data.

## Login branding boundary

Login branding changes presentation of the existing public static login page.
It does not introduce an authentication implementation. Its wrapper calls the
known stock file handler and only adapts that successful login HTML response.
All stock bootstrap scripts and components remain present. No login flow,
provider or token API is intercepted, and no form data, token, redirect query,
credential or cookie is read by the integration.

The configurable heading is JSON serialized with HTML delimiters escaped,
then applied as text to the existing welcome text node. It never becomes
markup. MFA prompts, errors and authentication-provider warnings remain stock.
An isolated DOM test checks attempted script injection and retention of the
existing nodes. A live aiohttp test checks the frozen router, original route
object, unchanged synthetic POST payloads to auth APIs, and exact restoration.

These tests validate presentation isolation; they are not a complete end-to-end
security audit of Home Assistant's authentication system.

## Browser and installed-web-app icons

Browsers and Android installers need to fetch public icons without a logged-in
HA session. `/api/ha_rebrand_local/icon/{content-hash}.png` therefore deliberately
uses `requires_auth = False`. The lookup key only selects precomputed PNG bytes
in the active runtime dictionary; it is never used as a filesystem path. The
response uses image/png and nosniff. Its cache lifetime is long because its URL
is a SHA-256 hash of the exact bytes; pixel changes generate a different URL.

Icons are resized/padded in an executor from the already validated local PNGs.
No new image files are written and no arbitrary remote image is fetched. Treat
these pixels and the manifest brand name as public, just like the loading page.
On disable/removal, the endpoint returns 404 and owned manifest fields are
restored. Browser/device caches can still retain old icons until refreshed or
an installed shortcut is recreated.

PWA branding uses HA's public `frontend.add_manifest_json_key` helper for name,
short_name and icons only. The existing app id, start URL, scope, theme metadata,
permissions and unrelated manifest fields are preserved. A later third-party
change to an owned field is not overwritten during cleanup.
