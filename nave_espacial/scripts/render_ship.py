# Renderiza una captura en vista de tres cuartos. No guarda el .blend:
# la cámara y las luces solo existen en esta sesión de render.
#
# Ejecutar:
#   blender -b --factory-startup --python render_ship.py -- <nave.blend> <salida.png>

import bpy
import math
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
blend_path, png_path = argv[0], argv[1]

bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

# Cámara en vista de tres cuartos (frente-derecha-arriba, la proa mira a la cámara)
cam_data = bpy.data.cameras.new("camara_render")
cam_data.lens = 50
cam = bpy.data.objects.new("camara_render", cam_data)
scene.collection.objects.link(cam)
cam_loc = Vector((6.0, 5.2, 4.0))
cam.location = cam_loc
cam.rotation_euler = (Vector((0, 0.5, 0)) - cam_loc).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

# Luz principal + relleno
sun_data = bpy.data.lights.new("sol", "SUN")
sun_data.energy = 3.0
sun = bpy.data.objects.new("sol", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(35))

fill_data = bpy.data.lights.new("relleno", "AREA")
fill_data.energy = 250
fill_data.size = 6
fill = bpy.data.objects.new("relleno", fill_data)
scene.collection.objects.link(fill)
fill.location = (-5, -4, 3)
fill.rotation_euler = (math.radians(60), 0, math.radians(-130))

# Fondo oscuro sencillo
world = bpy.data.worlds.new("fondo")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.05, 0.09, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
scene.world = world

# Render
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 64
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = png_path
bpy.ops.render.render(write_still=True)
print("PNG", png_path)
