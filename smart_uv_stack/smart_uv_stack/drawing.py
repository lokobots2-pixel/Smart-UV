from __future__ import annotations

from dataclasses import dataclass

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from .geometry import IslandRecord


@dataclass(slots=True)
class CacheEntry:
    object_key: tuple[str, str]
    groups: list[list[IslandRecord]]
    reference_indices: dict[int, int]


CACHE: dict[tuple[str, str], CacheEntry] = {}
_DRAW_HANDLER = None

PALETTE = [
    (0.93, 0.34, 0.34, 0.55),
    (0.28, 0.71, 0.96, 0.55),
    (0.31, 0.86, 0.43, 0.55),
    (0.96, 0.72, 0.24, 0.55),
    (0.74, 0.45, 0.95, 0.55),
    (0.26, 0.88, 0.82, 0.55),
    (0.98, 0.56, 0.79, 0.55),
    (0.86, 0.86, 0.86, 0.55),
]


def object_key(obj: bpy.types.Object | None) -> tuple[str, str]:
    if obj is None or obj.type != "MESH" or obj.data is None:
        return ("", "")
    return (obj.name_full, obj.data.name_full)


def store_cache(obj: bpy.types.Object, groups: list[list[IslandRecord]], reference_indices: dict[int, int] | None = None) -> None:
    key = object_key(obj)
    CACHE[key] = CacheEntry(key, groups, reference_indices or {})


def clear_cache() -> None:
    CACHE.clear()


def draw_text(text: str, x: float, y: float, size: int = 12) -> None:
    try:
        font_id = 0
        blf.size(font_id, size, 72)
        blf.position(font_id, x + 4.0, y + 4.0, 0.0)
        blf.draw(font_id, text)
    except Exception:
        return


def draw_callback() -> None:
    context = bpy.context
    area = getattr(context, "area", None)
    region = getattr(context, "region", None)
    space = getattr(context, "space_data", None)
    scene = getattr(context, "scene", None)

    if area is None or region is None or space is None or scene is None:
        return
    if area.type != "IMAGE_EDITOR":
        return

    settings = getattr(scene, "smart_uv_stack_settings", None)
    if settings is None:
        return
    if not settings.show_preview_colors and not settings.show_group_ids:
        return

    key = object_key(getattr(context, "object", None))
    entry = CACHE.get(key)
    if entry is None:
        return

    v2d = getattr(region, "view2d", None)
    if v2d is None:
        return

    try:
        shader = gpu.shader.from_builtin("2D_UNIFORM_COLOR")
    except Exception:
        return

    gpu.state.blend_set("ALPHA")

    max_groups = settings.max_preview_groups
    for group_index, group in enumerate(entry.groups[:max_groups]):
        color = PALETTE[group_index % len(PALETTE)]
        ref_idx = entry.reference_indices.get(group_index, 0)

        for island_index, island in enumerate(group):
            face_color = (1.0, 0.82, 0.15, 0.95) if island_index == ref_idx else color
            if settings.show_preview_colors:
                for face_record in island.face_records:
                    coords = []
                    for v in face_record.uv_coords:
                        try:
                            pt = v2d.view_to_region(v.x, v.y, clip=False)
                        except Exception:
                            pt = None
                        if pt is None:
                            continue
                        coords.append((pt[0], pt[1]))
                    if len(coords) < 2:
                        continue
                    coords.append(coords[0])
                    batch = batch_for_shader(shader, "LINE_STRIP", {"pos": coords})
                    shader.bind()
                    shader.uniform_float("color", face_color)
                    batch.draw(shader)

            if settings.show_group_ids and island.all_uvs:
                cx = sum(v.x for v in island.all_uvs) / max(1, len(island.all_uvs))
                cy = sum(v.y for v in island.all_uvs) / max(1, len(island.all_uvs))
                try:
                    x, y = v2d.view_to_region(cx, cy, clip=False)
                    draw_text(f"G{group_index + 1}", x, y, 11)
                except Exception:
                    continue


def install_draw_handler() -> None:
    global _DRAW_HANDLER
    if _DRAW_HANDLER is not None:
        return
    try:
        _DRAW_HANDLER = bpy.types.SpaceImageEditor.draw_handler_add(draw_callback, (), "WINDOW", "POST_PIXEL")
    except Exception:
        _DRAW_HANDLER = None


def remove_draw_handler() -> None:
    global _DRAW_HANDLER
    if _DRAW_HANDLER is None:
        return
    try:
        bpy.types.SpaceImageEditor.draw_handler_remove(_DRAW_HANDLER, "WINDOW")
    except Exception:
        pass
    finally:
        _DRAW_HANDLER = None
