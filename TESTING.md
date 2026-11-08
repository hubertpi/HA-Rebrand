# Validation

Current validation result: **141 Python tests and 8 DOM tests passed**. Ruff lint and format checks
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
- Shared frontend/login brand title, safe title escaping, and unchanged logo
  placement after title replacement.
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

## Android and mobile icon coverage

- Real generated PNG size/content-hash checks, deterministic URLs, and changes
  to the URL when pixels change.
- Proportion-preserving padding for wide logos and independent PWA/favicon sources.
- Manifest name/icons updated through native HA helpers, with app identity,
  start URL, scope, theme and unrelated fields preserved.
- Exact restoration of owned manifest fields, preservation of later changes,
  and public icon responses becoming unavailable after unload.
- Native HA view registration, anonymous PNG GET, rejected POST/arbitrary names,
  image MIME/nosniff/cache headers, and idempotent route registration.
- Live frontend/login icon URLs, touch links, manifest JSON and icon downloads.

These are server/DOM tests; they do not simulate Android's OS splash or Chrome's
installed-web-app update schedule. Those need testing on the target device.

## HTML5 secondary-image suppression

- Actual Core 2026.10.4 legacy, generic and HTML5-specific payload builders with
  outbound push mocked. Missing icons use the transparent default.
- Explicit icons, badges, pictures, action buttons, click URLs and dismiss calls
  are preserved. With no favicon, the badge default is unchanged. With a favicon,
  all three native send paths receive the generated white silhouette. Transparent
  cutouts and flat-background removal are checked separately.
- Public PNG decodes as 96 by 96 with zero alpha for every pixel. Unload returns
  404 for its URL.
- HTML5 loading after Rebrand, import/unload races, repeated reloads, setup
  failure/cancellation and unfamiliar-helper compatibility checks.
- Installed-app icon, favicon and login tests remain separate.
- Real Android rendering and any space reserved for the transparent image remain
  device checks. No notification visual result is claimed from Python tests.

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

The native Companion app splash/icon is outside this version's scope.
Android's installed web app splash uses manifest branding, but Android controls
its layout and Chrome controls installed-icon refresh. A custom title only persists within the loaded frontend document; tabs
must be reloaded after disabling or removal.

The 0.1.10 app-icon change was also checked against the reported transparent
white artwork: the old icon flattened to an almost-white square; the new app
icons have an opaque dark background. Automated checks cover contrast, alpha,
maskable safe-zone containment and unchanged favicon transparency. Actual
Samsung notification rendering and installed-icon refresh remain device checks.

A post-release HTTP test loads a transparent white source through the integration,
fetches the native `/manifest.json`, then fetches every advertised installation
PNG. It verifies opaque alpha, dark backing, white artwork and content-addressed
URLs for both ordinary and maskable icons. The favicon remains transparent.
The runtime correction is already in 0.1.10; this test adds coverage without a
new runtime release.

Chrome's WebAPK adaptive-icon resource uses a white background behind the
maskable artwork:
https://github.com/chromium/chromium/blob/main/chrome/android/webapk/shell_apk/res/mipmap-anydpi-v26/ic_launcher.xml

Using the reported source PNG, both 0.1.8 installation icons lost all pixels with
an RGB channel below 200 when composited onto white. The 0.1.10 icons retained
contrasting pixels in every advertised size and purpose. This reproduces an
asset-level failure, not a verified rendering of the user's installed APK.


## Notification interruption review (2026-11-08)

Additional resilience checks passed with real Core HTML5 payload construction
and mocked outbound push:

- 250 concurrent sends complete without a shared lock or reordered image URLs.
- A failed push is followed successfully by another send through the same hook.
- A held network push does not prevent a second send completing independently.
- The generated frontend title observer settles after 100 dashboard title
  updates; the test does not include other integrations' scripts.

The wrapper does not change snapshot URLs, TTL, urgency, registrations, signing,
service-worker source, or snapshot HTTP cache headers. No server-side deadlock
or self-sustaining title-observer loop was reproduced. These checks do not
establish that Chrome/Android notification delivery cannot stall.

A remaining browser-side risk is the added network dependency for the generated
notification icon and badge PNG URLs. Chromium loads notification image, icon
and badge resources before displaying the notification, with a 90-second image
fetch timeout in the reviewed current source. Slow/unreachable branding URLs
could therefore delay even a notification without a doorbell photograph.
This is a plausible display-delay mechanism, not confirmation of the reported
persistent interruption or proof that it freezes the entire web app.

Sources reviewed:
- https://github.com/chromium/chromium/blob/main/third_party/blink/renderer/modules/notifications/notification_resources_loader.cc
- https://github.com/chromium/chromium/blob/main/third_party/blink/renderer/modules/notifications/service_worker_registration_notifications.cc

This review adds tests and documentation only; it does not change the 0.1.12
runtime or publish a speculative runtime fix. A controlled test with Rebrand
disabled and Core restarted is needed to isolate its effect on the phone.
