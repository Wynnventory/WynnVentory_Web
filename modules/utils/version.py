import re
from functools import total_ordering

@total_ordering
class VersionPart:
    """
    A helper class that represents one “dot‑piece” of a version string,
    e.g. “3”, “3a”, “beta2”.  
    It splits into a numeric prefix and a string suffix, and compares:
      1) numerically by the prefix
      2) then by suffix:
         – empty suffix (a final release) > any non‑empty (a pre‑release)
         – otherwise lexicographically
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
        return (self.num, self.suffix) == (other.num, other.suffix)

    def __lt__(self, other):
        if self.num != other.num:
            return self.num < other.num
        # numeric equal → compare suffix
        # empty suffix is considered “greater” (final release > pre-release)
        if self.suffix == other.suffix:
            return False
        if self.suffix == "":
            return False  # self > other
        if other.suffix == "":
            return True   # self < other
        # both non-empty → lexicographic
        return self.suffix < other.suffix

def compare_versions(version_a: str, version_b: str) -> bool:
    """
    Returns True if version_a >= version_b else False.
    Handles segments with trailing letters, and differing segment counts.
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
