#!/usr/bin/env python
"""
Extracts Wynncraft item icons from the resource pack as .webp files.

Usage:
    python scripts/extract_resource_pack_icons.py --dry-run
    python scripts/extract_resource_pack_icons.py
    python scripts/extract_resource_pack_icons.py --overwrite

Requires: Pillow (pip install Pillow)
See docs/icon_extraction_plan.md for the full extraction plan.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SRC = Path(
    r"C:\Users\timki\Downloads\play.wynncraft.com"
    r"\play.wynncraft.com\assets\minecraft\textures\wynn"
)
DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "modules" / "routes" / "web" / "static" / "icons" / "wynn_icons"
)

ARCHETYPE_TO_WEAPON = {
    "archer": "bow",
    "assassin": "dagger",
    "mage": "wand",
    "shaman": "relik",
    "warrior": "spear",
}

TIER_LETTER = {"a": "1", "b": "2", "c": "3"}

BASIC_MAP = {
    "basic_gold": "basicGold",
    "basic_wooden": "basicWood",
    "basic_diamond": "basicDiamond",
    "basic_wood_gold": "basicWoodGold",
}

SKIP_DIRS = {"gui", "jigsaw", "signage", "housing"}

GENERIC_CATEGORIES = [
    "augment", "dungeon", "ingredient", "legacy", "loot",
    "mastery_tome", "mount", "potion", "pouch", "prop",
    "rune", "scroll", "tool", "ward",
]


# ---------------------------------------------------------------------------
# Stats tracker
# ---------------------------------------------------------------------------

class Stats:
    def __init__(self):
        self.created = 0
        self.skipped = 0
        self.warnings = 0

    def summary(self):
        print(f"\nDone. {self.created} created, {self.skipped} skipped, "
              f"{self.warnings} warnings.")


stats = Stats()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase: 'some_thing' -> 'someThing'."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def first_frame(img: Image.Image) -> Image.Image:
    """If the image is a vertical spritesheet, return the top square frame."""
    w, h = img.size
    if h > w > 0:
        return img.crop((0, 0, w, w))
    return img


def composite_layers(paths: list) -> Image.Image:
    """Alpha-composite PNG layers bottom-to-top."""
    base = first_frame(Image.open(paths[0]).convert("RGBA"))
    for p in paths[1:]:
        layer = first_frame(Image.open(p).convert("RGBA"))
        if layer.size != base.size:
            layer = layer.resize(base.size, Image.NEAREST)
        base = Image.alpha_composite(base, layer)
    return base


def save_icon(img: Image.Image, dest: Path, dry_run: bool):
    """Save image as WebP."""
    if dry_run:
        print(f"  [dry-run] {dest.name}")
        stats.created += 1
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest), "WEBP", quality=90, method=6)
    print(f"  ok    {dest.name}")
    stats.created += 1


def should_skip(dest: Path, skip_existing: bool) -> bool:
    if skip_existing and dest.exists():
        stats.skipped += 1
        return True
    return False


def is_animated_variant(path: Path) -> bool:
    """Check if this PNG is an animated variant (*_a.png with .mcmeta)."""
    if not path.stem.endswith("_a"):
        return False
    mcmeta = Path(str(path) + ".mcmeta")
    return mcmeta.exists()


def collect_pngs(directory: Path) -> list:
    """Collect non-animated PNGs from a directory (non-recursive)."""
    if not directory.exists():
        return []
    return sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix == ".png" and not is_animated_variant(f)
    )


def group_numbered_layers(pngs: list) -> dict:
    """
    Group files by base name, collecting _0, _1, _2 suffixed layers.
    Standalone files (no _N suffix) become single-item groups.
    """
    numbered = defaultdict(list)
    standalone = []

    for f in pngs:
        m = re.match(r"^(.+)_(\d+)$", f.stem)
        if m:
            numbered[m.group(1)].append((int(m.group(2)), f))
        else:
            standalone.append(f)

    result = {}
    for base, layers in sorted(numbered.items()):
        layers.sort(key=lambda x: x[0])
        result[base] = [p for _, p in layers]

    for f in standalone:
        if f.stem not in numbered:
            result[f.stem] = [f]

    return result


def process_group(layers: list, dest: Path, dry_run: bool, skip_existing: bool):
    """Composite layers (if multiple) and save as WebP."""
    if should_skip(dest, skip_existing):
        return
    if len(layers) > 1:
        img = composite_layers(layers)
    else:
        img = first_frame(Image.open(layers[0]).convert("RGBA"))
    save_icon(img, dest, dry_run)


# ---------------------------------------------------------------------------
# Weapon extraction
# ---------------------------------------------------------------------------

def weapon_attr(base_name: str) -> str:
    """Map weapon texture base name to CDN attribute string."""
    if base_name in BASIC_MAP:
        return BASIC_MAP[base_name]

    # element_tier_X (specific tier: a/b/c -> 1/2/3)
    m = re.match(r"^(\w+?)_tier_([abc])$", base_name)
    if m:
        return f"{m.group(1)}{TIER_LETTER[m.group(2)]}"

    # element_tier_X_Y (combined tiers, e.g. fire_tier_b_c, multi_tier_a_b)
    m = re.match(r"^(\w+?)_tier_([abc])_([abc])$", base_name)
    if m:
        return f"{m.group(1)}{TIER_LETTER[m.group(2)]}"

    # element_tier_all (one texture for all tiers)
    m = re.match(r"^(\w+?)_tier_all$", base_name)
    if m:
        return m.group(1)

    # element_{weapon}_all (e.g. thunder_bow_all)
    m = re.match(r"^(\w+?)_\w+_all$", base_name)
    if m:
        return m.group(1)

    return ""


def extract_weapons(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    weapon_dir = src / "weapon"
    if not weapon_dir.exists():
        return
    print("\n== Weapons ==")
    skip_prefixes = ("sunflower",)

    for arch_dir in sorted(weapon_dir.iterdir()):
        if not arch_dir.is_dir() or arch_dir.name == "anim":
            continue
        wtype = ARCHETYPE_TO_WEAPON.get(arch_dir.name)
        if not wtype:
            continue

        pngs = collect_pngs(arch_dir)
        groups = group_numbered_layers(pngs)

        for base_name, layers in groups.items():
            if any(base_name.startswith(p) for p in skip_prefixes):
                continue
            attr = weapon_attr(base_name)
            if not attr:
                print(f"  warn  unknown weapon texture: {arch_dir.name}/{base_name}")
                stats.warnings += 1
                continue
            process_group(layers, out / f"{wtype}.{attr}.webp", dry_run, skip_existing)


# ---------------------------------------------------------------------------
# Armor extraction
# ---------------------------------------------------------------------------

def extract_armor(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    armor_dir = src / "armor"
    if not armor_dir.exists():
        return
    print("\n== Armor ==")

    for piece_dir in sorted(armor_dir.iterdir()):
        if not piece_dir.is_dir():
            continue
        piece = piece_dir.name

        pngs = collect_pngs(piece_dir)
        overlay_map = {}
        base_files = []

        for f in pngs:
            if f.stem.startswith("pale_"):
                continue
            if f.stem.endswith("_overlay"):
                overlay_map[f.stem.removesuffix("_overlay")] = f
            else:
                base_files.append(f)

        for f in base_files:
            suffix = f"_{piece}"
            material = f.stem.removesuffix(suffix) if f.stem.endswith(suffix) else f.stem

            dest = out / f"{piece}.{material}.webp"
            if should_skip(dest, skip_existing):
                continue

            base_img = first_frame(Image.open(f).convert("RGBA"))
            if f.stem in overlay_map:
                overlay = first_frame(Image.open(overlay_map[f.stem]).convert("RGBA"))
                if overlay.size != base_img.size:
                    overlay = overlay.resize(base_img.size, Image.NEAREST)
                base_img = Image.alpha_composite(base_img, overlay)

            save_icon(base_img, dest, dry_run)


# ---------------------------------------------------------------------------
# Accessory extraction
# ---------------------------------------------------------------------------

def extract_accessories(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    acc_dir = src / "accessory"
    if not acc_dir.exists():
        return
    print("\n== Accessories ==")

    pngs = collect_pngs(acc_dir)
    groups = group_numbered_layers(pngs)

    for base_name, layers in groups.items():
        m = re.match(r"^(ring|necklace|bracelet)_(.+)$", base_name)
        if not m:
            print(f"  warn  unknown accessory: {base_name}")
            stats.warnings += 1
            continue
        acc_type, variant = m.groups()
        process_group(layers, out / f"{acc_type}.{variant}.webp", dry_run, skip_existing)


# ---------------------------------------------------------------------------
# Spell extraction
# ---------------------------------------------------------------------------

def extract_spells(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    spell_dir = src / "spell"
    if not spell_dir.exists():
        return
    print("\n== Spells ==")

    pngs = collect_pngs(spell_dir)
    groups = group_numbered_layers(pngs)

    for base_name, layers in groups.items():
        attr = snake_to_camel(base_name)
        process_group(layers, out / f"spell.{attr}.webp", dry_run, skip_existing)


# ---------------------------------------------------------------------------
# Powder extraction (palette-based)
# ---------------------------------------------------------------------------

def extract_powders(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    powder_dir = src / "powder"
    if not powder_dir.exists():
        return
    print("\n== Powders ==")

    palette_dir = powder_dir / "color_palettes"
    ref_path = palette_dir / "powder_palette.png"

    if not ref_path.exists():
        print("  warn  powder_palette.png not found, extracting base textures only")
        stats.warnings += 1
        for size in ("small", "large"):
            base_path = powder_dir / f"{size}.png"
            if base_path.exists():
                dest = out / f"powder.{size}.webp"
                if not should_skip(dest, skip_existing):
                    img = first_frame(Image.open(base_path).convert("RGBA"))
                    save_icon(img, dest, dry_run)
        return

    ref_palette = Image.open(ref_path).convert("RGBA")
    ref_colors = [ref_palette.getpixel((x, 0)) for x in range(ref_palette.width)]

    elements = ["air", "earth", "fire", "thunder", "water"]
    sizes = ["small", "large"]

    for element in elements:
        elem_path = palette_dir / f"{element}.png"
        if not elem_path.exists():
            print(f"  warn  {element}.png palette not found")
            stats.warnings += 1
            continue

        elem_palette = Image.open(elem_path).convert("RGBA")
        elem_colors = [elem_palette.getpixel((x, 0)) for x in range(elem_palette.width)]

        color_map = {}
        for rc, ec in zip(ref_colors, elem_colors):
            color_map[rc] = ec

        for size in sizes:
            base_path = powder_dir / f"{size}.png"
            if not base_path.exists():
                continue

            dest = out / f"powder.{element}{size.capitalize()}.webp"
            if should_skip(dest, skip_existing):
                continue

            if dry_run:
                print(f"  [dry-run] {dest.name}")
                stats.created += 1
                continue

            base_img = first_frame(Image.open(base_path).convert("RGBA"))
            pixels = base_img.load()
            w, h = base_img.size
            for y in range(h):
                for x in range(w):
                    px = pixels[x, y]
                    if px in color_map:
                        pixels[x, y] = color_map[px]

            save_icon(base_img, dest, False)


# ---------------------------------------------------------------------------
# Economy -> Profession extraction
# ---------------------------------------------------------------------------

def extract_professions(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    eco_dir = src / "economy"
    if not eco_dir.exists():
        return
    print("\n== Professions (economy) ==")

    # First pass: collect all items and detect name collisions
    all_items = []
    name_sources = defaultdict(set)

    for sub_dir in sorted(eco_dir.iterdir()):
        if not sub_dir.is_dir():
            continue
        subcategory = sub_dir.name
        pngs = collect_pngs(sub_dir)
        groups = group_numbered_layers(pngs)

        for base_name, layers in groups.items():
            camel = snake_to_camel(base_name)
            name_sources[camel].add(subcategory)
            all_items.append((subcategory, camel, layers))

    # Second pass: extract with collision-aware naming
    for subcategory, camel, layers in all_items:
        if len(name_sources[camel]) > 1:
            name = snake_to_camel(subcategory) + camel[0].upper() + camel[1:]
        else:
            name = camel
        process_group(layers, out / f"profession.{name}.webp", dry_run, skip_existing)


# ---------------------------------------------------------------------------
# Generic category extraction
# ---------------------------------------------------------------------------

def extract_generic(src: Path, out: Path, category: str, dry_run: bool,
                    skip_existing: bool):
    cat_dir = src / category
    if not cat_dir.exists():
        return

    prefix = snake_to_camel(category)
    print(f"\n== {prefix} ==")

    pngs = collect_pngs(cat_dir)
    groups = group_numbered_layers(pngs)

    for base_name, layers in groups.items():
        attr = snake_to_camel(base_name)
        process_group(layers, out / f"{prefix}.{attr}.webp", dry_run, skip_existing)


# ---------------------------------------------------------------------------
# Root-level wynn/ textures
# ---------------------------------------------------------------------------

def extract_root(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    pngs = [
        f for f in sorted(src.iterdir())
        if f.is_file() and f.suffix == ".png" and not is_animated_variant(f)
    ]
    if not pngs:
        return
    print("\n== Misc (root) ==")

    groups = group_numbered_layers(pngs)
    for base_name, layers in groups.items():
        attr = snake_to_camel(base_name)
        process_group(layers, out / f"misc.{attr}.webp", dry_run, skip_existing)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def extract_all(src: Path, out: Path, dry_run: bool, skip_existing: bool):
    print(f"Source:    {src}")
    print(f"Output:    {out}")
    print(f"Mode:      {'dry-run' if dry_run else 'write'}")
    print(f"Existing:  {'skip' if skip_existing else 'overwrite'}")

    if not src.exists():
        print(f"\nError: source directory not found: {src}")
        sys.exit(1)

    out.mkdir(parents=True, exist_ok=True)

    extract_weapons(src, out, dry_run, skip_existing)
    extract_armor(src, out, dry_run, skip_existing)
    extract_accessories(src, out, dry_run, skip_existing)
    extract_spells(src, out, dry_run, skip_existing)
    extract_powders(src, out, dry_run, skip_existing)
    extract_professions(src, out, dry_run, skip_existing)

    for cat in GENERIC_CATEGORIES:
        extract_generic(src, out, cat, dry_run, skip_existing)

    extract_root(src, out, dry_run, skip_existing)

    stats.summary()


def main():
    parser = argparse.ArgumentParser(
        description="Extract Wynncraft resource pack icons as .webp"
    )
    parser.add_argument(
        "--src", type=Path, default=DEFAULT_SRC,
        help="Resource pack wynn textures directory",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help="Output directory for .webp icons",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview output filenames without writing files",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing icons (default: skip)",
    )
    args = parser.parse_args()
    extract_all(args.src, args.out, args.dry_run, not args.overwrite)


if __name__ == "__main__":
    main()
