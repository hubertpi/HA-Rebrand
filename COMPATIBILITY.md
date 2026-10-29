# Compatibility notes

## Examined sources

- Home Assistant Core tag `2026.10.4`,
  `homeassistant/components/frontend/__init__.py`:
  https://github.com/home-assistant/core/blob/2026.10.4/homeassistant/components/frontend/__init__.py
- That release's frontend requirement is `home-assistant-frontend==20260930.5`:
  https://github.com/home-assistant/core/blob/2026.10.4/homeassistant/components/frontend/manifest.json
- The corresponding loading HTML:
  https://github.com/home-assistant/frontend/blob/20260930.5/src/html/index.html.template
- Native config/options APIs were checked against the same Core release.
  That release uses `probatio` for schemas and `OptionsFlowWithReload` for
  automatic options reloads.

## Loading template hook

`IndexView.get()` reads `_template_cache` before invoking `get_template()`.
This integration primes the original cache in an executor, verifies a rendered
copy, and replaces that single instance's cache with a `jinja2.Template`
subclass. Its `render()` delegates to the original before applying branding.

The original render cache keys include the template object. Installing or
restoring a different template object consequently selects a different cached
response without clearing the global render cache or changing other integrations.

The hook is intentionally limited to the standard packaged frontend. Frontend
development repositories are rejected. No class method, router collection,
authentication API view, or HA package file is changed.

## Login presentation hook

The standard frontend registers GET `/auth/authorize` as a partial of HA's
`http.server._serve_file` pointing to the packaged `authorize.html` file. When
login branding is enabled, HA Rebrand verifies that exact handler type and path,
loads and validates the stock HTML in an executor, and wraps the existing
route's `_handler` slot. It does not remove/re-register the route or modify the
router's resource collections. The original handler is invoked first for each
request. Only an unprepared, successful FileResponse for the known login HTML
is adapted; other responses are returned unchanged.

The HTML adapter retains every stock script and the `ha-authorize` component.
It replaces the header image when a custom logo is available and appends a
small local inline heading observer. The observer changes only the text node
containing the English `Welcome home!` message inside `ha-auth-flow h1`.
It preserves Lit's comment markers and text-node identity. MFA headings, errors,
provider warnings and form fields are not rewritten. Non-English welcome
messages remain stock in this version.

Login HTML is served with `Cache-Control: no-store` so removed or changed
branding does not remain in a cached login document. Static file range and
conditional-cache validators are omitted for this transformed presentation page.
The stock authentication providers, login flow, token APIs, request bodies,
redirect parameters, cookies and authentication checks are not inspected or
changed by the adapter. No authentication API handler is wrapped.

The private `_handler` slot and `_serve_file` identification are compatibility
sensitive. Setup rejects an unfamiliar handler before installing either hook.
Unload restores the exact original handler only while HA Rebrand still owns
the slot, and preserves a later third-party replacement with a restart warning.
Disable **Enable login branding** to use the original static login handler while
keeping loading screen branding.

## Expected HTML structure

The adapter checks for `#ha-launch-screen`, the known stock loading image with
class `ha-logo`, the initial Home Assistant document title, and the following
`home-assistant` element. Hiding attribution also requires the known `ohf-logo`
class. It replaces only the matched loading image and initial title, adds a
name below the logo, and appends scoped styles in the head.

A layout change that removes these markers makes setup fail with a clear error
before applying branding. If a transformation unexpectedly fails after setup,
the original HTML is returned. This guard is not a promise that every future
frontend layout retaining the same markers will look correct.

The supported loading logo is an image referencing
`/static/images/home-assistant-logo-loading.svg`.

## Cleanup and concurrent customization

The original template object is retained. Unload restores it only if the current
cache still points to our wrapper. Repeated reloads therefore do not nest
wrappers. If a later integration takes ownership, HA Rebrand warns rather than
overwriting that component; a Core restart clears the remaining in-memory hooks.

Avoid running multiple integrations that customize the index HTML at once.
Open browser documents require reloading after changes or removal.

## Limits

Only Core 2026.10.4 / frontend 20260930.5 has been tested automatically. No claims
are made yet for 2026.11 beta versions, frontend development builds, companion
app native splash screens, reverse-proxy HTML rewriting,
or arbitrary third-party themes. Separate light/dark images follow the browser
color preference available before HA startup.

## Android and web app manifest

The public `frontend.add_manifest_json_key` helper updates HA's existing web app
manifest name, short_name and icons. No manifest route is replaced. Original
values are retained and restored only while the field still equals our installed
value. HA's app id, start URL, scope, theme fields and other metadata remain intact.

The icon source is the explicit web app icon, then favicon, then a loading logo.
The integration produces 192/512 pixel square icons with transparent padding,
marked purpose any rather than maskable to avoid cropping an arbitrary logo.
Browser favicons use 64 pixel PNG URLs and touch icons use 180 pixel PNG URLs.
Loading and login header logos remain embedded and keep their independent sizes.

Icons are served from one public native HA view, registered once through
`hass.http.register_view`. HA supports dynamic registration on its production
router. The view remains registered but returns 404 with no active runtime;
no private router resource removal is needed on unload.

Android generates its native splash from manifest metadata, and controls its
layout. Chrome/Android caches installed web app icons independently of page HTML.
Testing in a fresh tab is not sufficient to prove an old installed shortcut has
updated; recreate the shortcut/web app to force a fresh install. These features
have server-level tests against Core 2026.10.4, not an Android emulator test.

Source references:
- https://developer.chrome.com/docs/lighthouse/pwa/splash-screen
- https://web.dev/articles/manifest-updates
- https://developer.chrome.com/blog/improvements-to-web-app-updates
