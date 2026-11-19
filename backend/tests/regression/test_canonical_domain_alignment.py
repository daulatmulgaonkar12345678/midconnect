"""
P1 canonical domain alignment regression tests (no database required).

Owner-approved canonical origin: https://udyogconnect.in (apex, HTTPS).
Every SEO URL the application generates must use it — never the legacy www
host and never the retired udyogconnect.com domain.

Includes a source tripwire: no backend Python file (outside server.py's CORS
allow-list) and no frontend src file (outside the documented keep-lists)
may hardcode the www origin.
"""
import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _BACKEND)

from services.seo_service import SEOService
from services.city_seo_service import CitySEOService

APEX = "https://udyogconnect.in"

# Files allowed to contain the literal https://www.udyogconnect.in:
#  - backend/server.py: CORS allow-list that must accept BOTH hosts
#  - frontend/src/lib/siteUrl.ts: LEGACY_WWW_URL conversion helper (never emitted)
KEEP_WWW = {
    os.path.normpath(os.path.join(_BACKEND, "server.py")),
    os.path.normpath(
        os.path.join(_BACKEND, "..", "frontend", "src", "lib", "siteUrl.ts")
    ),
}


def test_seo_service_site_url_is_apex():
    assert SEOService.SITE_URL == APEX


def test_city_seo_service_site_url_is_apex():
    assert CitySEOService.SITE_URL == APEX


def test_organization_json_ld_uses_apex():
    org = SEOService.generate_organization_json_ld()
    assert org["url"] == APEX
    assert org["logo"] == f"{APEX}/logo.png"


def test_internal_links_use_apex():
    links = SEOService.generate_internal_links(
        product_id="64f000000000000000000001",
        product_name="ABB Contactor",
        category_id="64f000000000000000000002",
        category_name="Contactors",
        category_slug="contactors",
        similar_products=[
            {"_id": "64f000000000000000000003", "name": "Siemens VFD", "slug": "siemens-vfd"}
        ],
        available_cities=["Mumbai", "Pune"],
        product_slug="abb-contactor",
    )
    urls = [links["topRated"], links["category"]["url"]]
    urls += [l["url"] for l in links["similarProducts"]]
    urls += [l["url"] for l in links["cityPages"]]
    urls += [l["url"] for l in links["intentCityPages"]]
    assert urls, "expected at least one generated internal link"
    for u in urls:
        assert u.startswith(APEX), f"non-apex internal link: {u}"
        assert "www.udyogconnect" not in u, f"www internal link: {u}"
        assert "udyogconnect.com" not in u, f"retired domain in internal link: {u}"


def _source_files():
    for root, exts in (
        (_BACKEND, {".py"}),
        (os.path.join(_BACKEND, "..", "frontend", "src"), {".ts", ".tsx"}),
    ):
        root = os.path.abspath(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames
                if d not in ("node_modules", "__pycache__", ".next", "tests", "dist")
            ]
            for fn in filenames:
                if os.path.splitext(fn)[1] in exts:
                    yield os.path.join(dirpath, fn)


def test_tripwire_no_hardcoded_www_origin_in_source():
    offenders = []
    for fp in _source_files():
        if os.path.normpath(fp) in KEEP_WWW:
            continue
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                if "https://www.udyogconnect.in" in line:
                    offenders.append(f"{fp}:{i}: {line.strip()[:120]}")
    assert not offenders, (
        "hardcoded https://www.udyogconnect.in outside the documented keep-list:\n"
        + "\n".join(offenders)
    )


def test_tripwire_no_retired_com_domain_in_frontend():
    offenders = []
    root = os.path.abspath(os.path.join(_BACKEND, "..", "frontend", "src"))
    for fp in _source_files():
        if not fp.startswith(root):
            continue
        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
            for i, line in enumerate(fh, 1):
                if "udyogconnect.com" in line:
                    offenders.append(f"{fp}:{i}: {line.strip()[:120]}")
    assert not offenders, (
        "retired udyogconnect.com domain found in frontend source:\n"
        + "\n".join(offenders)
    )
