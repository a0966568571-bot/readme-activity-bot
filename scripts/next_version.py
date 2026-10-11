"""Work out the next release version from VERSION and the existing git tags.

VERSION holds MAJOR.MINOR and is edited by hand when we want a minor or major bump.
The patch number is bumped automatically: one more than the highest patch already
tagged for that MAJOR.MINOR in any environment (dev-, staging- or prod-).

Looking at every environment, not just prod, matters: if a production deploy is
rejected, dev-v1.0.5 already exists, so the next run must use 1.0.6, not 1.0.5 again.
"""
import os
import re
import subprocess
import sys

BASE_RE = re.compile(r"^(\d+)\.(\d+)$")
TAG_RE = re.compile(r"^[a-z]+-v(\d+)\.(\d+)\.(\d+)$")


def parse_base(text):
    m = BASE_RE.match(text.strip())
    if not m:
        raise ValueError("VERSION must look like MAJOR.MINOR, got %r" % text.strip())
    return int(m.group(1)), int(m.group(2))


def next_version(base, tags):
    major, minor = base
    released = []
    for tag in tags:
        m = TAG_RE.match(tag.strip())
        if m:
            released.append(tuple(int(x) for x in m.groups()))
    if released and (major, minor) < max(released)[:2]:
        raise ValueError(
            "VERSION %d.%d is older than the newest tag %d.%d.%d" % ((major, minor) + max(released))
        )
    patches = [p for (ma, mi, p) in released if (ma, mi) == (major, minor)]
    patch = max(patches) + 1 if patches else 0
    return "%d.%d.%d" % (major, minor, patch)


def main():
    with open("VERSION") as f:
        base = parse_base(f.read())
    tags = subprocess.run(
        ["git", "tag", "--list"], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    version = next_version(base, tags)
    print(version)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write("version=%s\n" % version)


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        sys.exit(1)
