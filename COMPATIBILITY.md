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

## Private hook

`IndexView.get()` reads `_template_cache` before invoking `get_template()`.
This integration primes the original cache in an executor, verifies a rendered
copy, and replaces that single instance's cache with a `jinja2.Template`
subclass. Its `render()` delegates to the original before applying branding.

The original render cache keys include the template object. Installing or
restoring a different template object consequently selects a different cached
response without clearing the global render cache or changing other integrations.

The hook is intentionally limited to the standard packaged frontend. Frontend
development repositories are rejected. No class method, router collection,
authentication view, or HA package file is changed.

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

The original reference project matched an older inline SVG. HA 2026.10.4 instead
uses an image referencing `/static/images/home-assistant-logo-loading.svg`.
That implementation was not carried over.

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
app native splash screens, installed PWA branding, reverse-proxy HTML rewriting,
or arbitrary third-party themes. Separate light/dark images follow the browser
color preference available before HA startup.
