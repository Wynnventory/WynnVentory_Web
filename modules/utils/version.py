def compare_versions(version_a: str, version_b: str) -> bool:
    if version_a.lower().find("dev") != -1:
        return True

    # Split the versions by dot and convert each part to an integer
    parts_a = list(map(int, version_a.split('.')))
    parts_b = list(map(int, version_b.split('.')))

    # Compare each part: major, minor, patch
    for a, b in zip(parts_a, parts_b):
        if a > b:
            return True
        elif a < b:
            return False
    return True