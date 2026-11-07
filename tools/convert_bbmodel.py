#!/usr/bin/env python3
"""
Converts the ModelEngine .bbmodel blueprints of TROLLPACK into GeckoLib assets:

  assets/trollpack/geo/entity/<id>.geo.json
  assets/trollpack/animations/entity/<id>.animation.json
  assets/trollpack/textures/entity/<id>.png            (all textures of a model merged into one atlas)
  assets/trollpack/textures/entity/<id>_glowmask.png   (only when the pack ships an `_e` emissive texture)
  tools/model_meta.json                                (hitbox sizes, hidden bones, alt-part bones)

Usage:  python3 convert_bbmodel.py <unzipped TROLLPACK dir> <mod resources/assets/trollpack dir>

Conventions (same as Blockbench's Bedrock exporter, which is what GeckoLib reads):
  * X axis is mirrored:  pivot/origin x -> -x,  rotation (x,y,z) -> (-x,-y,z),  anim position x -> -x
  * ModelEngine "changepart" alternatives (the models in *_parts.bbmodel) become extra bones that are
    siblings of the bone they replace and receive a copy of that bone's animation. They are hidden by
    default and toggled from Java.
"""
import json, os, re, sys
from PIL import Image

SRC = sys.argv[1]
OUT = sys.argv[2]
BP = os.path.join(SRC, "plugin/ModelEngine/blueprints")
TEX = os.path.join(SRC, "plugin/ModelEngine/resource pack/assets/modelengine/textures/entity")

# model id -> (main blueprint, optional parts blueprint, alt-part -> base-bone resolver key)
MODELS = {
    "troll":        ("lr_troll", "lr_troll_parts", "troll"),
    "troll_elite":  ("lr_troll_elite", None, None),
    "troll_voodoo": ("lr_troll_voodoo", None, None),
    "troll_chief":  ("lr_troll_chief", None, None),
    "troll_pig":    ("lr_troll_pig", None, None),
    "troll_pot":    ("lr_troll_pot_1", "lr_troll_pots_parts", "pot"),
    "troll_totem":  ("lr_troll_totem", None, None),
    "troll_bedmat": ("lr_troll_bedmat", None, None),
    "troll_throne": ("lr_troll_throne", None, None),
}

SKIP_BONES = {"hitbox", "hp_bar", "tag_name"}  # ModelEngine utility bones


def alt_base(kind, name):
    """Return the base bone an alternative part replaces, or None."""
    if kind == "troll":
        m = re.match(r"^[012]_(body)(_fem)?$", name)
        if m: return "body"
        m = re.match(r"^[012]_((left|right)_(arm|forearm|hand|leg|shin|foot))$", name)
        if m: return m.group(1)
        m = re.match(r"^[012]_((left|right)_arm)_armor$", name)
        if m: return m.group(1)
        if re.match(r"^[012]_shield$", name): return "left_forearm"
        if re.match(r"^[012]_spear(_throw)?$", name): return "right_hand"
        if re.match(r"^[012]_\d+$", name): return "h_head"
        if name == "h_tusk_gold": return "h_tusk"
        if name == "h_tusk2_gold": return "h_tusk2"
    if kind == "pot":
        if name in ("pot2", "pot3"): return "pot"
    return None


def load(name):
    with open(os.path.join(BP, name + ".bbmodel")) as f:
        return json.load(f)


def num(v):
    """Keyframe values can be numbers, numeric strings or molang expressions."""
    if isinstance(v, (int, float)):
        return round(float(v), 5)
    try:
        return round(float(str(v).strip()), 5)
    except ValueError:
        return str(v)


def flatten_groups(outliner, els):
    """-> list of dicts(name, parent, group, cubes[]) in depth-first order."""
    out = []

    def walk(node, parent):
        cubes = [els[c] for c in node["children"] if isinstance(c, str)]
        out.append({"name": node["name"], "parent": parent, "group": node, "cubes": cubes})
        for c in node["children"]:
            if not isinstance(c, str):
                walk(c, node["name"])

    for n in outliner:
        if isinstance(n, dict):
            walk(n, None)
    return out


class Atlas:
    """Stacks every texture a model uses into one PNG (GeckoLib only binds one texture per render)."""

    def __init__(self):
        self.entries = []  # (name, Image, e_image or None)
        self.index = {}

    def add(self, name):
        if name in self.index:
            return self.index[name]
        im = Image.open(os.path.join(TEX, name)).convert("RGBA")
        epath = os.path.join(TEX, name[:-4] + "_e.png")
        em = Image.open(epath).convert("RGBA") if os.path.exists(epath) else None
        self.index[name] = len(self.entries)
        self.entries.append((name, im, em))
        return self.index[name]

    def layout(self):
        self.width = max(e[1].width for e in self.entries)
        self.offsets, y = [], 0
        for _, im, _ in self.entries:
            self.offsets.append(y)
            y += im.height
        self.height = y

    def save(self, base):
        atlas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        glow = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        has_glow = False
        for (name, im, em), y in zip(self.entries, self.offsets):
            atlas.paste(im, (0, y))
            if em is not None:
                glow.paste(em, (0, y)); has_glow = True
        atlas.save(base + ".png")
        if has_glow:
            glow.save(base + "_glowmask.png")
        return has_glow


def convert(model_id, main_name, parts_name, kind, meta):
    main = load(main_name)
    sources = [(main, False)]
    if parts_name:
        sources.append((load(parts_name), True))

    atlas = Atlas()
    tex_maps = []  # per source: bbmodel texture index -> (atlas index, scale_x, scale_y)
    for d, _ in sources:
        res = d["resolution"]
        m = {}
        for i, t in enumerate(d["textures"]):
            ai = atlas.add(t["name"])
            im = atlas.entries[ai][1]
            m[i] = (ai, im.width / res["width"], im.height / res["height"])
        tex_maps.append(m)
    atlas.layout()

    bones, hidden, alts = [], [], {}
    hitbox = None
    bone_names = set()
    base_groups = {}

    for si, (d, is_parts) in enumerate(sources):
        els = {e["uuid"]: e for e in d["elements"]}
        groups = flatten_groups(d["outliner"], els)
        for g in groups:
            name = g["name"]
            if not is_parts:
                if name == "hitbox":
                    for c in g["cubes"]:
                        f, t = c["from"], c["to"]
                        hitbox = {"width": max(t[0] - f[0], t[2] - f[2]) / 16.0, "height": (t[1] - f[1]) / 16.0,
                                  "min": f, "max": t}
                    continue
                if name in SKIP_BONES:
                    continue
                if g["group"].get("visibility") is False:
                    hidden.append(name)
            base = alt_base(kind, name) if is_parts else None
            if is_parts and base is None:
                print(f"  [{model_id}] parts group '{name}' has no base bone mapping -> skipped")
                continue

            cubes = []
            for c in g["cubes"]:
                if c.get("visibility") is False:
                    continue
                f, t, o = c["from"], c["to"], c["origin"]
                r = c.get("rotation", [0, 0, 0])
                cube = {
                    "origin": [round(-t[0], 5), round(f[1], 5), round(f[2], 5)],
                    "size": [round(t[0] - f[0], 5), round(t[1] - f[1], 5), round(t[2] - f[2], 5)],
                    "pivot": [round(-o[0], 5), round(o[1], 5), round(o[2], 5)],
                    "uv": {},
                }
                if any(abs(v) > 1e-6 for v in r):
                    cube["rotation"] = [round(-r[0], 5), round(-r[1], 5), round(r[2], 5)]
                if c.get("inflate"):
                    cube["inflate"] = c["inflate"]
                for face, fd in c["faces"].items():
                    if fd.get("texture") is None:
                        continue
                    ai, sx, sy = tex_maps[si][fd["texture"]]
                    u1, v1, u2, v2 = fd["uv"]
                    rot = fd.get("rotation", 0)
                    uvx, uvy = u1 * sx, v1 * sy + atlas.offsets[ai]
                    w, h = (u2 - u1) * sx, (v2 - v1) * sy
                    if rot == 180:  # expressible as flip on both axes
                        uvx, uvy, w, h = uvx + w, uvy + h, -w, -h
                    elif rot in (90, 270) and abs(w) > 1e-6 and abs(h) > 1e-6:
                        meta.setdefault("unsupported_face_rotations", []).append(f"{model_id}:{name}:{face}:{rot}")
                    cube["uv"][face] = {"uv": [round(uvx, 4), round(uvy, 4)], "uv_size": [round(w, 4), round(h, 4)]}
                cubes.append(cube)

            grp = g["group"]
            gr = grp.get("rotation", [0, 0, 0]) or [0, 0, 0]
            go = grp["origin"]
            bone = {
                "name": name,
                "pivot": [round(-go[0], 5), round(go[1], 5), round(go[2], 5)],
            }
            if any(abs(v) > 1e-6 for v in gr):
                bone["rotation"] = [round(-gr[0], 5), round(-gr[1], 5), round(gr[2], 5)]
            if cubes:
                bone["cubes"] = cubes
            if is_parts:
                # sibling of the base bone it replaces
                bone["_alt_of"] = base
                bone["_parent_of_base"] = None  # resolved after all base bones are known
                alts.setdefault(base, []).append(name)
            else:
                if g["parent"] and g["parent"] not in SKIP_BONES:
                    bone["parent"] = g["parent"]
                base_groups[name] = bone
            bones.append(bone)
            bone_names.add(name)

    # resolve parents of alt bones (siblings of base)
    by_name = {b["name"]: b for b in bones}
    for b in bones:
        if "_alt_of" in b:
            base = by_name.get(b.pop("_alt_of"))
            b.pop("_parent_of_base")
            if base is not None and "parent" in base:
                b["parent"] = base["parent"]
            b["_alt_of"] = None
    for b in bones:
        b.pop("_alt_of", None)

    # texture size used by GeckoLib to normalise UVs
    geo = {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {
                "identifier": f"geometry.trollpack.{model_id}",
                "texture_width": atlas.width,
                "texture_height": atlas.height,
                "visible_bounds_width": 4,
                "visible_bounds_height": 4,
                "visible_bounds_offset": [0, 1.5, 0],
            },
            "bones": bones,
        }],
    }
    # alt bones start hidden: tell Java through meta (GeckoLib has no 'hidden' flag in geo json)
    alt_names = [a for v in alts.values() for a in v]

    # ---- animations -----------------------------------------------------------
    d = main
    uuid_to_name = {}

    def collect(nodes):
        for n in nodes:
            if isinstance(n, dict):
                uuid_to_name[n["uuid"]] = n["name"]
                collect(n["children"])

    collect(d["outliner"])
    anims = {}
    for a in d.get("animations", []):
        length = a.get("length", 0)
        loop = a.get("loop", "once")
        entry = {"animation_length": round(length, 5)}
        if loop == "loop":
            entry["loop"] = True
        elif loop == "hold":
            entry["loop"] = "hold_on_last_frame"
        bones_anim = {}
        for uid, an in a.get("animators", {}).items():
            if an.get("type") != "bone":
                continue
            bname = an.get("name") or uuid_to_name.get(uid)
            if bname in SKIP_BONES or bname not in base_groups:
                continue
            chans = {}
            for kf in an.get("keyframes", []):
                ch = kf["channel"]
                if ch not in ("rotation", "position", "scale"):
                    continue
                pts = kf["data_points"]

                def conv(p):
                    v = [num(p.get("x", 0)), num(p.get("y", 0)), num(p.get("z", 0))]
                    if ch == "rotation":
                        v = [(-v[0] if not isinstance(v[0], str) else f"-({v[0]})"),
                             (-v[1] if not isinstance(v[1], str) else f"-({v[1]})"), v[2]]
                    elif ch == "position":
                        v = [(-v[0] if not isinstance(v[0], str) else f"-({v[0]})"), v[1], v[2]]
                    return v

                if kf.get("interpolation") == "step":
                    lerp = "step"
                else:
                    lerp = kf.get("interpolation", "linear")
                val = {}
                if len(pts) >= 2:
                    val["pre"], val["post"] = conv(pts[0]), conv(pts[1])
                else:
                    val["post"] = conv(pts[0])
                if lerp in ("catmullrom", "step"):
                    val["lerp_mode"] = lerp
                chans.setdefault(ch, {})[f"{round(kf['time'], 4):g}"] = val
            if chans:
                for ch in chans:  # time keys sorted
                    chans[ch] = dict(sorted(chans[ch].items(), key=lambda kv: float(kv[0])))
                bones_anim[bname] = chans
        # duplicate for alternative parts
        for base, names in alts.items():
            if base in bones_anim:
                for n in names:
                    bones_anim[n] = bones_anim[base]
        entry["bones"] = bones_anim
        anims[a["name"]] = entry

    os.makedirs(os.path.join(OUT, "geo/entity"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "animations/entity"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "textures/entity"), exist_ok=True)
    with open(os.path.join(OUT, f"geo/entity/{model_id}.geo.json"), "w") as f:
        json.dump(geo, f, separators=(",", ":"))
    with open(os.path.join(OUT, f"animations/entity/{model_id}.animation.json"), "w") as f:
        json.dump({"format_version": "1.8.0", "animations": anims}, f, separators=(",", ":"))
    glow = atlas.save(os.path.join(OUT, f"textures/entity/{model_id}"))

    meta[model_id] = {
        "hitbox": hitbox,
        "hidden_bones": hidden,
        "alt_bones": alts,
        "animations": list(anims.keys()),
        "bones": [b["name"] for b in bones],
        "glowmask": glow,
        "atlas": [atlas.width, atlas.height],
        "textures": [e[0] for e in atlas.entries],
    }
    print(f"{model_id}: {len(bones)} bones, {len(anims)} animations, atlas {atlas.width}x{atlas.height}, glow={glow}")


def main():
    meta = {}
    for mid, (m, p, k) in MODELS.items():
        convert(mid, m, p, k, meta)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_meta.json"), "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
