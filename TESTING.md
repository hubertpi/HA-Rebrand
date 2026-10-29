# Validation

Release validation result: **103 Python tests and 7 DOM tests passed**. Ruff lint and format checks
also passed. The test run emitted dependency deprecation warnings from aiohttp
and backoff; no integration test failed. A headless browser could not be
provisioned in the development environment, so no browser visual test is claimed.

## Automated environment

- Python 3.14
- Home Assistant Core 2026.10.4
- Home Assistant frontend 20260930.5
- Linux / aiohttp test server
- Node.js 24 / jsdom 30.1.3 for isolated DOM behavior tests

The tests use the real installed frontend index template, actual Core IndexView,
real Jinja rendering, real Pillow PNG decoding, native HA flow classes and an
isolated aiohttp HTTP server. HA state/executor scheduling are supplied by a
small test harness. These are not full Supervisor or production-instance tests. The DOM tests
execute the actual generated login heading script in jsdom without loading
remote scripts or contacting a production HA instance.

## Coverage

- Default and custom name rendering; the stock logo with no files configured.
- Separate light/dark logo markup, dark-only fallback and custom favicon.
- Attribution visibility enabled/disabled.
- HTML, JavaScript and Jinja injection strings in brand names.
- Changed template markers rejected before applying branding.
- Runtime transformation failure returns the original HTML and logs once.
- PNG validation, oversized input/dimensions, damaged files, animated PNGs,
  metadata stripping, trailing payload removal, missing files, path/URL rejection,
  and file/directory symlink rejection.
- HTTP response through actual IndexView, unchanged authorization route,
  dashboard index responses, and restoration after unload.
- Repeated reloads, duplicate setup rejection, disabled/safe-mode behavior,
  failed setup, development frontend rejection, and later third-party ownership.
- Native initial/options flows, single-entry behavior, clearing old images,
  disabling despite missing assets, and native automatic reload flow type.
- ASCII-only project text scan and code formatting/lint checks.
- Custom logo width bounds and type validation, native numeric selector storage,
  larger defaults for existing settings, natural image proportions, and viewport limits.
- Safe release version syntax, matching changelog notes, section boundaries,
  and standard/high-resolution native integration PNG validation.

## Login-specific coverage

- Native configuration validation and persistence for login heading and width.
- Shared loading logos, independent login light/dark logos, and disabled login settings.
- Shared frontend/login favicon setting, unchanged stock header image when only
  a favicon is configured, and restoration of the original favicon on unload.
- Preservation of stock authorize HTML scripts and the `ha-authorize` component.
- Missing login markers or unfamiliar static handlers rejected before hooks install.
- Installation and restoration on an already-frozen live aiohttp router.
- Unchanged synthetic POST data through login-flow and token API test endpoints.
- Exact original login handler restored, repeated reloads, and third-party ownership.
- Heading text/node identity, later welcome rendering, MFA/error text preservation,
  safe handling of script-like text, no same-heading mutation loop, observer cleanup, and back-forward cache restoration.

The HTTP tests use the real packaged authorize HTML and stock HA file handler.
Auth API endpoints are controlled sentinels, not a production credential flow.
Browser login/MFA should also be verified on the target HA instance.

## Browser validation checklist

The following checks require a running HA instance and a browser; they are not
part of the automated HTTP test harness:

1. Install from HACS; confirm adding and configuring HA Rebrand succeeds.
2. Reload Chrome with Network > Disable cache enabled. Confirm immediate loading
   logo/name and no unwanted stock-logo flash on a slow connection.
3. Test retained cache and a hard reload, then restart Core and retest.
4. Check the foundation toggle and blank-logo fallback.
5. Switch the browser/OS color scheme and inspect both logos.
6. Confirm custom login logo/text appear. Sign in normally and verify MFA if used;
   then disable login branding and confirm the stock login presentation returns.
7. Inspect Network for new third-party requests. This integration should add none.
8. Test a second browser session and the companion app WebView if used.
9. Disable/delete the integration, reload the browser, and confirm stock branding.
10. Check HA logs for new integration errors.

Native mobile splash screens and installed PWA icons are outside this version's
scope. A custom title only persists within the loaded frontend document; tabs
must be reloaded after disabling or removal.
