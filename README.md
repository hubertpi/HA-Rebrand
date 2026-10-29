# HA Rebrand

Local, English-only loading screen branding for Home Assistant.

Change the initial loading logo and displayed brand name, hide the Open Home
Foundation loading attribution, and optionally change the browser favicon.
Uses native Home Assistant configuration screens. No remote JavaScript, custom
admin panel, telemetry, upload service, or authentication-route replacement.

**Version 0.1.0 is an initial development release.** Automated tests use Home
Assistant Core **2026.10.4**, frontend **20260930.5**, and Python **3.14**.
It still needs a first installation check on your HA instance. Later HA versions
may require compatibility updates; the minimum version is not a guarantee of
compatibility with every future release.

## Install through HACS

1. Open HACS, select its menu, and open **Custom repositories**.
2. Add `https://github.com/hubertpi/HA-Rebrand` with type **Integration**.
3. Find **HA Rebrand** and download it.
4. Restart Home Assistant Core.
5. Open **Settings > Devices & services > Add integration**, and select **HA Rebrand**.
6. Set the brand name and attribution option. Leave image filenames blank to keep
   the Home Assistant loading logo and favicon.
7. Reload the browser to see the result. Use a hard reload if necessary.

Remove the original `WOOWTECH/Ha_rebrand_manager` integration and restart Core
before using this one. Our domain is `ha_rebrand_local`; it does not import the
old integration, migrate its settings, or use its public files.

## Custom logos and favicon

Create this directory using your HA file editor, Samba, or Terminal:

```bash
mkdir -p /config/ha_rebrand_local
```

Copy your PNG files there, for example:

```text
/config/ha_rebrand_local/logo.png
/config/ha_rebrand_local/logo-dark.png
/config/ha_rebrand_local/favicon.png
```

Under **Settings > Devices & services > HA Rebrand > Configure**, enter only the
basenames, such as `logo.png`. Paths, URLs, SVGs, symlinks, animated PNGs and files
larger than 2 MiB are rejected. Images may be at most 2048 by 2048 pixels. Use
transparent PNGs with comfortable padding; the loading logo fits a 96 by 96 box.
A square favicon is recommended.

The dark logo follows the browser/OS `prefers-color-scheme` setting during early
loading. HA's saved theme is not yet available at that stage. If only one logo
is supplied, it is used for both modes. If both fields are blank, the stock
Home Assistant loading logo stays in place.

PNG content is decoded and re-encoded with metadata removed, then embedded in
the HTML. There are no public logo endpoints and no additional image requests.
Your configured brand name and logos are visible to anyone able to load HA's
index page, just like the default loading screen; do not use sensitive content.

Changing an image file requires reloading the integration, or saving its options,
then reloading the browser. Files are read only during setup/options validation.

## Options

| Option | Behavior |
| --- | --- |
| Enable branding | Turn this integration's changes on or off. |
| Brand name | Loading screen text, loading image alt text, and browser tab title. Defaults to Home Assistant; use 1 to 80 printable ASCII characters. |
| Hide Open Home Foundation attribution | Hide the loading screen attribution while retaining its layout space. Enabled by default. |
| Light logo filename | PNG basename inside `/config/ha_rebrand_local`. Optional. |
| Dark logo filename | Optional PNG for a dark browser/OS color scheme. |
| Favicon filename | Optional PNG for the browser tab. |

Settings live only in the native config entry options. There is no YAML or
parallel JSON configuration. All code, documentation, and supplied UI text is
English. No non-English translation files are included.

The brand name changes visible loading/tab branding; it does not rename the HA
installation in its backend configuration. A custom tab name stays fixed when
navigating dashboards. The sidebar, login page, onboarding page, installed PWA
icons/name, mobile app native splash, and theme accent colors remain stock in
this version. Mobile WebView loading behavior still requires device testing.

## Disable, remove, and recover

- To disable, uncheck **Enable branding** in Configure, or disable the integration
  in HA. Saving options reloads the integration automatically.
- To remove, delete the integration entry in HA, then remove it from HACS.
- Reload every open browser tab/WebView afterward. A document already loaded in
  a browser retains its current title script until the document is reloaded.
- User-supplied PNGs in `/config/ha_rebrand_local` are deliberately preserved.
  Remove that directory manually if you no longer want those images.

Unloading restores the exact original index template in the running HA process.
Core and frontend package files are never modified. If another component has
replaced the same template after HA Rebrand, this integration preserves that
component's replacement and logs a warning; restart Core to finish cleanup.

If the UI becomes inaccessible, remove
`/config/custom_components/ha_rebrand_local` through Terminal/file access and
restart Core. HA safe mode skips custom integrations and is another recovery
option. Do not edit `.storage` files to remove this integration.

## Architecture and compatibility

The loading logo and foundation attribution are already present in the initial
server HTML. `frontend.add_extra_js_url()` runs later and cannot prevent an
initial flash of stock branding. For immediate branding, this implementation
wraps **one instance's `IndexView._template_cache`** with a Jinja template adapter.
This is a private HA implementation detail, documented in [COMPATIBILITY.md](COMPATIBILITY.md).

The adapter first renders the original template unchanged, then transforms only
known launch screen/title markers. User input never becomes Jinja source. It
adds scoped CSS and, for a custom name, a small inline title observer. This uses
the same script environment as HA's existing inline startup scripts and needs
no disabled browser security settings.

It never patches the `IndexView` class or `get_template`, rewrites HA package
files, modifies the router, replaces `/auth/authorize` or `/onboarding`, or reads
authentication tokens. Setup rejects unfamiliar template markers. Runtime
transformation errors return the original HTML and log once per wrapper.

See [SECURITY.md](SECURITY.md), [TESTING.md](TESTING.md), and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Development

Use Python 3.14 on Linux:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest -q
```

Tests install the actual pinned Core and frontend packages. The HTTP harness
uses real `IndexView` and aiohttp with controlled HA state; it is not a complete
production HA installation. No production HA instance is contacted by the tests.
