from __future__ import annotations

import bpy
import bmesh

from .drawing import clear_cache, store_cache
from .stacking import get_uv_layer, stack_islands, select_islands, collect_records, group_records


def _context_object(context: bpy.types.Context) -> bpy.types.Object | None:
    obj = getattr(context, "object", None)
    if obj is None or obj.type != "MESH":
        return None
    return obj


def _get_bmesh(context: bpy.types.Context) -> tuple[bmesh.types.BMesh | None, bpy.types.BMLayerItem | None]:
    obj = _context_object(context)
    if obj is None or context.mode != "EDIT_MESH":
        return None, None
    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = get_uv_layer(bm)
    return bm, uv_layer


def _settings(context: bpy.types.Context):
    return context.scene.smart_uv_stack_settings


def _finish(context: bpy.types.Context, obj: bpy.types.Object, bm: bmesh.types.BMesh) -> None:
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    for area in context.screen.areas:
        if area.type == "IMAGE_EDITOR":
            area.tag_redraw()


class SMARTUVSTACK_OT_detect_similar_islands(bpy.types.Operator):
    bl_idname = "smart_uv_stack.detect_similar_islands"
    bl_label = "Detect Similar Islands"
    bl_description = "Detect similar UV islands and cache them for preview"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _context_object(context) is not None and context.mode == "EDIT_MESH"

    def execute(self, context: bpy.types.Context):
        obj = _context_object(context)
        bm, uv_layer = _get_bmesh(context)
        if obj is None or bm is None or uv_layer is None:
            self.report({"WARNING"}, "No active mesh UV layer found")
            return {"CANCELLED"}

        settings = _settings(context)
        records = collect_records(bm, uv_layer, selected_only=False, similarity_threshold=settings.similarity_threshold)
        groups = group_records(records, settings.similarity_threshold)
        reference_indices = {i: 0 for i in range(len(groups))}
        store_cache(obj, groups, reference_indices)
        self.report({"INFO"}, f"Detected {len(groups)} UV island groups")
        _finish(context, obj, bm)
        return {"FINISHED"}


class SMARTUVSTACK_OT_stack_selected_islands(bpy.types.Operator):
    bl_idname = "smart_uv_stack.stack_selected_islands"
    bl_label = "Stack Selected Islands"
    bl_description = "Stack similar islands among the selected UV islands"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _context_object(context) is not None and context.mode == "EDIT_MESH"

    def execute(self, context: bpy.types.Context):
        obj = _context_object(context)
        bm, uv_layer = _get_bmesh(context)
        if obj is None or bm is None or uv_layer is None:
            self.report({"WARNING"}, "No active mesh UV layer found")
            return {"CANCELLED"}

        settings = _settings(context)
        groups, stacked_count = stack_islands(
            bm=bm,
            uv_layer=uv_layer,
            selected_only=True,
            similarity_threshold=settings.similarity_threshold,
            allow_mirrored=settings.allow_mirrored_islands,
            apply_rotation=settings.auto_align_rotation and not settings.ignore_rotation,
            apply_scale=settings.auto_scale and not settings.ignore_scale,
            preserve_active_island=settings.preserve_active_island,
        )
        reference_indices = {i: 0 for i in range(len(groups))}
        store_cache(obj, groups, reference_indices)
        self.report({"INFO"}, f"Stacked {stacked_count} islands")
        _finish(context, obj, bm)
        return {"FINISHED"}


class SMARTUVSTACK_OT_stack_all_similar_islands(bpy.types.Operator):
    bl_idname = "smart_uv_stack.stack_all_similar_islands"
    bl_label = "Stack All Similar Islands"
    bl_description = "Stack all similar islands in the mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _context_object(context) is not None and context.mode == "EDIT_MESH"

    def execute(self, context: bpy.types.Context):
        obj = _context_object(context)
        bm, uv_layer = _get_bmesh(context)
        if obj is None or bm is None or uv_layer is None:
            self.report({"WARNING"}, "No active mesh UV layer found")
            return {"CANCELLED"}

        settings = _settings(context)
        groups, stacked_count = stack_islands(
            bm=bm,
            uv_layer=uv_layer,
            selected_only=False,
            similarity_threshold=settings.similarity_threshold,
            allow_mirrored=settings.allow_mirrored_islands,
            apply_rotation=settings.auto_align_rotation and not settings.ignore_rotation,
            apply_scale=settings.auto_scale and not settings.ignore_scale,
            preserve_active_island=settings.preserve_active_island,
        )
        reference_indices = {i: 0 for i in range(len(groups))}
        store_cache(obj, groups, reference_indices)
        self.report({"INFO"}, f"Stacked {stacked_count} islands")
        _finish(context, obj, bm)
        return {"FINISHED"}


class SMARTUVSTACK_OT_select_similar_islands(bpy.types.Operator):
    bl_idname = "smart_uv_stack.select_similar_islands"
    bl_label = "Select Similar Islands"
    bl_description = "Select islands that match the active island"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _context_object(context) is not None and context.mode == "EDIT_MESH"

    def execute(self, context: bpy.types.Context):
        obj = _context_object(context)
        bm, uv_layer = _get_bmesh(context)
        if obj is None or bm is None or uv_layer is None:
            self.report({"WARNING"}, "No active mesh UV layer found")
            return {"CANCELLED"}

        settings = _settings(context)
        groups, selected_count = select_islands(
            bm=bm,
            uv_layer=uv_layer,
            similarity_threshold=settings.similarity_threshold,
            allow_mirrored=settings.allow_mirrored_islands,
            active_only=True,
        )
        reference_indices = {i: 0 for i in range(len(groups))}
        store_cache(obj, groups, reference_indices)
        self.report({"INFO"}, f"Selected {selected_count} faces")
        _finish(context, obj, bm)
        return {"FINISHED"}


class SMARTUVSTACK_OT_clear_groups(bpy.types.Operator):
    bl_idname = "smart_uv_stack.clear_groups"
    bl_label = "Clear Groups"
    bl_description = "Clear cached detection data and preview overlays"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _context_object(context) is not None

    def execute(self, context: bpy.types.Context):
        clear_cache()
        for area in context.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.tag_redraw()
        self.report({"INFO"}, "Cleared cached groups")
        return {"FINISHED"}
