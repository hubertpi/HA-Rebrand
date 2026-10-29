# Security design

This is a frontend customization, not an authentication or security component.

- No network client, telemetry, remote import, subprocess, external executable,
  new HTTP/WebSocket endpoint, or token access exists in the integration.
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

The instance template cache is private HA API. A future frontend/Core update can
require an integration update. Guards reject changed markers at setup, runtime
failure falls back to original HTML, and unload restores the previous template.
See COMPATIBILITY.md for the exact hook and recovery path.

## Reporting a problem

Open an issue at https://github.com/hubertpi/HA-Rebrand/issues with versions and
sanitized logs. Do not post tokens, passwords, full `.storage` files or private
HA configuration. For a security issue, describe the affected behavior without
posting working credentials or other private data.
