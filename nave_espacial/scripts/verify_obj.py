# Verifica el OBJ: caras triangulares, malla conectada y simetría en X.
#
# Ejecutar:  python verify_obj.py <nave_espacial.obj>

import sys

path = sys.argv[1]
verts = []
faces = []
mtl_refs = []

with open(path, encoding="utf-8") as fh:
    for line in fh:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            verts.append(tuple(float(x) for x in parts[1:4]))
        elif parts[0] == "f":
            faces.append([int(tok.split("/")[0]) - 1 for tok in parts[1:]])
        elif parts[0] in ("usemtl", "mtllib"):
            mtl_refs.append(line.strip())

non_tri = [f for f in faces if len(f) != 3]
print("vertices:", len(verts))
print("caras:", len(faces))
print("caras no triangulares:", len(non_tri))

# Componentes conectados (union-find sobre los vértices usados por las caras)
parent = list(range(len(verts)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for f in faces:
    for a in f[1:]:
        ra, rb = find(f[0]), find(a)
        if ra != rb:
            parent[ra] = rb

used = {i for f in faces for i in f}
roots = {find(i) for i in used}
print("componentes conectados:", len(roots))

# Simetría: cada vértice tiene su espejo en X = -X
keys = {tuple(round(c, 5) for c in v) for v in verts}
mirror_ok = all(
    (round(-x, 5), round(y, 5), round(z, 5)) in keys for x, y, z in keys
)
print("simetrico en X:", mirror_ok)
xs = [v[0] for v in verts]
ys = [v[1] for v in verts]
zs = [v[2] for v in verts]
print("bbox X:", round(min(xs), 3), round(max(xs), 3))
print("bbox Y:", round(min(ys), 3), round(max(ys), 3))
print("bbox Z:", round(min(zs), 3), round(max(zs), 3))
print("referencias de material:", mtl_refs)
