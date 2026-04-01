"""
Computacao Grafica - Projeto 1
Estudo isolado do gol (trave + rede), baseado em references/goal_sketch.jpeg.

Controles:
- A / D: mover no eixo X
- W / S: mover no eixo Y
- Q / E: aumentar/diminuir profundidade da trave
- Z / X: aumentar/diminuir escala
- P: wireframe on/off
- R: reset de estado
"""

import ctypes
import math

import glfw
import numpy as np
from OpenGL.GL import *

PI = 3.141592

# ============================================================================
# GLFW
# ============================================================================

if not glfw.init():
    raise RuntimeError("Falha ao inicializar GLFW")

glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
window = glfw.create_window(980, 840, "Estudo - Goal Sketch", None, None)
if window is None:
    glfw.terminate()
    raise RuntimeError("Falha ao criar janela GLFW")

glfw.make_context_current(window)

# ============================================================================
# Shaders
# ============================================================================

vertex_code = """
attribute vec3 position;
uniform mat4 mat_transformation;
void main(){
    gl_Position = mat_transformation * vec4(position, 1.0);
}
"""

fragment_code = """
uniform vec4 color;
void main(){
    gl_FragColor = color;
}
"""

program = glCreateProgram()
vertex = glCreateShader(GL_VERTEX_SHADER)
fragment = glCreateShader(GL_FRAGMENT_SHADER)

glShaderSource(vertex, vertex_code)
glShaderSource(fragment, fragment_code)

glCompileShader(vertex)
if not glGetShaderiv(vertex, GL_COMPILE_STATUS):
    raise RuntimeError(glGetShaderInfoLog(vertex).decode())

glCompileShader(fragment)
if not glGetShaderiv(fragment, GL_COMPILE_STATUS):
    raise RuntimeError(glGetShaderInfoLog(fragment).decode())

glAttachShader(program, vertex)
glAttachShader(program, fragment)
glLinkProgram(program)

if not glGetProgramiv(program, GL_LINK_STATUS):
    raise RuntimeError(glGetProgramInfoLog(program))

glUseProgram(program)

# ============================================================================
# Geometry helpers
# ============================================================================


def gerar_cilindro(raio, altura, num_sectors, num_stacks):
    sector_step = (PI * 2.0) / num_sectors
    stack_step = altura / num_stacks
    z0 = -altura / 2.0

    def c(theta, z, r):
        return (r * math.cos(theta), r * math.sin(theta), z)

    verts = []

    for j in range(num_stacks):
        for i in range(num_sectors):
            u = i * sector_step
            z = z0 + j * stack_step
            un = PI * 2.0 if (i + 1) == num_sectors else (i + 1) * sector_step
            zn = z0 + altura if (j + 1) == num_stacks else z0 + (j + 1) * stack_step

            p0 = c(u, z, raio)
            p1 = c(u, zn, raio)
            p2 = c(un, z, raio)
            p3 = c(un, zn, raio)
            verts += [p0, p2, p1, p3, p1, p2]

            if j == 0:
                verts += [p0, p2, (0.0, 0.0, z)]
            if (j + 1) == num_stacks:
                verts += [p1, p3, (0.0, 0.0, zn)]

    return verts


# ============================================================================
# Object registry
# ============================================================================

objetos = {}
todos_vertices = []


def reg(nome, verts, prim="T"):
    inicio = len(todos_vertices)
    todos_vertices.extend(verts)
    objetos[nome] = (inicio, len(verts), prim)


reg("unit_cyl", gerar_cilindro(1.0, 1.0, 20, 5), "T")

# ============================================================================
# Upload to GPU
# ============================================================================

vertices = np.zeros(len(todos_vertices), [("position", np.float32, 3)])
vertices["position"] = np.array(todos_vertices, dtype=np.float32)

buffer = glGenBuffers(1)
glBindBuffer(GL_ARRAY_BUFFER, buffer)
glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)

stride = vertices.strides[0]
offset = ctypes.c_void_p(0)

loc_pos = glGetAttribLocation(program, "position")
glEnableVertexAttribArray(loc_pos)
glVertexAttribPointer(loc_pos, 3, GL_FLOAT, False, stride, offset)

loc_color = glGetUniformLocation(program, "color")
loc_mat = glGetUniformLocation(program, "mat_transformation")

# ============================================================================
# Matrix helpers
# ============================================================================


def mm(a, b):
    return np.dot(a.reshape(4, 4), b.reshape(4, 4)).reshape(1, 16).astype(np.float32)


def mt(tx, ty, tz=0.0):
    return np.array([
        1, 0, 0, tx,
        0, 1, 0, ty,
        0, 0, 1, tz,
        0, 0, 0, 1,
    ], np.float32)


def ms(sx, sy, sz=1.0):
    return np.array([
        sx, 0, 0, 0,
        0, sy, 0, 0,
        0, 0, sz, 0,
        0, 0, 0, 1,
    ], np.float32)


def rx(a):
    c = math.cos(a)
    s = math.sin(a)
    return np.array([
        1, 0, 0, 0,
        0, c, -s, 0,
        0, s, c, 0,
        0, 0, 0, 1,
    ], np.float32)


def rz(a):
    c = math.cos(a)
    s = math.sin(a)
    return np.array([
        c, -s, 0, 0,
        s, c, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ], np.float32)


# ============================================================================
# Drawing helpers
# ============================================================================


def draw(nome, cor, mat):
    inicio, count, prim = objetos[nome]
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, mat)
    glUniform4f(loc_color, *cor)

    if prim == "T":
        glDrawArrays(GL_TRIANGLES, inicio, count)


def draw_segment(start, end, radius, color, z=0.0):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1e-6:
        return

    angle = math.atan2(dx, -dy)
    mid_x = (start[0] + end[0]) * 0.5
    mid_y = (start[1] + end[1]) * 0.5

    m = mt(mid_x, mid_y, z)
    m = mm(m, rz(angle))
    m = mm(m, rx(PI / 2.0))
    m = mm(m, ms(radius, radius, length))
    draw("unit_cyl", color, m)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(pa, pb, t):
    return (lerp(pa[0], pb[0], t), lerp(pa[1], pb[1], t))


def transform_pt(pt, tx, ty, scale):
    x = pt[0] * scale
    y = pt[1] * scale
    return (x + tx, y + ty)


def draw_goal(tx, ty, scale, depth_mag):
    frame_front = (1.00, 1.00, 1.00, 1.0)
    frame_mid = (0.85, 0.85, 0.88, 0.55)
    frame_back = (0.76, 0.76, 0.80, 0.42)
    net_color = (0.66, 0.66, 0.72, 0.45)

    r_front = 0.031 * scale
    r_mid = 0.021 * scale
    r_back = 0.018 * scale
    r_net = 0.0068 * scale

    Z_NEAR = -0.32
    Z_CONNECT = +0.02
    Z_FAR = +0.22
    Z_BRACE = +0.28
    Z_NET = +0.34

    # Canonical face rectangle (kept for proportions).
    face_tl = (-0.44, 0.28)
    face_tr = (0.44, 0.28)
    face_bl = (-0.44, -0.27)
    face_br = (0.44, -0.27)

    depth = (depth_mag, -0.62 * depth_mag)

    # Inverted hierarchy: what was behind comes forward, and vice-versa.
    near_tl = (face_tl[0] + depth[0], face_tl[1] + depth[1])
    near_tr = (face_tr[0] + depth[0], face_tr[1] + depth[1])
    near_bl = (face_bl[0] + depth[0], face_bl[1] + depth[1])
    near_br = (face_br[0] + depth[0], face_br[1] + depth[1])

    far_tl = face_tl
    far_tr = face_tr
    far_bl = face_bl
    far_br = face_br

    n_tl = transform_pt(near_tl, tx, ty, scale)
    n_tr = transform_pt(near_tr, tx, ty, scale)
    n_bl = transform_pt(near_bl, tx, ty, scale)
    n_br = transform_pt(near_br, tx, ty, scale)

    f_tl = transform_pt(far_tl, tx, ty, scale)
    f_tr = transform_pt(far_tr, tx, ty, scale)
    f_bl = transform_pt(far_bl, tx, ty, scale)
    f_br = transform_pt(far_br, tx, ty, scale)

    # Back elements first: far frame without vertical side poles, then net/braces/connectors.
    draw_segment(f_bl, f_br, r_back, frame_back, z=Z_FAR)

    top_attach_l = lerp2(near_tl, far_tl, 0.55)
    top_attach_r = lerp2(near_tr, far_tr, 0.55)
    net_tl = top_attach_l
    net_tr = top_attach_r
    net_bl = far_bl
    net_br = far_br

    p_net_top_l = transform_pt(net_tl, tx, ty, scale)
    p_net_top_r = transform_pt(net_tr, tx, ty, scale)
    draw_segment(p_net_top_l, p_net_top_r, r_net * 0.95, net_color, z=Z_NET)

    # Roof net strands: connect back top-net edge to the front top pole
    # using the same slant direction as the side connectors.
    for i in range(7):
        t = i / 6.0
        p_back_top = transform_pt(lerp2(net_tl, net_tr, t), tx, ty, scale)
        p_front_top = transform_pt(lerp2(near_tl, near_tr, t), tx, ty, scale)
        draw_segment(p_back_top, p_front_top, r_net * 0.75, net_color, z=Z_NET)

    for i in range(8):
        t = i / 7.0
        p0 = transform_pt(lerp2(net_tl, net_tr, t), tx, ty, scale)
        p1 = transform_pt(lerp2(net_bl, net_br, t), tx, ty, scale)
        draw_segment(p0, p1, r_net, net_color, z=Z_NET)

    for j in range(1, 4):
        u = j / 4.0
        p0 = transform_pt(lerp2(net_tl, net_bl, u), tx, ty, scale)
        p1 = transform_pt(lerp2(net_tr, net_br, u), tx, ty, scale)
        draw_segment(p0, p1, r_net * 0.88, net_color, z=Z_NET)

    left_mid_top = transform_pt(top_attach_l, tx, ty, scale)
    right_mid_top = transform_pt(top_attach_r, tx, ty, scale)
    draw_segment(left_mid_top, f_bl, r_back, frame_mid, z=Z_BRACE)
    draw_segment(right_mid_top, f_br, r_back, frame_mid, z=Z_BRACE)

    draw_segment(n_tl, left_mid_top, r_mid, frame_mid, z=Z_CONNECT)
    draw_segment(n_tr, right_mid_top, r_mid, frame_mid, z=Z_CONNECT)
    draw_segment(n_bl, f_bl, r_mid, frame_mid, z=Z_CONNECT)
    draw_segment(n_br, f_br, r_mid, frame_mid, z=Z_CONNECT)

    # Side-panel net (left and right), filling the empty regions between poles.
    for i in range(1, 4):
        t = i / 4.0
        # Left side: slanted strands
        l_top = transform_pt(lerp2(near_tl, top_attach_l, t), tx, ty, scale)
        l_bot = transform_pt(lerp2(near_bl, far_bl, t), tx, ty, scale)
        draw_segment(l_top, l_bot, r_net * 0.75, net_color, z=Z_NET)

        # Right side: slanted strands
        r_top = transform_pt(lerp2(near_tr, top_attach_r, t), tx, ty, scale)
        r_bot = transform_pt(lerp2(near_br, far_br, t), tx, ty, scale)
        draw_segment(r_top, r_bot, r_net * 0.75, net_color, z=Z_NET)

    for j in range(1, 3):
        u = j / 3.0
        # Left side: cross strands
        l_front_pt = transform_pt(lerp2(near_tl, near_bl, u), tx, ty, scale)
        l_back_pt = transform_pt(lerp2(top_attach_l, far_bl, u), tx, ty, scale)
        draw_segment(l_front_pt, l_back_pt, r_net * 0.68, net_color, z=Z_NET)

        # Right side: cross strands
        r_front_pt = transform_pt(lerp2(near_tr, near_br, u), tx, ty, scale)
        r_back_pt = transform_pt(lerp2(top_attach_r, far_br, u), tx, ty, scale)
        draw_segment(r_front_pt, r_back_pt, r_net * 0.68, net_color, z=Z_NET)

    # Front frame (open face): top bar + two posts only.
    # Post top must align with the topmost edge of the top horizontal pole.
    n_tl_post = (n_tl[0], n_tl[1] + r_front)
    n_tr_post = (n_tr[0], n_tr[1] + r_front)
    post_bottom_extra = 0.02 * scale
    n_bl_post = (n_bl[0], n_bl[1] - post_bottom_extra)
    n_br_post = (n_br[0], n_br[1] - post_bottom_extra)
    draw_segment(n_tl, n_tr, r_front, frame_front, z=Z_NEAR)
    draw_segment(n_tl_post, n_bl_post, r_front, frame_front, z=Z_NEAR)
    draw_segment(n_tr_post, n_br_post, r_front, frame_front, z=Z_NEAR)


# ============================================================================
# Scene state and controls
# ============================================================================


def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))


goal_x = -0.03
goal_y = 0.02
goal_scale = 0.92
goal_depth = 0.22
wireframe = False


def reset_state():
    global goal_x, goal_y, goal_scale, goal_depth, wireframe
    goal_x = -0.03
    goal_y = 0.02
    goal_scale = 0.92
    goal_depth = 0.22
    wireframe = False


def key_event(_window, key, _scancode, action, _mods):
    global goal_x, goal_y, goal_scale, goal_depth, wireframe

    if key == glfw.KEY_P and action == glfw.PRESS:
        wireframe = not wireframe
        return

    if key == glfw.KEY_R and action == glfw.PRESS:
        reset_state()
        return

    if action not in (glfw.PRESS, glfw.REPEAT):
        return

    if key == glfw.KEY_A:
        goal_x = clamp(goal_x - 0.03, -0.80, 0.80)
    elif key == glfw.KEY_D:
        goal_x = clamp(goal_x + 0.03, -0.80, 0.80)
    elif key == glfw.KEY_W:
        goal_y = clamp(goal_y + 0.03, -0.60, 0.60)
    elif key == glfw.KEY_S:
        goal_y = clamp(goal_y - 0.03, -0.60, 0.60)
    elif key == glfw.KEY_Q:
        goal_depth = clamp(goal_depth + 0.02, 0.10, 0.40)
    elif key == glfw.KEY_E:
        goal_depth = clamp(goal_depth - 0.02, 0.10, 0.40)
    elif key == glfw.KEY_Z:
        goal_scale = clamp(goal_scale + 0.04, 0.50, 1.40)
    elif key == glfw.KEY_X:
        goal_scale = clamp(goal_scale - 0.04, 0.50, 1.40)


glfw.set_key_callback(window, key_event)

# ============================================================================
# Main loop
# ============================================================================

glfw.show_window(window)
glEnable(GL_DEPTH_TEST)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

while not glfw.window_should_close(window):
    glfw.poll_events()

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glClearColor(0.94, 0.95, 0.97, 1.0)

    if wireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    else:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    draw_goal(goal_x, goal_y, goal_scale, goal_depth)

    glfw.swap_buffers(window)

glfw.terminate()
