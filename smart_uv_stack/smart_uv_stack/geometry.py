from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from hashlib import blake2b
import math
from typing import Dict, Sequence

import bpy
import bmesh
from mathutils import Vector


EPS = 1e-8


@dataclass(slots=True)
class FaceRecord:
    face_index: int
    uv_coords: list[Vector]
    descriptor: tuple
    boundary_edges: int


@dataclass(slots=True)
class IslandRecord:
    island_index: int
    face_indices: list[int]
    faces: list[bmesh.types.BMFace]
    face_records: list[FaceRecord]
    all_uvs: list[Vector]
    centroid: Vector
    scale: float
    basis_x: Vector
    basis_y: Vector
    signature: str


def stable_digest(data: object, size: int = 16) -> str:
    payload = repr(data).encode("utf8", "replace")
    return blake2b(payload, digest_size=size).hexdigest()


def uv_distance(a: Vector, b: Vector) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def poly_area(uvs: Sequence[Vector]) -> float:
    if len(uvs) < 3:
        return 0.0
    area = 0.0
    for i in range(len(uvs)):
        j = (i + 1) % len(uvs)
        area += uvs[i].x * uvs[j].y - uvs[j].x * uvs[i].y
    return 0.5 * area


def polygon_centroid(points: Sequence[Vector]) -> Vector:
    if not points:
        return Vector((0.0, 0.0))
    area = poly_area(points)
    if abs(area) < EPS:
        sx = sum(p.x for p in points)
        sy = sum(p.y for p in points)
        return Vector((sx / len(points), sy / len(points)))
    factor = 1.0 / (6.0 * area)
    cx = 0.0
    cy = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        cross = points[i].x * points[j].y - points[j].x * points[i].y
        cx += (points[i].x + points[j].x) * cross
        cy += (points[i].y + points[j].y) * cross
    return Vector((cx * factor, cy * factor))


def normalize_step(threshold: float) -> float:
    t = max(0.0, min(1.0, threshold / 100.0))
    return 10.0 ** (-6.0 + 4.0 * t)


def quantize(value: float, step: float) -> int:
    if step <= 0.0:
        return int(round(value * 1e6))
    return int(round(value / step))


def face_uv_coords(face: bpy.types.BMFace, uv_layer: bpy.types.BMLayerItem) -> list[Vector]:
    return [loop[uv_layer].uv.copy() for loop in face.loops]


def is_uv_continuous(loop_a: bpy.types.BMLoop, loop_b: bpy.types.BMLoop, uv_layer: bpy.types.BMLayerItem, eps: float) -> bool:
    a0 = loop_a[uv_layer].uv
    a1 = loop_a.link_loop_next[uv_layer].uv
    b0 = loop_b[uv_layer].uv
    b1 = loop_b.link_loop_next[uv_layer].uv

    direct = uv_distance(a0, b0) <= eps and uv_distance(a1, b1) <= eps
    reverse = uv_distance(a0, b1) <= eps and uv_distance(a1, b0) <= eps
    return direct or reverse


def face_descriptor(face: bpy.types.BMFace, uv_layer: bpy.types.BMLayerItem, step: float, boundary_edges: int) -> tuple:
    coords = face_uv_coords(face, uv_layer)
    n = len(coords)
    if n == 0:
        return (0,)

    edges = []
    angles = []
    perimeter = 0.0

    for i in range(n):
        p0 = coords[i]
        p1 = coords[(i + 1) % n]
        p2 = coords[(i - 1) % n]
        v1 = p1 - p0
        v0 = p2 - p0
        l1 = v1.length
        l0 = v0.length
        perimeter += l1
        edges.append(l1)

        if l0 > EPS and l1 > EPS:
            a = max(-1.0, min(1.0, (v0.normalized().dot(v1.normalized()))))
            angles.append(math.acos(a))
        else:
            angles.append(0.0)

    area = abs(poly_area(coords))
    if perimeter <= EPS:
        perimeter = 1.0

    edge_sig = tuple(sorted(quantize(e / perimeter, step) for e in edges))
    angle_sig = tuple(sorted(quantize(a / math.pi, step) for a in angles))
    area_sig = quantize(area / (perimeter * perimeter), step)
    return (n, boundary_edges, area_sig, edge_sig, angle_sig)


def pca_basis(points: Sequence[Vector]) -> tuple[Vector, Vector, Vector, float]:
    if not points:
        return Vector((0.0, 0.0)), Vector((1.0, 0.0)), Vector((0.0, 1.0)), 1.0

    centroid = polygon_centroid(points)
    dxs = [p.x - centroid.x for p in points]
    dys = [p.y - centroid.y for p in points]
    n = float(len(points))
    cov_xx = sum(x * x for x in dxs) / n
    cov_xy = sum(x * y for x, y in zip(dxs, dys)) / n
    cov_yy = sum(y * y for y in dys) / n

    trace = cov_xx + cov_yy
    det_term = max(0.0, (cov_xx - cov_yy) * (cov_xx - cov_yy) + 4.0 * cov_xy * cov_xy)
    root = math.sqrt(det_term)
    eig1 = 0.5 * (trace + root)

    if abs(cov_xy) > EPS or abs(eig1 - cov_yy) > EPS:
        vx = eig1 - cov_yy
        vy = cov_xy
    else:
        vx = 1.0
        vy = 0.0

    basis_x = Vector((vx, vy))
    if basis_x.length <= EPS:
        basis_x = Vector((1.0, 0.0))
    else:
        basis_x.normalize()

    basis_y = Vector((-basis_x.y, basis_x.x))
    scale = math.sqrt(max(EPS, cov_xx + cov_yy))
    return centroid, basis_x, basis_y, scale


def project_points(points: Sequence[Vector], centroid: Vector, basis_x: Vector, basis_y: Vector, scale: float) -> list[Vector]:
    if scale <= EPS:
        scale = 1.0
    result = []
    for p in points:
        rel = p - centroid
        x = rel.dot(basis_x) / scale
        y = rel.dot(basis_y) / scale
        result.append(Vector((x, y)))
    return result


def canonical_point_signature(points: Sequence[Vector], step: float) -> tuple:
    return tuple(sorted((quantize(p.x, step), quantize(p.y, step)) for p in points))


def component_faces_from_bmesh(bm: bpy.types.BMesh, uv_layer: bpy.types.BMLayerItem, selected_only: bool = False, eps: float = 1e-6) -> list[list[bpy.types.BMFace]]:
    faces = [f for f in bm.faces if (not selected_only or f.select)]
    face_set = set(faces)
    adjacency: Dict[bpy.types.BMFace, set[bpy.types.BMFace]] = {f: set() for f in faces}

    for face in faces:
        for loop in face.loops:
            edge = loop.edge
            linked = edge.link_faces
            if len(linked) != 2:
                continue
            other = linked[0] if linked[1] is face else linked[1]
            if other not in face_set:
                continue
            other_loop = next((l for l in other.loops if l.edge is edge), None)
            if other_loop is None:
                continue
            if is_uv_continuous(loop, other_loop, uv_layer, eps):
                adjacency[face].add(other)
                adjacency[other].add(face)

    components: list[list[bpy.types.BMFace]] = []
    visited: set[bpy.types.BMFace] = set()

    for start in faces:
        if start in visited:
            continue
        queue = deque([start])
        visited.add(start)
        comp = []
        while queue:
            face = queue.popleft()
            comp.append(face)
            for other in adjacency[face]:
                if other not in visited:
                    visited.add(other)
                    queue.append(other)
        components.append(comp)

    return components


def build_island_record(island_index: int, faces: list[bpy.types.BMFace], uv_layer: bpy.types.BMLayerItem, similarity_threshold: float, eps: float = 1e-6) -> IslandRecord:
    step = normalize_step(similarity_threshold)
    face_set = set(faces)
    all_uvs: list[Vector] = []
    face_records: list[FaceRecord] = []
    descriptors: list[str] = []

    adjacency: Dict[bpy.types.BMFace, set[bpy.types.BMFace]] = {f: set() for f in faces}

    for face in faces:
        coords = face_uv_coords(face, uv_layer)
        all_uvs.extend(coords)
        boundary_edges = 0
        for loop in face.loops:
            edge = loop.edge
            connected = False
            for linked_face in edge.link_faces:
                if linked_face is face or linked_face not in face_set:
                    continue
                linked_loop = next((l for l in linked_face.loops if l.edge is edge), None)
                if linked_loop is not None and is_uv_continuous(loop, linked_loop, uv_layer, eps):
                    connected = True
                    adjacency[face].add(linked_face)
                    adjacency[linked_face].add(face)
                    break
            if not connected:
                boundary_edges += 1

        desc = face_descriptor(face, uv_layer, step, boundary_edges)
        face_records.append(FaceRecord(face.index, coords, desc, boundary_edges))
        descriptors.append(repr(desc))

    colors = [stable_digest(face_records[i].descriptor) for i in range(len(face_records))]
    face_to_index = {face: idx for idx, face in enumerate(faces)}
    for _ in range(3):
        new_colors: list[str] = []
        for i, face in enumerate(faces):
            neigh = sorted(colors[face_to_index[n]] for n in adjacency[face])
            new_colors.append(stable_digest((colors[i], tuple(neigh))))
        colors = new_colors

    centroid, basis_x, basis_y, scale = pca_basis(all_uvs)
    projection = project_points(all_uvs, centroid, basis_x, basis_y, scale)
    point_sig = canonical_point_signature(projection, step)
    degree_sig = tuple(sorted(len(adjacency[f]) for f in faces))
    final_sig = stable_digest((tuple(sorted(colors)), degree_sig, point_sig, tuple(sorted(descriptors))))

    return IslandRecord(
        island_index=island_index,
        face_indices=[face.index for face in faces],
        faces=faces,
        face_records=face_records,
        all_uvs=all_uvs,
        centroid=centroid,
        scale=scale,
        basis_x=basis_x,
        basis_y=basis_y,
        signature=final_sig,
    )


def island_score(a: IslandRecord, b: IslandRecord, threshold: float) -> float:
    step = normalize_step(threshold)
    if a.signature == b.signature:
        return 0.0

    ap = canonical_point_signature(project_points(a.all_uvs, a.centroid, a.basis_x, a.basis_y, a.scale), step)
    bp = canonical_point_signature(project_points(b.all_uvs, b.centroid, b.basis_x, b.basis_y, b.scale), step)
    if len(ap) != len(bp):
        return float("inf")

    mismatch = 0
    for pa, pb in zip(ap, bp):
        if pa != pb:
            mismatch += 1
    return mismatch / max(1, len(ap))


def best_transform_to_reference(
    reference: IslandRecord,
    candidate: IslandRecord,
    allow_mirrored: bool,
    apply_rotation: bool,
    apply_scale: bool,
) -> tuple[Vector, Vector, float] | None:
    ref_centroid = reference.centroid
    cand_centroid = candidate.centroid

    ref_basis_x, ref_basis_y = reference.basis_x, reference.basis_y
    cand_basis_x, cand_basis_y = candidate.basis_x, candidate.basis_y

    ref_scale = reference.scale if reference.scale > EPS else 1.0
    cand_scale = candidate.scale if candidate.scale > EPS else 1.0
    scale_ratio = ref_scale / cand_scale if apply_scale else 1.0

    orientation_options = [
        (1.0, 1.0),
        (-1.0, 1.0),
        (1.0, -1.0),
        (-1.0, -1.0),
    ]
    if not allow_mirrored:
        orientation_options = [(1.0, 1.0), (-1.0, -1.0)]

    ref_points = sorted(reference.all_uvs, key=lambda p: (round(p.x, 8), round(p.y, 8)))
    if len(ref_points) != len(candidate.all_uvs):
        # Fall back to the best effort transform even when the multiset sizes do not line up.
        pass

    best_error = float("inf")
    best_basis = (cand_basis_x, cand_basis_y)

    for sx, sy in orientation_options:
        if apply_rotation:
            bx = cand_basis_x * sx
            by = cand_basis_y * sy
        else:
            bx = Vector((1.0, 0.0))
            by = Vector((0.0, 1.0))

        transformed = []
        for p in candidate.all_uvs:
            rel = p - cand_centroid
            x = rel.dot(bx)
            y = rel.dot(by)
            transformed.append(ref_centroid + ref_basis_x * (x * scale_ratio) + ref_basis_y * (y * scale_ratio))

        transformed.sort(key=lambda p: (round(p.x, 8), round(p.y, 8)))
        ref_sorted = list(ref_points)
        ref_sorted.sort(key=lambda p: (round(p.x, 8), round(p.y, 8)))

        if len(transformed) != len(ref_sorted):
            continue

        total = 0.0
        for a, b in zip(transformed, ref_sorted):
            dx = a.x - b.x
            dy = a.y - b.y
            total += dx * dx + dy * dy
        error = math.sqrt(total / max(1, len(transformed)))

        if error < best_error:
            best_error = error
            best_basis = (bx, by)

    if best_error == float("inf"):
        return None
    return best_basis[0], best_basis[1], scale_ratio
