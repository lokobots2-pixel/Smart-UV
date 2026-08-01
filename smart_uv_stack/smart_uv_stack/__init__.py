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
        try:
            bpy.utils.register_class(cls)
        except RuntimeError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except Exception:
                pass
    if not hasattr(bpy.types.Scene, "smart_uv_stack_settings"):
        bpy.types.Scene.smart_uv_stack_settings = bpy.props.PointerProperty(type=SmartUVStackSettings)
    try:
        install_draw_handler()
    except Exception:
        pass


def unregister() -> None:
    try:
        remove_draw_handler()
    except Exception:
        pass
    if hasattr(bpy.types.Scene, "smart_uv_stack_settings"):
        try:
            del bpy.types.Scene.smart_uv_stack_settings
        except Exception:
            pass
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()
