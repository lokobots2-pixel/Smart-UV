from __future__ import annotations

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import PropertyGroup


def _tag_redraw(context: bpy.types.Context | None) -> None:
    if context is None:
        return
    window = getattr(context, "window", None)
    if window is None:
        return
    for area in window.screen.areas:
        if area.type == "IMAGE_EDITOR":
            area.tag_redraw()


class SmartUVStackSettings(PropertyGroup):
    similarity_threshold: FloatProperty(
        name="Similarity Threshold",
        description="How close two islands must be to be considered a match",
        min=0.0,
        max=100.0,
        default=92.0,
        subtype="PERCENTAGE",
        update=_tag_redraw,
    )
    allow_mirrored_islands: BoolProperty(
        name="Allow Mirrored Islands",
        description="Treat mirrored islands as matches",
        default=True,
        update=_tag_redraw,
    )
    ignore_rotation: BoolProperty(
        name="Ignore Rotation",
        description="Do not rotate islands during stacking",
        default=False,
        update=_tag_redraw,
    )
    ignore_scale: BoolProperty(
        name="Ignore Scale",
        description="Do not scale islands during stacking",
        default=False,
        update=_tag_redraw,
    )
    auto_align_rotation: BoolProperty(
        name="Auto Align Rotation",
        description="Rotate matching islands to the reference orientation",
        default=True,
        update=_tag_redraw,
    )
    auto_scale: BoolProperty(
        name="Auto Scale",
        description="Scale matching islands to the reference island",
        default=False,
        update=_tag_redraw,
    )
    preserve_active_island: BoolProperty(
        name="Preserve Active Island",
        description="Use the active island as the reference when possible",
        default=True,
        update=_tag_redraw,
    )
    show_preview_colors: BoolProperty(
        name="Show Preview Colors",
        description="Draw group outlines in the UV Editor",
        default=True,
        update=_tag_redraw,
    )
    show_group_ids: BoolProperty(
        name="Show Group IDs",
        description="Display group numbers in the UV Editor",
        default=True,
        update=_tag_redraw,
    )
    max_preview_groups: IntProperty(
        name="Preview Group Limit",
        description="Maximum number of groups drawn for preview",
        min=1,
        max=4096,
        default=256,
        update=_tag_redraw,
    )
