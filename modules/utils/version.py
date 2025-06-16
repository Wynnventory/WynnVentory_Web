import re
from functools import total_ordering


@total_ordering
class VersionPart:
    """
    A helper class that represents one “dot‑piece” of a version string,
    e.g. “3”, “3a”, “beta2”, “0-dev”.
    It splits into a numeric prefix and a string suffix, and compares:
      1) numerically by the prefix
      2) then by suffix, with this precedence:
         – any “dev” suffix (e.g. “dev”, “-dev”, “dev1”) >
         – empty suffix (final release) >
         – any other non‑empty (pre‑release)
         – otherwise, lexicographically
    """
    __slots__ = ("num", "suffix")

    def __init__(self, part: str):
        m = re.match(r"^(\d+)(.*)$", part)
        if m:
            self.num = int(m.group(1))
            self.suffix = m.group(2) or ""
        else:
            # no leading digits at all → treat numeric part as 0
            self.num = 0
            self.suffix = part

    def __eq__(self, other):
        if not isinstance(other, VersionPart):
            return NotImplemented
        return (self.num, self.suffix) == (other.num, other.suffix)

    def __lt__(self, other):
        if not isinstance(other, VersionPart):
            return NotImplemented

        # 1) different numeric prefix
        if self.num != other.num:
            return self.num < other.num

        # 2) same numeric → compare suffix
        if self.suffix == other.suffix:
            return False

        # helper to test for a “dev” suffix (strip leading dashes, case‑insensitive)
        def is_dev(s: str) -> bool:
            return s.lstrip("-").lower().startswith("dev")

        # 2a) dev _always_ ranks highest
        if is_dev(self.suffix) and not is_dev(other.suffix):
            return False  # self (dev) > other → not less
        if is_dev(other.suffix) and not is_dev(self.suffix):
            return True  # other (dev) > self → self < other

        # 2b) empty suffix (final) > any other non‑dev pre‑release
        if self.suffix == "":
            return False  # self (final) > other → not less
        if other.suffix == "":
            return True  # other (final) > self → self < other

        # 2c) both non‑empty, non‑dev → lexicographic
        return self.suffix < other.suffix


def compare_versions(version_a: str, version_b: str) -> bool:
    """
    Returns True if version_a >= version_b else False.
    Handles segments with trailing letters (including '-dev'),
    and differing segment counts.
    """
    parts_a = version_a.split(".")
    parts_b = version_b.split(".")
    # pad the shorter one with “0” segments, so we compare everything
    length = max(len(parts_a), len(parts_b))
    parts_a += ["0"] * (length - len(parts_a))
    parts_b += ["0"] * (length - len(parts_b))

    for pa, pb in zip(parts_a, parts_b):
        vp_a = VersionPart(pa)
        vp_b = VersionPart(pb)
        if vp_a > vp_b:
            return True
        if vp_a < vp_b:
            return False
    # all parts equal
    return True
