from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import bpy
import bmesh
from mathutils import Vector

from .geometry import (
    IslandRecord,
    build_island_record,
    component_faces_from_bmesh,
    island_score,
    best_transform_to_reference,
    normalize_step,
)


@dataclass(slots=True)
class StackingResult:
    groups: list[list[IslandRecord]]
    reference_by_group: dict[int, int]


def get_uv_layer(bm: bpy.types.BMesh) -> bpy.types.BMLayerItem | None:
    uv_layers = bm.loops.layers.uv
    if not uv_layers:
        return None
    return uv_layers.active or uv_layers[0]


def collect_records(
    bm: bpy.types.BMesh,
    uv_layer: bpy.types.BMLayerItem,
    selected_only: bool,
    similarity_threshold: float,
) -> list[IslandRecord]:
    components = component_faces_from_bmesh(bm, uv_layer, selected_only=selected_only)
    records: list[IslandRecord] = []
    for idx, faces in enumerate(components):
        if not faces:
            continue
        records.append(build_island_record(idx, faces, uv_layer, similarity_threshold))
    return records


def group_records(records: list[IslandRecord], similarity_threshold: float) -> list[list[IslandRecord]]:
    if not records:
        return []

    parent = list(range(len(records)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    limit = max(0.0, 1.0 - (similarity_threshold / 100.0))

    for i, rec in enumerate(records):
        for j in range(i + 1, len(records)):
            other = records[j]
            if len(rec.face_indices) != len(other.face_indices):
                continue
            if rec.signature == other.signature:
                union(i, j)
                continue
            score = island_score(rec, other, similarity_threshold)
            if score <= limit:
                union(i, j)

    buckets: dict[int, list[IslandRecord]] = {}
    for idx, rec in enumerate(records):
        root = find(idx)
        buckets.setdefault(root, []).append(rec)

    return list(buckets.values())


def choose_reference(group: list[IslandRecord], active_face: bpy.types.BMFace | None, preserve_active: bool) -> IslandRecord:
    if preserve_active and active_face is not None:
        for rec in group:
            if active_face.index in rec.face_indices:
                return rec
    return group[0]


def apply_transform(
    island: IslandRecord,
    reference: IslandRecord,
    uv_layer: bpy.types.BMLayerItem,
    allow_mirrored: bool,
    apply_rotation: bool,
    apply_scale: bool,
) -> bool:
    transform = best_transform_to_reference(
        reference=reference,
        candidate=island,
        allow_mirrored=allow_mirrored,
        apply_rotation=apply_rotation,
        apply_scale=apply_scale,
    )
    if transform is None:
        return False

    cand_basis_x, cand_basis_y, scale_ratio = transform
    ref_basis_x, ref_basis_y = reference.basis_x, reference.basis_y
    cand_centroid = island.centroid

    for face in island.faces:
        for loop in face.loops:
            uv = loop[uv_layer].uv
            rel = uv - cand_centroid
            x = rel.dot(cand_basis_x)
            y = rel.dot(cand_basis_y)
            new_uv = reference.centroid + ref_basis_x * (x * scale_ratio) + ref_basis_y * (y * scale_ratio)
            loop[uv_layer].uv = new_uv

    return True


def stack_islands(
    bm: bpy.types.BMesh,
    uv_layer: bpy.types.BMLayerItem,
    selected_only: bool,
    similarity_threshold: float,
    allow_mirrored: bool,
    apply_rotation: bool,
    apply_scale: bool,
    preserve_active_island: bool,
) -> tuple[list[list[IslandRecord]], int]:
    records = collect_records(bm, uv_layer, selected_only=selected_only, similarity_threshold=similarity_threshold)
    groups = group_records(records, similarity_threshold)

    active_face = bm.faces.active
    stacked_count = 0

    for group in groups:
        if not group:
            continue
        reference = choose_reference(group, active_face, preserve_active_island)
        for island in group:
            if island is reference:
                continue
            if apply_transform(
                island,
                reference,
                uv_layer,
                allow_mirrored=allow_mirrored,
                apply_rotation=apply_rotation,
                apply_scale=apply_scale,
            ):
                stacked_count += 1

    return groups, stacked_count


def select_islands(
    bm: bpy.types.BMesh,
    uv_layer: bpy.types.BMLayerItem,
    similarity_threshold: float,
    allow_mirrored: bool,
    active_only: bool = True,
) -> tuple[list[list[IslandRecord]], int]:
    records = collect_records(bm, uv_layer, selected_only=False, similarity_threshold=similarity_threshold)
    groups = group_records(records, similarity_threshold)
    active_face = bm.faces.active

    target_group: list[IslandRecord] | None = None
    if active_only and active_face is not None:
        for group in groups:
            for rec in group:
                if active_face.index in rec.face_indices:
                    target_group = group
                    break
            if target_group is not None:
                break

    if target_group is None and groups:
        target_group = groups[0]

    selected = 0
    for face in bm.faces:
        face.select = False
        for loop in face.loops:
            loop[uv_layer].select = False
            loop[uv_layer].select_edge = False

    if target_group is not None:
        face_indices = {idx for rec in target_group for idx in rec.face_indices}
        for face in bm.faces:
            if face.index in face_indices:
                face.select = True
                selected += 1
                for loop in face.loops:
                    loop[uv_layer].select = True
                    loop[uv_layer].select_edge = True

    return groups, selected
