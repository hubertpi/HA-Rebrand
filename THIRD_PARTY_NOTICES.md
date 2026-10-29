# Third-party notices

## Reference project

This project was inspired by HA Rebrand Manager:
https://github.com/WOOWTECH/Ha_rebrand_manager

Reference inspected: commit `797d215cc6c867607d88eaa0e381bdc57a6992bf`.
Its MIT license was verified before implementation. This project is a new,
English-only implementation of the loading-screen requirements. It does not
bundle the original Python backend, frontend JavaScript, admin panel, remote
LitElement dependency, authentication views, or translations. The upstream
notice is retained below for attribution.

```text
MIT License

Copyright (c) 2026 woowtech

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Runtime and test dependencies

Home Assistant, its frontend, Jinja2 and Pillow are provided by Home Assistant's
installation. Their source is not bundled here. The tests install those packages
and use the frontend template from that installed package. Their respective
upstream licenses continue to apply to those packages.
