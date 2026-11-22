"""Smoke tests: every page must render without exceptions.

Run with:
    python tests/test_smoke.py                      # uses sample.gnucash
    GNUCASH_DB=/path/to/book.gnucash python tests/test_smoke.py
"""
import glob
import os
import sys

from streamlit.testing.v1 import AppTest

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, BASE)  # pages/ import the app modules from the project root
os.environ.setdefault("GNUCASH_DB", os.path.join(BASE, "sample.gnucash"))

PAGES = [os.path.join(BASE, "Home.py")] + sorted(glob.glob(os.path.join(BASE, "pages", "*.py")))


def run_pages():
    failures = []
    for page in PAGES:
        at = AppTest.from_file(page, default_timeout=240)
        at.run()
        if at.exception:
            failures.append((page, [e.value for e in at.exception]))
        print(f"{os.path.relpath(page, BASE)}: {'FAIL' if at.exception else 'ok'}")
    return failures


if __name__ == "__main__":
    problems = run_pages()
    if problems:
        for page, errors in problems:
            print(f"FAILED {page}: {errors}")
        sys.exit(1)
    print("All pages rendered without exceptions.")
