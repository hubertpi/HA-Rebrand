"""Supply actual generated login scripts to the isolated DOM tests."""

import json
import re
import sys
from pathlib import Path

import hass_frontend

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.ha_rebrand_local.branding import Branding
from custom_components.ha_rebrand_local.login import transform_login_html

original = (hass_frontend.where() / "authorize.html").read_text()
fixtures = {}
for heading in [
    "Welcome",
    "Welcome home!",
    "</script><script>window.compromised=true</script>",
    "Facility sign in",
]:
    branding = Branding("Facility", True, None, None, None, login_heading=heading)
    html = transform_login_html(original, branding)
    script = re.search(
        r'<script id="ha-rebrand-local-login-heading">(.*?)</script>', html, re.DOTALL
    ).group(1)
    fixtures[heading] = script
print(json.dumps(fixtures))
