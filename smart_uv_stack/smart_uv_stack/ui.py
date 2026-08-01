from __future__ import annotations

import bpy


class SMARTUVSTACK_PT_main(bpy.types.Panel):
    bl_label = "Smart UV Stack"
    bl_idname = "SMARTUVSTACK_PT_main"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "UV"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = getattr(context, "object", None)
        return bool(obj and obj.type == "MESH" and context.mode == "EDIT_MESH")

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        settings = context.scene.smart_uv_stack_settings

        col = layout.column(align=True)
        col.operator("smart_uv_stack.detect_similar_islands", icon="VIEWZOOM")
        col.operator("smart_uv_stack.stack_selected_islands", icon="UV")
        col.operator("smart_uv_stack.stack_all_similar_islands", icon="SEQ_STRIP_DUPLICATE")
        col.operator("smart_uv_stack.select_similar_islands", icon="RESTRICT_SELECT_OFF")
        col.operator("smart_uv_stack.clear_groups", icon="TRASH")

        layout.separator()

        box = layout.box()
        box.label(text="Options")
        box.prop(settings, "similarity_threshold", slider=True)
        box.prop(settings, "allow_mirrored_islands")
        box.prop(settings, "ignore_rotation")
        box.prop(settings, "ignore_scale")
        box.prop(settings, "auto_align_rotation")
        box.prop(settings, "auto_scale")
        box.prop(settings, "preserve_active_island")
        box.prop(settings, "show_preview_colors")
        box.prop(settings, "show_group_ids")
