#!/usr/bin/env python
"""
Renders 3D Minecraft models from the Wynncraft resource pack as .webp icons.

Usage:
    python scripts/render_3d_icons.py --dry-run
    python scripts/render_3d_icons.py
    python scripts/render_3d_icons.py --overwrite --size 256

Requires: Pillow, numpy
See docs/icon_extraction_plan.md for the full extraction plan.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: numpy is required. Install with: pip install numpy")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODELS = Path(
    r"C:\Users\timki\Downloads\play.wynncraft.com"
    r"\play.wynncraft.com\assets\minecraft\models\item\wynn"
)
DEFAULT_TEXTURES = Path(
    r"C:\Users\timki\Downloads\play.wynncraft.com"
    r"\play.wynncraft.com\assets\minecraft\textures"
)
DEFAULT_VANILLA = Path(
    r"C:\Users\timki\Downloads\1.21.11\assets\minecraft"
)
DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "modules" / "routes" / "web" / "static" / "icons" / "wynn_icons"
)

SKIP_CATEGORIES = {
    "housing", "jigsaw", "gui", "template", "emotes", "outer_void",
    "skin", "charm", "accessory", "armor",
}
RENDER_SIZE = 128

TIER_MAP = {"a": "1", "b": "2", "c": "3"}
ARCHETYPE_TO_WEAPON = {
    "archer": "bow", "assassin": "dagger", "mage": "wand",
    "shaman": "relik", "warrior": "spear",
}
FACE_SHADE = {
    "down": 0.5, "up": 1.0,
    "north": 0.8, "south": 0.8,
    "east": 0.6, "west": 0.6,
}

DEFAULT_GUI_VECTOR = [0, 0, 0]

# Default GUI display for models that don't specify one
DEFAULT_GUI = {"rotation": DEFAULT_GUI_VECTOR, "scale": [0.625, 0.625, 0.625]}


# ---------------------------------------------------------------------------
# Stats
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
# Math helpers
# ---------------------------------------------------------------------------

def rot_matrix(deg, axis):
    """3x3 rotation matrix for the given axis."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)


def build_gui_matrix(display):
    """Build the view rotation+scale matrix from GUI display settings."""
    r = display.get("rotation", DEFAULT_GUI_VECTOR)
    s = display.get("scale", [0.625, 0.625, 0.625])
    # Minecraft rotation order: Y, X, Z
    R = rot_matrix(r[1], "y") @ rot_matrix(r[0], "x") @ rot_matrix(r[2], "z")
    S = np.diag(s)
    return R @ S, np.array(display.get("translation", [0, 0, 0]), dtype=np.float64)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model_chain(path, models_base, vanilla_models=None):
    """Load a model JSON and merge its parent chain (elements, textures, display)."""
    with open(path, "r") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    textures = data.get("textures", {})
    display = data.get("display", {}).get("gui")

    parent = data.get("parent", "")
    if parent:
        parent = parent.replace("minecraft:", "")
        ppath = None
        # Resolve wynn model parents
        if parent.startswith("item/wynn/"):
            ppath = models_base / (parent.removeprefix("item/wynn/") + ".json")
        else:
            # Try wynn models dir first, then vanilla
            rel = parent.replace("/", "\\") + ".json"
            candidate = models_base.parent / rel
            if candidate.exists():
                ppath = candidate
            elif vanilla_models:
                candidate = vanilla_models / rel
                if candidate.exists():
                    ppath = candidate

        if ppath and ppath.exists():
            p_elems, p_tex, p_disp = load_model_chain(
                ppath, models_base, vanilla_models
            )
            if not elements:
                elements = p_elems
            merged = dict(p_tex)
            merged.update(textures)
            textures = merged
            if display is None:
                display = p_disp

    return elements, textures, display


def resolve_tex_ref(ref, textures_dict, textures_bases, cache):
    """Follow #ref chain and return a numpy RGBA array.
    textures_bases is a list of directories to search (wynn first, vanilla fallback).
    """
    seen = set()
    while ref.startswith("#"):
        key = ref[1:]
        if key in seen:
            return None
        seen.add(key)
        ref = textures_dict.get(key, "")
    if not ref:
        return None

    ref = ref.replace("minecraft:", "")
    if ref in cache:
        return cache[ref]

    rel = ref.replace("/", "\\") + ".png"
    for base in textures_bases:
        path = base / rel
        if path.exists():
            img = Image.open(path).convert("RGBA")
            w, h = img.size
            if h > w:
                img = img.crop((0, 0, w, w))
            arr = np.array(img)
            cache[ref] = arr
            return arr

    return None


# ---------------------------------------------------------------------------
# Mesh building
# ---------------------------------------------------------------------------

def build_face_quad(frm, to, face_name, face_data, textures_dict,
                    textures_bases, tex_cache):
    """
    Build a single face quad: 4 vertices + 4 UV coords + texture + shade.
    Returns None if face texture cannot be resolved.
    """
    tex_ref = face_data.get("texture", "")
    tex_arr = resolve_tex_ref(tex_ref, textures_dict, textures_bases, tex_cache)
    if tex_arr is None:
        return None

    x1, y1, z1 = frm
    x2, y2, z2 = to
    tex_h, tex_w = tex_arr.shape[:2]

    # Vertex positions for each face (4 verts, UV-corner order)
    face_verts = {
        "north": [(x2,y2,z1), (x1,y2,z1), (x1,y1,z1), (x2,y1,z1)],
        "south": [(x1,y2,z2), (x2,y2,z2), (x2,y1,z2), (x1,y1,z2)],
        "east":  [(x2,y2,z2), (x2,y2,z1), (x2,y1,z1), (x2,y1,z2)],
        "west":  [(x1,y2,z1), (x1,y2,z2), (x1,y1,z2), (x1,y1,z1)],
        "up":    [(x1,y2,z1), (x2,y2,z1), (x2,y2,z2), (x1,y2,z2)],
        "down":  [(x1,y1,z2), (x2,y1,z2), (x2,y1,z1), (x1,y1,z1)],
    }

    verts = np.array(face_verts[face_name], dtype=np.float64)

    # UV coordinates (0-16 model space -> pixel space)
    uv = face_data.get("uv")
    if uv is None:
        # Auto-generate default UV from geometry
        defaults = {
            "north": [16-x2, 16-y2, 16-x1, 16-y1],
            "south": [x1, 16-y2, x2, 16-y1],
            "east":  [16-z2, 16-y2, 16-z1, 16-y1],
            "west":  [z1, 16-y2, z2, 16-y1],
            "up":    [x1, z1, x2, z2],
            "down":  [x1, 16-z2, x2, 16-z1],
        }
        uv = defaults[face_name]

    u1, v1, u2, v2 = uv
    # Convert from 0-16 model UV space to pixel coordinates
    px_per_uv = tex_w / 16.0
    py_per_uv = tex_h / 16.0
    u1p, v1p = u1 * px_per_uv, v1 * py_per_uv
    u2p, v2p = u2 * px_per_uv, v2 * py_per_uv

    # 4 UV corners: TL, TR, BR, BL
    uvs = np.array([
        [u1p, v1p], [u2p, v1p], [u2p, v2p], [u1p, v2p]
    ], dtype=np.float64)

    # Apply UV rotation (rotate which vertex gets which UV corner)
    rot = face_data.get("rotation", 0)
    if rot:
        shift = rot // 90
        uvs = np.roll(uvs, shift, axis=0)

    normal = np.cross(verts[1] - verts[0], verts[3] - verts[0])
    shade = FACE_SHADE.get(face_name, 0.7)

    return verts, uvs, tex_arr, shade, normal


def apply_element_rotation(verts, rotation):
    """Apply per-element rotation around the specified origin."""
    angle = rotation["angle"]
    axis = rotation["axis"]
    origin = np.array(rotation["origin"], dtype=np.float64)

    R = rot_matrix(angle, axis)
    centered = verts - origin
    rotated = centered @ R.T
    return rotated + origin


def build_all_faces(elements, textures_dict, textures_bases, tex_cache):
    """Build all renderable face quads from model elements."""
    faces = []
    for elem in elements:
        frm = elem["from"]
        to = elem["to"]
        rotation = elem.get("rotation")

        for face_name, face_data in elem.get("faces", {}).items():
            result = build_face_quad(
                frm, to, face_name, face_data,
                textures_dict, textures_bases, tex_cache
            )
            if result is None:
                continue
            verts, uvs, tex_arr, shade, normal = result

            if rotation:
                verts = apply_element_rotation(verts, rotation)
                # Recompute normal after rotation
                normal = np.cross(verts[1] - verts[0], verts[3] - verts[0])

            faces.append((verts, uvs, tex_arr, shade, normal))

    return faces


# ---------------------------------------------------------------------------
# Rasterizer
# ---------------------------------------------------------------------------

def rasterize_triangle(zbuf, cbuf, v0, v1, v2, uv0, uv1, uv2,
                       tex_arr, shade):
    """Rasterize a single textured triangle with z-buffer (numpy-vectorized)."""
    h, w = zbuf.shape
    tex_h, tex_w = tex_arr.shape[:2]

    min_x = max(0, int(np.floor(min(v0[0], v1[0], v2[0]))))
    max_x = min(w - 1, int(np.ceil(max(v0[0], v1[0], v2[0]))))
    min_y = max(0, int(np.floor(min(v0[1], v1[1], v2[1]))))
    max_y = min(h - 1, int(np.ceil(max(v0[1], v1[1], v2[1]))))
    if min_x > max_x or min_y > max_y:
        return

    # Pixel grid
    ys, xs = np.mgrid[min_y:max_y + 1, min_x:max_x + 1]
    px = xs.astype(np.float64) + 0.5
    py = ys.astype(np.float64) + 0.5

    # Barycentric coordinates
    e01 = v1[:2] - v0[:2]
    e02 = v2[:2] - v0[:2]
    denom = e01[0] * e02[1] - e02[0] * e01[1]
    if abs(denom) < 1e-10:
        return
    inv = 1.0 / denom

    dx = px - v0[0]
    dy = py - v0[1]
    u = (dx * e02[1] - dy * e02[0]) * inv
    v = (dy * e01[0] - dx * e01[1]) * inv
    bw = 1.0 - u - v

    mask = (u >= 0) & (v >= 0) & (bw >= 0)
    if not np.any(mask):
        return

    # Interpolate Z
    z = bw * v0[2] + u * v1[2] + v * v2[2]

    # Z-test (larger Z = closer to camera in our projection)
    slc = (slice(min_y, max_y + 1), slice(min_x, max_x + 1))
    z_mask = mask & (z > zbuf[slc])
    if not np.any(z_mask):
        return

    # Interpolate UV
    tex_u = bw * uv0[0] + u * uv1[0] + v * uv2[0]
    tex_v = bw * uv0[1] + u * uv1[1] + v * uv2[1]

    # Sample texture (nearest neighbor, clamp)
    tx = np.clip(tex_u.astype(np.int32), 0, tex_w - 1)
    ty = np.clip(tex_v.astype(np.int32), 0, tex_h - 1)

    # Get colors for valid pixels
    vy = ys[z_mask]
    vx = xs[z_mask]
    colors = tex_arr[ty[z_mask], tx[z_mask]].astype(np.float64)

    # Alpha test
    alpha_ok = colors[:, 3] > 0
    if not np.any(alpha_ok):
        return

    vy, vx = vy[alpha_ok], vx[alpha_ok]
    vz = z[z_mask][alpha_ok]
    colors = colors[alpha_ok]

    # Apply shading
    colors[:, :3] = np.clip(colors[:, :3] * shade, 0, 255)

    zbuf[vy, vx] = vz
    cbuf[vy, vx] = colors.astype(np.uint8)


def render_faces(faces, view_mat, view_trans, size):
    """Transform and rasterize all faces into an RGBA image."""
    zbuf = np.full((size, size), -np.inf, dtype=np.float64)
    cbuf = np.zeros((size, size, 4), dtype=np.uint8)

    # Transform all face vertices (two passes: measure bbox, then rasterize)
    view_space = []
    for verts, uvs, tex_arr, shade, normal in faces:
        # Center model (0-16 space -> centered at origin)
        centered = verts - 8.0
        # Apply GUI rotation + scale
        tv = (centered @ view_mat.T) + view_trans
        # Transform normal for back-face culling
        tn = normal @ view_mat.T

        # Back-face cull: skip if normal points away from camera (+Z)
        if tn[2] <= 0:
            continue

        view_space.append((tv, uvs, tex_arr, shade))

    if not view_space:
        return Image.fromarray(cbuf, "RGBA")

    # Compute bounding box of all visible vertices in view space
    all_xy = np.concatenate([tv[:, :2] for tv, *_ in view_space])
    max_extent = np.max(np.abs(all_xy))
    # Fit model into canvas with 5% padding on each side
    padding = 0.90
    if max_extent > 0:
        scale = (size / 2.0) * padding / max_extent
    else:
        scale = size / 16.0

    # Project to screen
    transformed = []
    for tv, uvs, tex_arr, shade in view_space:
        screen = np.zeros_like(tv)
        screen[:, 0] = tv[:, 0] * scale + size / 2.0
        screen[:, 1] = -tv[:, 1] * scale + size / 2.0
        screen[:, 2] = tv[:, 2]  # keep Z for depth

        transformed.append((screen, uvs, tex_arr, shade))

    # Sort by average Z (painter's algorithm backup - z-buffer is primary)
    transformed.sort(key=lambda t: np.mean(t[0][:, 2]))

    for screen, uvs, tex_arr, shade in transformed:
        # Split quad into 2 triangles and rasterize
        for tri_idx in [(0, 1, 2), (0, 2, 3)]:
            i, j, k = tri_idx
            rasterize_triangle(
                zbuf, cbuf,
                screen[i], screen[j], screen[k],
                uvs[i], uvs[j], uvs[k],
                tex_arr, shade,
            )

    return Image.fromarray(cbuf, "RGBA")


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

def snake_to_camel(name):
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def model_to_icon_name(rel_path):
    """Convert a model's relative path to an output icon filename."""
    parts = Path(rel_path).with_suffix("").parts
    cat = parts[0] if len(parts) > 1 else ""
    stem = parts[-1]

    # Weapons: weapon/archer/bow_air_a -> bow.air1.webp
    if cat == "weapon" and len(parts) == 3:
        m = re.match(r"^(\w+?)_(.+?)_([abc])$", stem)
        if m:
            weapon, element, tier = m.groups()
            return f"{weapon}.{element}{TIER_MAP[tier]}.webp"
        m = re.match(r"^(\w+?)_(basic_.+)$", stem)
        if m:
            weapon, variant = m.groups()
            return f"{weapon}.{snake_to_camel(variant)}.webp"
        return None

    # Skins: skin/bow/abyssal_bow -> skin.abyssalBow.webp
    if cat == "skin":
        return f"skin.{snake_to_camel(stem)}.webp"

    # Root-level models: beam.json -> misc.beam.webp
    if not cat:
        return f"misc.{snake_to_camel(stem)}.webp"

    # Generic: prop/barrel_oak -> prop.barrelOak.webp
    return f"{cat}.{snake_to_camel(stem)}.webp"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _has_elements(path, models_base, vanilla_models=None, depth=0):
    """Check if a model has elements directly or via parent chain."""
    if depth > 10:
        return False
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    if "elements" in data:
        return True
    parent = data.get("parent", "").replace("minecraft:", "")
    if parent.startswith("item/wynn/"):
        ppath = models_base / (parent.removeprefix("item/wynn/") + ".json")
        return _has_elements(ppath, models_base, vanilla_models, depth + 1)
    # Check non-wynn parents (wynn models dir, then vanilla)
    if parent:
        rel = parent.replace("/", "\\") + ".json"
        for base in [models_base.parent, vanilla_models]:
            if base is None:
                continue
            candidate = base / rel
            if candidate.exists():
                return _has_elements(
                    candidate, models_base, vanilla_models, depth + 1
                )
    return False


def collect_3d_models(models_base, vanilla_models=None):
    """Find all model JSONs with 'elements' (directly or inherited)."""
    results = []
    for path in sorted(models_base.rglob("*.json")):
        rel = path.relative_to(models_base)
        cat = rel.parts[0] if len(rel.parts) > 1 else ""

        if cat in SKIP_CATEGORIES:
            continue

        if _has_elements(path, models_base, vanilla_models):
            results.append(path)
    return results


def render_model(model_path, models_base, textures_bases, size,
                 vanilla_models=None):
    """Render a single model to a PIL Image. Returns None on failure."""
    tex_cache = {}
    elements, textures, gui_display = load_model_chain(
        model_path, models_base, vanilla_models
    )

    if not elements:
        return None

    if gui_display is None:
        gui_display = DEFAULT_GUI

    faces = build_all_faces(elements, textures, textures_bases, tex_cache)
    if not faces:
        return None

    view_mat, view_trans = build_gui_matrix(gui_display)
    return render_faces(faces, view_mat, view_trans, size)


def main():
    parser = argparse.ArgumentParser(
        description="Render 3D Wynncraft models as .webp icons"
    )
    parser.add_argument(
        "--models", type=Path, default=DEFAULT_MODELS,
        help="Wynn models directory",
    )
    parser.add_argument(
        "--textures", type=Path, default=DEFAULT_TEXTURES,
        help="Textures root directory",
    )
    parser.add_argument(
        "--vanilla", type=Path, default=DEFAULT_VANILLA,
        help="Vanilla Minecraft assets directory (fallback textures/models)",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help="Output directory for .webp icons",
    )
    parser.add_argument(
        "--size", type=int, default=RENDER_SIZE,
        help="Output icon size in pixels (default: 128)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview output filenames without rendering",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing icons (default: skip)",
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Only render models from this category (e.g. 'prop', 'weapon')",
    )
    args = parser.parse_args()

    if not args.models.exists():
        print(f"Error: models directory not found: {args.models}")
        sys.exit(1)

    args.out.mkdir(parents=True, exist_ok=True)

    # Build texture search path: wynn pack first, vanilla fallback
    vanilla_textures = args.vanilla / "textures" if args.vanilla.exists() else None
    textures_bases = [args.textures]
    if vanilla_textures and vanilla_textures.exists():
        textures_bases.append(vanilla_textures)

    vanilla_models = args.vanilla / "models" if args.vanilla.exists() else None

    print(f"Models:   {args.models}")
    print(f"Textures: {args.textures}")
    print(f"Vanilla:  {args.vanilla}")
    print(f"Output:   {args.out}")
    print(f"Size:     {args.size}x{args.size}")
    print(f"Mode:     {'dry-run' if args.dry_run else 'write'}")

    models = collect_3d_models(args.models, vanilla_models)
    print(f"Found {len(models)} models with 3D geometry\n")

    for model_path in models:
        rel = model_path.relative_to(args.models)
        cat = rel.parts[0] if len(rel.parts) > 1 else ""

        if args.category and cat != args.category:
            continue

        icon_name = model_to_icon_name(str(rel))
        if icon_name is None:
            continue

        dest = args.out / icon_name

        if not args.overwrite and dest.exists():
            stats.skipped += 1
            continue

        if args.dry_run:
            print(f"  [dry-run] {icon_name}")
            stats.created += 1
            continue

        img = render_model(
            model_path, args.models, textures_bases, args.size, vanilla_models
        )
        if img is None:
            print(f"  warn  failed to render: {rel}")
            stats.warnings += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(dest), "WEBP", quality=90, method=6)
        print(f"  ok    {icon_name}")
        stats.created += 1

    stats.summary()


if __name__ == "__main__":
    main()
