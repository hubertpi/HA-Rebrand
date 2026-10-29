# Dependency notices

HA Rebrand is distributed under the MIT license in LICENSE.

Home Assistant Core, its frontend, Jinja2, and Pillow are supplied by the Home
Assistant installation and retain their respective upstream licenses. Their
source code is not bundled in this repository. Tests install the pinned Core
and frontend packages and read the index template from that installed package.

The icon is an original vector design included under this project's MIT license.
CairoSVG was used to render its PNG exports; CairoSVG is not required at runtime.

The development-only DOM tests use jsdom and its npm dependencies, whose
licenses are recorded in package-lock.json. They are not installed into HA Core
or downloaded by the integration at runtime.
