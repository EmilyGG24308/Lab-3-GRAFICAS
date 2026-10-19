# Construye la nave a partir de UN solo cubo, usando solo operaciones de modelado
# permitidas (Move, Scale, Rotate, Extrude, Inset, Bevel, Knife, Subdivide).
#
# Ejecutar:
#   blender -b --factory-startup --python build_ship.py -- <carpeta_salida>

import bpy
import bmesh
import math
import os
import sys
from mathutils import Matrix, Vector

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
os.makedirs(OUT, exist_ok=True)

# --- Escena limpia: solo quedará la nave -------------------------------------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

# --- Punto de partida: un único cubo (lado 2, de -1 a 1) ---------------------
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
ship = bpy.context.active_object
ship.name = "nave_espacial"
ship.data.name = "nave_espacial"

bm = bmesh.new()
bm.from_mesh(ship.data)


# --- Helpers sobre el mismo BMesh -------------------------------------------
def faces_where(pred):
    bm.normal_update()
    return [f for f in bm.faces if pred(f)]


def center(f):
    return f.calc_center_median()


def extrude(faces, offset=(0, 0, 0), scale=(1, 1, 1)):
    """Extrude + Scale + Move sobre la región dada (alrededor de su centro)."""
    if not faces:
        raise RuntimeError("extrude: no se encontraron caras")
    res = bmesh.ops.extrude_face_region(bm, geom=faces)
    new_verts = [v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)]
    new_faces = [f for f in res["geom"] if isinstance(f, bmesh.types.BMFace)]
    c = sum((v.co for v in new_verts), Vector()) / len(new_verts)
    bmesh.ops.translate(bm, verts=new_verts, vec=-c)
    bmesh.ops.scale(bm, verts=new_verts, vec=scale)
    bmesh.ops.translate(bm, verts=new_verts, vec=c + Vector(offset))
    return new_faces


def inset(faces, thickness):
    res = bmesh.ops.inset_region(bm, faces=faces, thickness=thickness, depth=0.0)
    return res["faces"]


def bevel(edges, width):
    bmesh.ops.bevel(
        bm, geom=edges, offset=width, offset_type="OFFSET",
        segments=1, profile=0.5, affect="EDGES",
    )


def rotate(verts, angle_deg, pivot):
    bmesh.ops.rotate(
        bm, verts=verts, cent=pivot,
        matrix=Matrix.Rotation(math.radians(angle_deg), 3, "Z"),
    )


def knife(plane_co, plane_no):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(
        bm, geom=geom, dist=0.0001,
        plane_co=plane_co, plane_no=plane_no,
        clear_inner=False, clear_outer=False,
    )


# --- 1) Fuselaje: el cubo estirado a un prisma alargado ----------------------
bmesh.ops.scale(bm, verts=bm.verts[:], vec=(0.3, 2.0, 0.3))

# --- 2) Morro: dos extrusiones de la cara frontal que la afilan -------------
front = faces_where(lambda f: f.normal.y > 0.5 and center(f).y > 1.9)
nose1 = extrude(front, offset=(0, 0.7, 0), scale=(0.6, 1, 0.6))
nose_cap = faces_where(lambda f: f.normal.y > 0.5 and center(f).y > 2.5)
extrude(nose_cap, offset=(0, 0.6, 0), scale=(0.5, 1, 0.5))

# --- 3) Cabina: inset de la cara superior y extrusión hacia arriba ----------
def is_top_center(f):
    c = center(f)
    return f.normal.z > 0.5 and abs(c.z - 0.3) < 1e-4 and abs(c.y) < 0.5 and abs(c.x) < 0.1


top = faces_where(is_top_center)
assert len(top) == 1, f"cara superior: {len(top)}"
inset(top, thickness=0.12)
canopy_base = faces_where(is_top_center)
assert len(canopy_base) == 1, f"cara interior de cabina: {len(canopy_base)}"
extrude(canopy_base, offset=(0, 0.25, 0.22), scale=(0.8, 0.5, 1))
# Bevel en el borde superior de la cabina
bevel([e for e in bm.edges if all(v.co.z > 0.5 for v in e.verts)], 0.04)

# --- 4) Alas: extrusión de cada cara lateral + punta con barrido -----------
for s in (1, -1):
    side = faces_where(
        lambda f: abs(f.normal.x - s) < 0.01 and abs(center(f).x - 0.3 * s) < 1e-3
    )
    assert len(side) == 1, f"cara lateral {s}: {len(side)}"
    extrude(side, offset=(1.0 * s, 0, 0), scale=(1, 0.4, 0.4))

    tip = faces_where(
        lambda f: abs(f.normal.x - s) < 0.01 and abs(center(f).x - 1.3 * s) < 1e-3
    )
    assert len(tip) == 1, f"punta del ala {s}: {len(tip)}"
    tip_new = extrude(tip, offset=(0.4 * s, 0, 0), scale=(1, 0.7, 0.8))
    tip_verts = [v for v in bm.verts if v.co.x * s > 1.6]
    rotate(tip_verts, -s * 12, Vector((1.3 * s, 0, 0)))

# --- 5) Motores integrados bajo cada ala + toberas traseras -----------------
for s in (1, -1):
    pods = faces_where(
        lambda f: f.normal.z < -0.5
        and 0.4 < center(f).x * s < 1.2
        and center(f).z < 0
    )
    assert len(pods) == 1, f"base de motor {s}: {len(pods)}"
    extrude(pods, offset=(0, -0.6, -0.45), scale=(0.5, 0.6, 1))
    nozzle = faces_where(
        lambda f: f.normal.y < -0.5
        and 0.4 < center(f).x * s < 1.2
        and center(f).z < -0.2
    )
    assert len(nozzle) == 1, f"tobera de motor {s}: {len(nozzle)}"
    extrude(nozzle, offset=(0, -0.35, 0), scale=(0.6, 1, 0.6))

rear = faces_where(
    lambda f: f.normal.y < -0.5 and abs(center(f).x) < 0.1 and center(f).y < -1.9
)
assert len(rear) == 1, f"cara trasera: {len(rear)}"
extrude(rear, offset=(0, -0.3, 0), scale=(0.6, 1, 0.6))

# --- 6) Aleta vertical en la parte trasera superior ------------------------
fin_base = faces_where(
    lambda f: f.normal.z > 0.5
    and abs(center(f).z - 0.3) < 1e-3
    and abs(center(f).x) < 0.1
    and center(f).y < -1.5
)
assert len(fin_base) == 1, f"base de aleta: {len(fin_base)}"
extrude(fin_base, offset=(0, 0, 0.7), scale=(0.4, 1.5, 1))

# --- 7) Corte de cuchillo (Knife) transversal y bevel de la punta -----------
knife(Vector((0, 1.4, 0)), Vector((0, 1, 0)))
bevel([e for e in bm.edges if all(v.co.y > 2.5 for v in e.verts)], 0.03)

# --- 8) Materiales simples por zona (asignados por índice de cara) ---------
def mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = rgba
    return m


ship.data.materials.clear()
mat_body = mat("casco_gris", (0.80, 0.82, 0.86, 1.0))
mat_wing = mat("alas_azul", (0.12, 0.32, 0.78, 1.0))
mat_engine = mat("motores_naranja", (0.95, 0.42, 0.08, 1.0))
mat_glass = mat("cabina_cian", (0.25, 0.90, 1.00, 1.0))
for m in (mat_body, mat_wing, mat_engine, mat_glass):
    ship.data.materials.append(m)
IDX = {"body": 0, "wing": 1, "engine": 2, "glass": 3}

bm.faces.ensure_lookup_table()
for f in bm.faces:
    c = center(f)
    if f.normal.z > 0.5 and c.z > 0.35 and abs(c.x) < 0.2 and c.y > -1.5:
        f.material_index = IDX["glass"]
    elif c.z > 0.3 and abs(c.x) < 0.2 and c.y < -1.5:
        f.material_index = IDX["wing"]  # aleta
    elif c.z < -0.2 and 0.4 < abs(c.x) < 1.25:
        f.material_index = IDX["engine"]
    elif abs(c.x) > 0.35:
        f.material_index = IDX["wing"]
    else:
        f.material_index = IDX["body"]

bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(ship.data)
bm.free()

# --- 9) Triangulate (modificador) aplicado ---------------------------------
bpy.ops.object.select_all(action="DESELECT")
ship.select_set(True)
bpy.context.view_layer.objects.active = ship
tri = ship.modifiers.new("Triangulate", "TRIANGULATE")
bpy.ops.object.modifier_apply(modifier=tri.name)

# --- 10) Exportar OBJ (+ MTL) con caras trianguladas -----------------------
obj_path = os.path.join(OUT, "nave_espacial.obj")
bpy.ops.wm.obj_export(
    filepath=obj_path,
    export_selected_objects=True,
    export_materials=True,
    export_triangulated_mesh=True,
    export_normals=False,
    export_uv=False,
    forward_axis="NEGATIVE_Z",
    up_axis="Y",
)

# --- 11) Guardar el .blend editable (solo la nave) -------------------------
blend_path = os.path.join(OUT, "nave_espacial.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

me = ship.data
print("VERTICES", len(me.vertices), "POLIGONOS", len(me.polygons))
print("OBJETOS EN ESCENA", len(bpy.data.objects))
print("OBJ", obj_path)
print("BLEND", blend_path)
