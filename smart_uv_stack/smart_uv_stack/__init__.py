from __future__ import annotations

bl_info = {
    "name": "Smart UV Stack",
    "author": "OpenAI",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "UV Editor > Sidebar > UV",
    "description": "Detects similar UV islands and stacks them with a single click.",
    "category": "UV",
}

import bpy

from .properties import SmartUVStackSettings
from .operators import (
    SMARTUVSTACK_OT_clear_groups,
    SMARTUVSTACK_OT_detect_similar_islands,
    SMARTUVSTACK_OT_select_similar_islands,
    SMARTUVSTACK_OT_stack_all_similar_islands,
    SMARTUVSTACK_OT_stack_selected_islands,
)
from .ui import SMARTUVSTACK_PT_main
from .drawing import install_draw_handler, remove_draw_handler


CLASSES = (
    SmartUVStackSettings,
    SMARTUVSTACK_OT_detect_similar_islands,
    SMARTUVSTACK_OT_stack_selected_islands,
    SMARTUVSTACK_OT_stack_all_similar_islands,
    SMARTUVSTACK_OT_select_similar_islands,
    SMARTUVSTACK_OT_clear_groups,
    SMARTUVSTACK_PT_main,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.smart_uv_stack_settings = bpy.props.PointerProperty(type=SmartUVStackSettings)
    install_draw_handler()


def unregister() -> None:
    remove_draw_handler()
    if hasattr(bpy.types.Scene, "smart_uv_stack_settings"):
        del bpy.types.Scene.smart_uv_stack_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
