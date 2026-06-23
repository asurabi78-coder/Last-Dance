#!/usr/bin/env python3
"""Email pattern guesser for journalists.

Inputs : journalists.jsonl
Output : emails.csv (journalist_slug, candidate_email_1..3, verified_status)

Patterns applied (in order of likelihood per major US/UK outlet groups):

  Hearst / Condé Nast / Dotdash Meredith    : firstname.lastname@outlet.com
  NBCUniversal / Vox / Voxnet                : flastname@outlet.com
  BuzzFeed / indie / Substack newsletter     : firstname@outlet.com
  Generic catchall                            : firstname_lastname@outlet.com

Verification (--verify flag):
  - SMTP MX probe via dnspython + smtplib (free, ~60% accurate)
  - Hunter.io API if HUNTER_API_KEY env var set (paid, ~95% accurate)

Usage:
  python3 guess_emails.py journalists.jsonl --out emails.csv
  python3 guess_emails.py journalists.jsonl --out emails.csv --verify
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from unicodedata import normalize


# Outlet → preferred pattern. Add more as you observe.
OUTLET_PATTERNS = {
    # Hearst (cosmopolitan, esquire, goodhousekeeping, womensday, marieclaire)
    "cosmopolitan.com":      "firstname.lastname",
    "esquire.com":           "firstname.lastname",
    "goodhousekeeping.com":  "firstname.lastname",
    "womensday.com":         "firstname.lastname",
    # Condé Nast (vogue, glamour, allure, teenvogue, gq, vanityfair, wired)
    "vogue.com":             "firstname_lastname",
    "glamour.com":           "firstname_lastname",
    "allure.com":            "firstname_lastname",
    "teenvogue.com":         "firstname_lastname",
    "wired.com":             "firstname_lastname",
    # Dotdash Meredith (people, instyle, byrdie, realsimple, parents, thespruce, marthastewart, southernliving)
    "people.com":            "firstname.lastname",
    "instyle.com":           "firstname.lastname",
    "byrdie.com":            "firstname.lastname",
    "realsimple.com":        "firstname.lastname",
    "parents.com":           "firstname.lastname",
    # NBC Universal
    "nbcnews.com":           "flastname",
    # Vice / Refinery29 (now Vice Media)
    "refinery29.com":        "firstname.lastname",
    # BuzzFeed
    "buzzfeed.com":          "firstname.lastname",
    # The Guardian
    "theguardian.com":       "firstname.lastname",
}

ALL_PATTERNS = ["firstname.lastname", "firstname_lastname", "flastname", "firstname"]


def normalize_name(name):
    """ASCII-fold, lowercase, drop apostrophes/special chars."""
    n = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^A-Za-z\s\-]", "", n).strip().lower()
    return n


def split_name(name):
    """Return (firstname, lastname). Handles middle names by collapsing into last."""
    parts = normalize_name(name).split()
    if len(parts) < 2:
        return parts[0] if parts else "", ""
    return parts[0], parts[-1]


def make_email(first, last, domain, pattern):
    if pattern == "firstname.lastname":
        return f"{first}.{last}@{domain}"
    if pattern == "firstname_lastname":
        return f"{first}_{last}@{domain}"
    if pattern == "flastname":
        return f"{first[0]}{last}@{domain}"
    if pattern == "firstname":
        return f"{first}@{domain}"
    return None


def guess(name, domain):
    first, last = split_name(name)
    if not first or not last:
        return []
    primary = OUTLET_PATTERNS.get(domain, "firstname.lastname")
    fallbacks = [p for p in ALL_PATTERNS if p != primary][:2]
    return [make_email(first, last, domain, p) for p in [primary] + fallbacks]


def verify_smtp(email):
    """Lightweight SMTP MX probe. Returns 'smtp_ok' / 'smtp_fail' / 'unknown'."""
    try:
        import dns.resolver
        import smtplib
    except ImportError:
        return "unknown"  # dnspython not installed
    domain = email.split("@", 1)[1]
    try:
        records = dns.resolver.resolve(domain, "MX")
        mx = sorted(records, key=lambda r: r.preference)[0].exchange.to_text()
    except Exception:
        return "smtp_fail"
    try:
        s = smtplib.SMTP(timeout=10)
        s.connect(mx)
        s.helo("example.com")
        s.mail("verify@example.com")
        code, _ = s.rcpt(email)
        s.quit()
        return "smtp_ok" if code in (250, 251) else "smtp_fail"
    except Exception:
        return "unknown"


def verify_hunter(email):
    """Hunter.io API verification. Set HUNTER_API_KEY env var."""
    key = os.environ.get("HUNTER_API_KEY")
    if not key:
        return "unknown"
    import requests
    try:
        r = requests.get("https://api.hunter.io/v2/email-verifier",
                         params={"email": email, "api_key": key}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {})
            status = data.get("status", "unknown")
            return f"hunter_{status}"
    except Exception:
        pass
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journalists_file", type=Path)
    ap.add_argument("--out", type=Path, default=Path("emails.csv"))
    ap.add_argument("--verify", action="store_true",
                    help="SMTP probe (slow; or Hunter if HUNTER_API_KEY set)")
    args = ap.parse_args()

    journos = [json.loads(line) for line in args.journalists_file.read_text().splitlines() if line.strip()]
    rows = []
    for j in journos:
        candidates = guess(j["journalist"], j["outlet_domain"])
        verified = "unverified"
        if args.verify and candidates:
            for c in candidates:
                v = verify_hunter(c) if os.environ.get("HUNTER_API_KEY") else verify_smtp(c)
                if v in ("smtp_ok", "hunter_valid", "hunter_accept_all"):
                    verified = v
                    candidates = [c] + [x for x in candidates if x != c]  # promote verified one
                    break
        rows.append({
            "muckrack_slug": j.get("muckrack_slug", ""),
            "journalist": j["journalist"],
            "outlet_domain": j["outlet_domain"],
            "email_1": candidates[0] if len(candidates) > 0 else "",
            "email_2": candidates[1] if len(candidates) > 1 else "",
            "email_3": candidates[2] if len(candidates) > 2 else "",
            "verified": verified,
        })

    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["muckrack_slug","journalist","outlet_domain",
                                          "email_1","email_2","email_3","verified"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} email guesses to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
