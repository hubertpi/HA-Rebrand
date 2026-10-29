**AI-generated project:** HA Rebrand's code, icon, and documentation were created with AI assistance.

# HA Rebrand

<img src="custom_components/ha_rebrand_local/brand/icon.png" width="96" height="96" alt="HA Rebrand icon">

Give Home Assistant a custom loading screen with your own logo, name, and favicon.
Configure everything through Home Assistant's native integration settings.

- Center your logo above the brand name.
- Use separate light and dark PNG logos.
- Show or hide the Open Home Foundation loading attribution.
- Set a custom browser tab title and favicon.
- Enable or disable branding without editing HA's files.
- Keep settings and logos through updates and restarts.

No external JavaScript, telemetry, upload service, or custom authentication page.
The integration includes its own icon for Home Assistant's integration screen.

## Requirements

- Home Assistant Core **2026.10.4** or newer; automated compatibility testing uses
  Core **2026.10.4** and frontend **20260930.5**.
- HACS for the recommended installation method.
- Access to your HA configuration directory if you want to add custom PNGs.

The current release is **v0.1.2**. See [release notes](https://github.com/hubertpi/HA-Rebrand/releases)
and [changelog](CHANGELOG.md). Future HA frontend changes may require an update;
see [compatibility details](COMPATIBILITY.md).

## Install with HACS

1. Open **HACS** and its **Custom repositories** menu.
2. Enter `https://github.com/hubertpi/HA-Rebrand` and choose **Integration**.
3. Find **HA Rebrand** in HACS and download the latest numbered release.
4. Restart Home Assistant Core.
5. Open **Settings > Devices & services > Add integration**.
6. Search for **HA Rebrand** and add it.
7. Enter your brand name, choose whether to hide the foundation attribution,
   and save. You can leave all image fields blank to use the stock HA images.
8. Hard-refresh your browser with **Ctrl+Shift+R**.

Only one HA Rebrand entry is needed. It applies to the instance's frontend for
all users. Its integration domain is `ha_rebrand_local`.

### Manual installation

Download the latest release's source ZIP from the
[Releases page](https://github.com/hubertpi/HA-Rebrand/releases).
Copy the entire `custom_components/ha_rebrand_local` folder into your HA
configuration directory's `custom_components` folder, preserving its `brand`
and `translations` subfolders. Restart Core, then follow steps 5 through 8 above.

## Add your logo and favicon

### 1. Create the image directory

In HA Terminal, run:

```bash
mkdir -p /config/ha_rebrand_local
```

You can also create the folder with File editor, Studio Code Server, or Samba.
`/config` means the directory containing your HA `configuration.yaml`.

### 2. Copy your PNG files

Example folder contents:

```text
/config/ha_rebrand_local/logo.png
/config/ha_rebrand_local/logo-dark.png
/config/ha_rebrand_local/favicon.png
```

If an image is already in HA's `www` folder, copy it with:

```bash
cp /config/www/logo.png /config/ha_rebrand_local/logo.png
```

Keep the exact filename, including capitalization. Use static PNGs up to
**2 MiB** and **2048 pixels per dimension**. SVGs, animated PNGs, links to files,
and remote images are not supported. A transparent background works well.

### 3. Configure the filenames

Open **Settings > Devices & services > HA Rebrand > Configure**.

| Field | Example value | Purpose |
| --- | --- | --- |
| Light logo filename | `logo.png` | Logo for light mode. |
| Dark logo filename | `logo-dark.png` | Optional alternative for dark mode. |
| Favicon filename | `favicon.png` | Browser tab icon; a square image is recommended. |

Enter **only the filename**, without `/config`, `/local`, a folder, or a URL.
Save, then hard-refresh the browser. The loading logo fits a 96 by 96 pixel box
and appears above the centered name. Wide logos retain their proportions.

If only one loading logo is supplied, it is used in both modes. If neither is
supplied, HA's loading logo stays in place. To remove a custom image, clear its
filename field and save. Replacing an existing image file requires reloading
the integration or saving its options, followed by a browser refresh.

Dark-mode selection follows the browser/OS color preference during early
loading; HA's saved theme is not yet available at that point.

## Settings

| Option | What it does |
| --- | --- |
| Enable branding | Apply branding. Turn off to restore stock HTML on the next browser load. |
| Brand name | Loading screen text, image alt text, and fixed browser tab title. Use 1 to 80 printable ASCII characters. |
| Hide Open Home Foundation attribution | Hide the loading attribution while retaining its layout space. Enabled by default. |
| Light logo filename | Optional PNG in `/config/ha_rebrand_local`. |
| Dark logo filename | Optional PNG for a dark browser/OS color scheme. |
| Favicon filename | Optional PNG for the browser tab. |

Settings are stored in HA's native config entry. No YAML or separate JSON
configuration is needed. Code, documentation, and supplied interface text are
English-only.

The name controls visible loading/tab branding. It does not change the instance
name in HA's backend settings. The sidebar, login page, onboarding page, installed
PWA name/icons, mobile app native splash, and theme colors are outside this
integration's scope.

## Update through HACS

1. Refresh HACS and open **HA Rebrand**.
2. Install the latest numbered release, for example **v0.1.2**.
3. Restart Home Assistant Core.
4. Hard-refresh open browser tabs. Reload companion app WebViews if used.

Your options and PNG files stay saved. If you previously downloaded **main**,
use HACS's redownload/version selector to choose a numbered release once.
That switches your installation to release-based version tracking.

HACS gets version numbers from **published GitHub releases**, rather than only
from the integration manifest. Each new version on main is tested before the
release workflow publishes its tag and changelog notes. An existing release is
never overwritten. Pull requests do not publish releases.

The bundled integration icon is served by HA's native branding system. Some
older HACS versions still display an upstream placeholder in their own cards,
even when the icon works in **Settings > Devices & services**. The integration
icon is separate from the loading logo and favicon you configure.

## Disable or uninstall

To pause branding, turn off **Enable branding** in Configure, save, and refresh
your browser. You can also disable the integration entry in HA.

To uninstall:

1. Delete the HA Rebrand entry under **Settings > Devices & services**.
2. Remove HA Rebrand from HACS, or remove its custom component folder if installed manually.
3. Reload open browser tabs. A loaded document retains its title behavior until refreshed.
4. Optionally delete `/config/ha_rebrand_local` if you no longer need your images.

Unloading restores the previous index template. HA package files are never
modified. If another component has replaced the template after HA Rebrand, a
warning is logged; restart Core to clear the remaining in-memory changes.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Integration is not listed | Confirm `custom_components/ha_rebrand_local/manifest.json` exists, then restart Core. |
| Image validation fails | Check filename capitalization, directory, PNG content, file size, and dimensions. Enter only a basename. |
| Old image or title remains | Save the options or reload the integration, then hard-refresh the browser. |
| HACS shows a commit hash | Select a published numbered release instead of main. |
| Integration icon has not appeared | Restart Core and refresh. HA caches brand images; older HACS cards may use their own placeholder. |
| Branding setup fails after an HA update | Check HA logs and this repository's compatibility notes/releases. The adapter rejects unsupported loading HTML. |

If you cannot reach the UI, remove
`/config/custom_components/ha_rebrand_local` through Terminal/file access and
restart Core. HA safe mode also skips custom integrations. Do not edit `.storage`
files to remove the integration.

## Technical details

The adapter wraps one instance's loading template and transforms the finished
HTML. It restores the previous template on unload. It does not replace login
routes, change authentication, read tokens, or modify HA package files. PNGs are
validated, stripped of metadata, and embedded in the loading HTML. Your brand
name and images are public to anyone who can load the index, so do not use
sensitive content.

See [security](SECURITY.md), [compatibility](COMPATIBILITY.md),
[validation](TESTING.md), and [dependency notices](THIRD_PARTY_NOTICES.md).

## Development and releases

Use Python 3.14 on Linux:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest -q
```

To publish a new version, bump `custom_components/ha_rebrand_local/manifest.json`
and add a matching `CHANGELOG.md` section. Push to main. The test job runs first;
a successful run publishes the version as `v<major>.<minor>.<patch>` using
GitHub's built-in token. No personal access token is required.

The editable integration icon is `assets/icon.svg`; its PNG exports are bundled
in the component's `brand` directory at 256 and 512 pixels. Runtime users do not
need an SVG renderer.

Licensed under [MIT](LICENSE).
