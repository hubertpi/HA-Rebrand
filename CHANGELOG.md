# Changelog

## 0.1.6

- Apply the configured brand name to the login browser tab title.
- Escape title text safely and preserve login logo placement after title changes.
- Keep the stock title when login branding is disabled or removed.

## 0.1.5

- Apply the configured favicon to the login page as well as the main frontend.
- Preserve the stock login header logo when only a favicon is configured.
- Restore the stock login favicon when login branding is disabled or removed.

## 0.1.4

- Add independently configurable login branding, welcome text, light/dark PNGs,
  and logo width, defaulting to the loading logos and the heading Welcome.
- Preserve the existing static login route, auth bootstrap scripts, credential
  handling, MFA prompts, and authentication API routes.
- Restore both presentation hooks when disabled or removed.
- Add isolated DOM tests for heading updates, MFA preservation, safe text,
  component text-node identity, observer cleanup, and repeated rendering.

## 0.1.3

- Add a loading logo width setting from 96 to 800 pixels.
- Increase custom logos to a 320-pixel default width, preserving their natural
  proportions instead of fitting wide wordmarks into a 96 by 96 pixel box.
- Scale logos down on small screens and keep them above the centered name.
- Apply the larger default to existing settings without a migration.

## 0.1.2

- Add a dedicated HA Rebrand icon with standard and high-resolution PNGs for
  Home Assistant's native integration branding.
- Publish versioned GitHub releases after tests pass on main, so HACS can show
  release numbers instead of commit hashes.
- Add complete installation, image setup, updates, removal, and troubleshooting
  instructions, with an AI-generated notice at the top of the README.
- Keep the loading logo centered above the brand name from 0.1.1.

## 0.1.1

- Center the loading logo above the brand name on all screen sizes.

## 0.1.0

- Initial loading screen, name and favicon customization with native options.
- Validated local PNG files, no remote scripts, and reversible template cleanup.
