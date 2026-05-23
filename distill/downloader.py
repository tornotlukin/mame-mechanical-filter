"""Download the latest catver.ini package from progettoSNAPS.

Scrapes the catver index page for the highest-versioned `pS_CatVer_<NNN>.zip`
href, downloads it, and extracts `catver.ini` into the project's lists/ folder.

Stdlib-only (urllib + zipfile + re) to keep the PyInstaller bundle small.
"""

from __future__ import annotations

import logging
import re
import ssl
import sys
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

from config import (
    CATVER_DOWNLOAD_URL,
    CATVER_FILENAME,
    CATVER_INDEX_URL,
)

logger = logging.getLogger(__name__)

ZIP_FILENAME_PATTERN: re.Pattern[str] = re.compile(r"pS_CatVer_(\d+)\.zip")
USER_AGENT: str = "Mozilla/5.0 (distill MAME ROM filter)"


def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context that trusts the OS root certificates.

    Python on Windows ships with no CA bundle baked in, so the default
    context can't verify HTTPS hosts. We pull the Windows ROOT/CA stores
    via the stdlib `ssl.enum_certificates` helper. On other platforms the
    default context already works.
    """
    ctx = ssl.create_default_context()
    if sys.platform != "win32":
        return ctx
    for store in ("CA", "ROOT"):
        for cert, encoding, _trust in ssl.enum_certificates(store):
            if encoding == "x509_asn":
                try:
                    ctx.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(cert))
                except ssl.SSLError:
                    continue
    return ctx


def _fetch(url: str, timeout: int) -> bytes:
    """GET a URL with strict TLS; fall back to no-verify on Windows AIA gap.

    progettoSNAPS does not send intermediate certs in its TLS handshake.
    Schannel (Windows native TLS) fetches the missing intermediate via the
    AIA URL automatically; OpenSSL (Python) does not. Since the payload is
    a public static data file and the URL is well-known, falling back to
    no-verify with a logged warning is acceptable.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            return r.read()
    except urllib.error.URLError as exc:
        if not isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise
        logger.warning(
            "TLS chain verification failed (server is missing an intermediate "
            "cert); retrying without verification."
        )
        unverified = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=timeout, context=unverified) as r:
            return r.read()


def latest_zip_filename() -> str:
    """Fetch the catver index page and return the newest zip filename."""
    logger.info("Fetching catver index: %s", CATVER_INDEX_URL)
    html = _fetch(CATVER_INDEX_URL, timeout=30).decode("utf-8", errors="replace")

    versions = {int(m.group(1)) for m in ZIP_FILENAME_PATTERN.finditer(html)}
    if not versions:
        raise RuntimeError(
            "No pS_CatVer_<ver>.zip references found at " + CATVER_INDEX_URL
        )
    newest = max(versions)
    return f"pS_CatVer_{newest}.zip"


def download_zip(filename: str) -> bytes:
    """Download the named catver zip and return its bytes."""
    url = CATVER_DOWNLOAD_URL.format(filename=filename)
    logger.info("Downloading: %s", url)
    return _fetch(url, timeout=120)


def extract_catver_ini(zip_bytes: bytes, dest_dir: Path) -> Path:
    """Extract just `catver.ini` from the zip into dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / CATVER_FILENAME

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        member = next(
            (n for n in zf.namelist() if n.lower().endswith(CATVER_FILENAME)),
            None,
        )
        if member is None:
            raise RuntimeError(f"{CATVER_FILENAME} not found inside the downloaded zip")
        with zf.open(member) as src, out_path.open("wb") as dst:
            dst.write(src.read())

    logger.info("Wrote %s", out_path)
    return out_path


def download_latest_catver(dest_dir: Path) -> Path:
    """End-to-end: scrape, download, extract. Returns the path to catver.ini."""
    filename = latest_zip_filename()
    logger.info("Latest catver pack: %s", filename)
    blob = download_zip(filename)
    return extract_catver_ini(blob, dest_dir)
