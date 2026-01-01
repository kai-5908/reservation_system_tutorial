import os

# Ensure AUTH_SECRET is available before importing application modules in tests.
os.environ.setdefault("AUTH_SECRET", "testsecret")
