"""
Computacao Grafica - Projeto 1
Cena integrada baseada no sketch: personagem do Gremio pisando na bola do Inter.

Controles:
- A / D: translacao horizontal do personagem
- W / S: intensidade da pisada (stomp)
- Q / E: movimento de corte do braco com espada
- Z / X: escala do chapeu no chao
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
window = glfw.create_window(980, 840, "Projeto 1 - Cena Final", None, None)
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
varying float obj_x;
void main(){
    obj_x = position.x;
    gl_Position = mat_transformation * vec4(position, 1.0);
}
"""

fragment_code = """
uniform vec4 color;
uniform int use_stripes;
uniform int stripe_count;
uniform float stripe_bound_0;
uniform float stripe_bound_1;
uniform vec4 stripe_color_0;
uniform vec4 stripe_color_1;
uniform vec4 stripe_color_2;
varying float obj_x;

void main(){
    if (use_stripes == 0) {
        gl_FragColor = color;
        return;
    }

    if (stripe_count == 2) {
        if (obj_x < stripe_bound_0) gl_FragColor = stripe_color_0;
        else gl_FragColor = stripe_color_1;
        return;
    }

    if (obj_x < stripe_bound_0) gl_FragColor = stripe_color_0;
    else if (obj_x < stripe_bound_1) gl_FragColor = stripe_color_1;
    else gl_FragColor = stripe_color_2;
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
# Geometry generators
# ============================================================================


def gerar_esfera(raio, num_sectors, num_stacks):
    sector_step = (PI * 2.0) / num_sectors
    stack_step = PI / num_stacks

    def f(u, v, r):
        return (
            r * math.sin(v) * math.cos(u),
            r * math.sin(v) * math.sin(u),
            r * math.cos(v),
        )

    verts = []
    for i in range(num_sectors):
        for j in range(num_stacks):
            u = i * sector_step
            v = j * stack_step
            un = PI * 2.0 if (i + 1) == num_sectors else (i + 1) * sector_step
            vn = PI if (j + 1) == num_stacks else (j + 1) * stack_step

            p0 = f(u, v, raio)
            p1 = f(u, vn, raio)
            p2 = f(un, v, raio)
            p3 = f(un, vn, raio)
            verts += [p0, p2, p1, p3, p1, p2]

    return verts


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


def gerar_circulo(raio, n):
    verts = [(0.0, 0.0, 0.0)]
    for i in range(n + 1):
        a = i * 2.0 * PI / n
        verts.append((math.cos(a) * raio, math.sin(a) * raio, 0.0))
    return verts


def gerar_retangulo(w, h):
    hw = w / 2.0
    hh = h / 2.0
    return [
        (+hw, -hh, 0.0),
        (+hw, +hh, 0.0),
        (-hw, -hh, 0.0),
        (-hw, +hh, 0.0),
    ]


def gerar_caixa(w, h, d):
    hw = w / 2.0
    hh = h / 2.0
    hd = d / 2.0
    return [
        (-hw, -hh, +hd), (+hw, -hh, +hd), (-hw, +hh, +hd), (+hw, +hh, +hd),
        (+hw, -hh, +hd), (+hw, -hh, -hd), (+hw, +hh, +hd), (+hw, +hh, -hd),
        (+hw, -hh, -hd), (-hw, -hh, -hd), (+hw, +hh, -hd), (-hw, +hh, -hd),
        (-hw, -hh, -hd), (-hw, -hh, +hd), (-hw, +hh, -hd), (-hw, +hh, +hd),
        (-hw, -hh, -hd), (+hw, -hh, -hd), (-hw, -hh, +hd), (+hw, -hh, +hd),
        (-hw, +hh, +hd), (+hw, +hh, +hd), (-hw, +hh, -hd), (+hw, +hh, -hd),
    ]


def gerar_estrela(r_outer, r_inner, pontas=5):
    pts = []
    for i in range(pontas * 2):
        ang = i * PI / pontas - PI / 2.0
        r = r_outer if (i % 2) == 0 else r_inner
        pts.append((math.cos(ang) * r, math.sin(ang) * r, 0.0))

    verts = []
    center = (0.0, 0.0, 0.0)
    for i in range(len(pts)):
        p0 = pts[i]
        p1 = pts[(i + 1) % len(pts)]
        verts += [center, p0, p1]
    return verts


def gerar_triangulo(base, altura):
    hb = base / 2.0
    return [(-hb, 0.0, 0.0), (hb, 0.0, 0.0), (0.0, altura, 0.0)]


def gerar_raios_sol(r_inner, r_outer, n):
    verts = []
    for i in range(n):
        a = i * 2.0 * PI / n
        ap = a - (PI / n) * 0.42
        an = a + (PI / n) * 0.42
        verts += [
            (math.cos(ap) * r_inner, math.sin(ap) * r_inner, 0.0),
            (math.cos(an) * r_inner, math.sin(an) * r_inner, 0.0),
            (math.cos(a) * r_outer, math.sin(a) * r_outer, 0.0),
        ]
    return verts


def gerar_crescente(r_outer, r_inner, off_x, off_y, n=64):
    def arc_points(cx, cy, r, a0, a1, samples):
        if a1 < a0:
            a1 += 2.0 * PI
        pts = []
        for i in range(samples):
            t = i / float(samples - 1)
            a = a0 + (a1 - a0) * t
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, 0.0))
        return pts

    def midpoint_angle(a0, a1):
        if a1 < a0:
            a1 += 2.0 * PI
        return 0.5 * (a0 + a1)

    d = math.sqrt(off_x * off_x + off_y * off_y)
    if d < 1e-6:
        return []

    if d >= (r_outer + r_inner) or d <= abs(r_outer - r_inner):
        # Fallback strip if circles are not in intersecting crescent configuration.
        start = 1.20 * PI
        end = 2.05 * PI
        outer = arc_points(0.0, 0.0, r_outer, start, end, n)
        inner = arc_points(off_x, off_y, r_inner, start, end, n)
        verts = []
        for i in range(n - 1):
            o0, o1 = outer[i], outer[i + 1]
            i0, i1 = inner[i], inner[i + 1]
            verts += [o0, o1, i0, o1, i1, i0]
        return verts

    a = (r_outer * r_outer - r_inner * r_inner + d * d) / (2.0 * d)
    h2 = max(r_outer * r_outer - a * a, 0.0)
    h = math.sqrt(h2)
    ux, uy = off_x / d, off_y / d
    mx, my = ux * a, uy * a

    ix1, iy1 = mx - uy * h, my + ux * h
    ix2, iy2 = mx + uy * h, my - ux * h

    ao1 = math.atan2(iy1, ix1)
    ao2 = math.atan2(iy2, ix2)
    ai1 = math.atan2(iy1 - off_y, ix1 - off_x)
    ai2 = math.atan2(iy2 - off_y, ix2 - off_x)

    m12 = midpoint_angle(ao1, ao2)
    pmx, pmy = math.cos(m12) * r_outer, math.sin(m12) * r_outer
    is_outside_inner = ((pmx - off_x) * (pmx - off_x) + (pmy - off_y) * (pmy - off_y)) >= (r_inner * r_inner)

    if is_outside_inner:
        o_start, o_end = ao1, ao2
        i_start, i_end = ai1, ai2
    else:
        o_start, o_end = ao2, ao1
        i_start, i_end = ai2, ai1

    outer_arc = arc_points(0.0, 0.0, r_outer, o_start, o_end, n)
    inner_arc_a = arc_points(off_x, off_y, r_inner, i_start, i_end, n)
    mid_in = inner_arc_a[n // 2]
    inside_outer_a = (mid_in[0] * mid_in[0] + mid_in[1] * mid_in[1]) <= (r_outer * r_outer)

    if inside_outer_a:
        inner_arc = inner_arc_a
    else:
        inner_arc = list(reversed(arc_points(off_x, off_y, r_inner, i_end, i_start, n)))

    verts = []
    for i in range(n - 1):
        o0, o1 = outer_arc[i], outer_arc[i + 1]
        i0, i1 = inner_arc[i], inner_arc[i + 1]
        verts += [o0, o1, i0, o1, i1, i0]
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


reg("sphere_body", gerar_esfera(0.26, 34, 34), "T")
reg("sphere_inter", gerar_esfera(0.08, 30, 30), "T")
reg("sphere_foot", gerar_esfera(0.05, 14, 14), "T")
reg("unit_cyl", gerar_cilindro(1.0, 1.0, 18, 5), "T")
reg("box_unit", gerar_caixa(1.0, 1.0, 1.0), "B")

reg("star", gerar_estrela(0.028, 0.012, 5), "T")
reg("shadow", gerar_circulo(0.22, 40), "F")

reg("ground", gerar_retangulo(2.50, 0.62), "S")
reg("ground_line", gerar_retangulo(2.50, 0.008), "S")
reg("mist", gerar_retangulo(2.30, 0.08), "S")
reg("mountain", gerar_triangulo(1.00, 1.00), "T")
reg("moon", gerar_circulo(0.11, 40), "F")
reg("cloud", gerar_circulo(0.09, 30), "F")
reg("sun_disk", gerar_circulo(0.095, 44), "F")
reg("sun_rays", gerar_raios_sol(0.11, 0.18, 12), "T")
reg("crescent", gerar_crescente(0.245, 0.220, -0.070, 0.105, 68), "T")

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
loc_use_stripes = glGetUniformLocation(program, "use_stripes")
loc_stripe_count = glGetUniformLocation(program, "stripe_count")
loc_stripe_bound_0 = glGetUniformLocation(program, "stripe_bound_0")
loc_stripe_bound_1 = glGetUniformLocation(program, "stripe_bound_1")
loc_stripe_color_0 = glGetUniformLocation(program, "stripe_color_0")
loc_stripe_color_1 = glGetUniformLocation(program, "stripe_color_1")
loc_stripe_color_2 = glGetUniformLocation(program, "stripe_color_2")

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


def ry(a):
    c = math.cos(a)
    s = math.sin(a)
    return np.array([
        c, 0, s, 0,
        0, 1, 0, 0,
        -s, 0, c, 0,
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


def set_solid_mode():
    glUniform1i(loc_use_stripes, 0)


def set_stripe_mode(limites_x, cores_faixas):
    if len(cores_faixas) not in (2, 3):
        raise RuntimeError("Apenas 2 ou 3 faixas sao suportadas")
    if len(limites_x) != len(cores_faixas) - 1:
        raise RuntimeError("Numero de limites deve ser numero de cores - 1")

    glUniform1i(loc_use_stripes, 1)
    glUniform1i(loc_stripe_count, len(cores_faixas))

    b0 = limites_x[0] if len(limites_x) >= 1 else 0.0
    b1 = limites_x[1] if len(limites_x) >= 2 else 0.0
    glUniform1f(loc_stripe_bound_0, b0)
    glUniform1f(loc_stripe_bound_1, b1)

    c0 = cores_faixas[0]
    c1 = cores_faixas[1] if len(cores_faixas) >= 2 else cores_faixas[0]
    c2 = cores_faixas[2] if len(cores_faixas) >= 3 else c1
    glUniform4f(loc_stripe_color_0, *c0)
    glUniform4f(loc_stripe_color_1, *c1)
    glUniform4f(loc_stripe_color_2, *c2)


def draw(nome, cor, mat):
    inicio, count, prim = objetos[nome]
    set_solid_mode()
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, mat)
    glUniform4f(loc_color, *cor)

    if prim == "T":
        glDrawArrays(GL_TRIANGLES, inicio, count)
    elif prim == "S":
        glDrawArrays(GL_TRIANGLE_STRIP, inicio, count)
    elif prim == "F":
        glDrawArrays(GL_TRIANGLE_FAN, inicio, count)


def draw_caixa(nome, cor, mat):
    inicio, count, prim = objetos[nome]
    if prim != "B" or count != 24:
        raise RuntimeError("Objeto de caixa invalido")

    set_solid_mode()
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, mat)
    glUniform4f(loc_color, *cor)
    for face in range(6):
        glDrawArrays(GL_TRIANGLE_STRIP, inicio + face * 4, 4)


def draw_sphere_striped(nome, mat, limites_x, cores_faixas):
    inicio, count, prim = objetos[nome]
    if prim != "T":
        raise RuntimeError("draw_sphere_striped requer objeto TRIANGLES")

    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, mat)
    set_stripe_mode(limites_x, cores_faixas)
    glDrawArrays(GL_TRIANGLES, inicio, count)
    set_solid_mode()


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


def draw_box_oriented(center, size_xyz, angle_z, color, z=0.0):
    m = mt(center[0], center[1], z)
    m = mm(m, rz(angle_z))
    m = mm(m, ms(size_xyz[0], size_xyz[1], size_xyz[2]))
    draw_caixa("box_unit", color, m)


def draw_blob(center, radii_xyz, color, z=0.0):
    # sphere_foot has radius 0.05 in object space
    m = mt(center[0], center[1], z)
    m = mm(m, ms(radii_xyz[0] / 0.05, radii_xyz[1] / 0.05, radii_xyz[2] / 0.05))
    draw("sphere_foot", color, m)


def draw_mountain_with_snow(base_x, base_y, width, height, body_color, snow_color, snow_scale=0.30):
    m_body = mm(mt(base_x, base_y, 0.01), ms(width, height, 1.0))
    draw("mountain", body_color, m_body)

    # Snow cap is the same triangle scaled around the apex, guaranteeing attachment.
    m_snow = mm(m_body, mt(0.0, 1.0, 0.0))
    m_snow = mm(m_snow, ms(snow_scale, snow_scale, 1.0))
    m_snow = mm(m_snow, mt(0.0, -1.0, 0.0))
    draw("mountain", snow_color, m_snow)


def draw_goal_left(tx, ty, scale, depth_mag):
    def lerp(a, b, t):
        return a + (b - a) * t

    def lerp2(pa, pb, t):
        return (lerp(pa[0], pb[0], t), lerp(pa[1], pb[1], t))

    def transform_pt(pt):
        return (pt[0] * scale + tx, pt[1] * scale + ty)

    frame_front = (1.00, 1.00, 1.00, 1.0)
    frame_mid = (0.85, 0.85, 0.88, 0.55)
    frame_back = (0.76, 0.76, 0.80, 0.42)
    net_color = (0.66, 0.66, 0.72, 0.45)

    r_front = 0.031 * scale
    r_mid = 0.021 * scale
    r_back = 0.018 * scale
    r_net = 0.0068 * scale

    z_near = -0.32
    z_connect = +0.02
    z_far = +0.22
    z_brace = +0.28
    z_net = +0.34

    face_tl = (-0.44, 0.28)
    face_tr = (0.44, 0.28)
    face_bl = (-0.44, -0.27)
    face_br = (0.44, -0.27)

    depth = (depth_mag, -0.62 * depth_mag)

    near_tl = (face_tl[0] + depth[0], face_tl[1] + depth[1])
    near_tr = (face_tr[0] + depth[0], face_tr[1] + depth[1])
    near_bl = (face_bl[0] + depth[0], face_bl[1] + depth[1])
    near_br = (face_br[0] + depth[0], face_br[1] + depth[1])

    far_tl = face_tl
    far_tr = face_tr
    far_bl = face_bl
    far_br = face_br

    n_tl = transform_pt(near_tl)
    n_tr = transform_pt(near_tr)
    n_bl = transform_pt(near_bl)
    n_br = transform_pt(near_br)

    f_tl = transform_pt(far_tl)
    f_tr = transform_pt(far_tr)
    f_bl = transform_pt(far_bl)
    f_br = transform_pt(far_br)

    # Back frame reduced to bottom bar only (approved goal shape).
    draw_segment(f_bl, f_br, r_back, frame_back, z=z_far)

    top_attach_l = lerp2(near_tl, far_tl, 0.55)
    top_attach_r = lerp2(near_tr, far_tr, 0.55)
    net_tl = top_attach_l
    net_tr = top_attach_r
    net_bl = far_bl
    net_br = far_br

    p_net_top_l = transform_pt(net_tl)
    p_net_top_r = transform_pt(net_tr)
    draw_segment(p_net_top_l, p_net_top_r, r_net * 0.95, net_color, z=z_net)

    for i in range(7):
        t = i / 6.0
        p_back_top = transform_pt(lerp2(net_tl, net_tr, t))
        p_front_top = transform_pt(lerp2(near_tl, near_tr, t))
        draw_segment(p_back_top, p_front_top, r_net * 0.75, net_color, z=z_net)

    for i in range(8):
        t = i / 7.0
        p0 = transform_pt(lerp2(net_tl, net_tr, t))
        p1 = transform_pt(lerp2(net_bl, net_br, t))
        draw_segment(p0, p1, r_net, net_color, z=z_net)

    for j in range(1, 4):
        u = j / 4.0
        p0 = transform_pt(lerp2(net_tl, net_bl, u))
        p1 = transform_pt(lerp2(net_tr, net_br, u))
        draw_segment(p0, p1, r_net * 0.88, net_color, z=z_net)

    left_mid_top = transform_pt(top_attach_l)
    right_mid_top = transform_pt(top_attach_r)
    draw_segment(left_mid_top, f_bl, r_back, frame_mid, z=z_brace)
    draw_segment(right_mid_top, f_br, r_back, frame_mid, z=z_brace)

    draw_segment(n_tl, left_mid_top, r_mid, frame_mid, z=z_connect)
    draw_segment(n_tr, right_mid_top, r_mid, frame_mid, z=z_connect)

    for i in range(1, 4):
        t = i / 4.0
        l_top = transform_pt(lerp2(near_tl, top_attach_l, t))
        l_bot = transform_pt(lerp2(near_bl, far_bl, t))
        draw_segment(l_top, l_bot, r_net * 0.75, net_color, z=z_net)

        r_top = transform_pt(lerp2(near_tr, top_attach_r, t))
        r_bot = transform_pt(lerp2(near_br, far_br, t))
        draw_segment(r_top, r_bot, r_net * 0.75, net_color, z=z_net)

    for j in range(1, 3):
        u = j / 3.0
        l_front_pt = transform_pt(lerp2(near_tl, near_bl, u))
        l_back_pt = transform_pt(lerp2(top_attach_l, far_bl, u))
        draw_segment(l_front_pt, l_back_pt, r_net * 0.68, net_color, z=z_net)

        r_front_pt = transform_pt(lerp2(near_tr, near_br, u))
        r_back_pt = transform_pt(lerp2(top_attach_r, far_br, u))
        draw_segment(r_front_pt, r_back_pt, r_net * 0.68, net_color, z=z_net)

    n_tl_post = (n_tl[0], n_tl[1] + r_front)
    n_tr_post = (n_tr[0], n_tr[1] + r_front)
    post_bottom_extra = 0.03 * scale
    n_bl_post = (n_bl[0], n_bl[1] - post_bottom_extra)
    n_br_post = (n_br[0], n_br[1] - post_bottom_extra)
    draw_segment(n_tl, n_tr, r_front, frame_front, z=z_near)
    draw_segment(n_tl_post, n_bl_post, r_front, frame_front, z=z_near)
    draw_segment(n_tr_post, n_br_post, r_front, frame_front, z=z_near)


def solve_ik_knee(hip, ankle, l_thigh, l_shin, bend_sign):
    dx = ankle[0] - hip[0]
    dy = ankle[1] - hip[1]
    d = math.sqrt(dx * dx + dy * dy)

    max_d = l_thigh + l_shin - 1e-5
    min_d = abs(l_thigh - l_shin) + 1e-5

    if d < 1e-7:
        ux, uy = 1.0, 0.0
        d = min_d
    else:
        ux, uy = dx / d, dy / d

    d = max(min_d, min(max_d, d))

    a = (l_thigh * l_thigh - l_shin * l_shin + d * d) / (2.0 * d)
    h2 = max(l_thigh * l_thigh - a * a, 0.0)
    h = math.sqrt(h2)

    mx = hip[0] + ux * a
    my = hip[1] + uy * a
    px, py = -uy, ux

    return (mx + bend_sign * h * px, my + bend_sign * h * py)


# ============================================================================
# Scene state and controls
# ============================================================================


def clamp(v, vmin, vmax):
    return max(vmin, min(vmax, v))


char_x = -0.05
t_stomp = 0.35
slash_angle = 0.0
hat_scale = 1.0
wireframe = False


def reset_state():
    global char_x, t_stomp, slash_angle, hat_scale, wireframe
    char_x = -0.05
    t_stomp = 0.35
    slash_angle = 0.0
    hat_scale = 1.0
    wireframe = False


def key_event(_window, key, _scancode, action, _mods):
    global char_x, t_stomp, slash_angle, hat_scale, wireframe

    if key == glfw.KEY_P and action == glfw.PRESS:
        wireframe = not wireframe
        return

    if key == glfw.KEY_R and action == glfw.PRESS:
        reset_state()
        return

    if action not in (glfw.PRESS, glfw.REPEAT):
        return

    if key == glfw.KEY_A:
        char_x = clamp(char_x - 0.03, -0.50, 0.42)
    elif key == glfw.KEY_D:
        char_x = clamp(char_x + 0.03, -0.50, 0.42)
    elif key == glfw.KEY_W:
        t_stomp = clamp(t_stomp + 0.05, 0.0, 1.0)
    elif key == glfw.KEY_S:
        t_stomp = clamp(t_stomp - 0.05, 0.0, 1.0)
    elif key == glfw.KEY_Q:
        slash_angle = clamp(slash_angle + 0.08, -0.65, 0.45)
    elif key == glfw.KEY_E:
        slash_angle = clamp(slash_angle - 0.08, -0.65, 0.45)
    elif key == glfw.KEY_Z:
        hat_scale = clamp(hat_scale + 0.05, 0.55, 1.75)
    elif key == glfw.KEY_X:
        hat_scale = clamp(hat_scale - 0.05, 0.55, 1.75)


glfw.set_key_callback(window, key_event)

# ============================================================================
# Main loop
# ============================================================================

GROUND_Y = -0.44

BLUE = (0.00, 0.24, 0.60, 1.0)
BLACK = (0.00, 0.00, 0.00, 1.0)
WHITE = (1.00, 1.00, 1.00, 1.0)
RED = (0.82, 0.03, 0.08, 1.0)
SKIN = (0.83, 0.73, 0.62, 1.0)

SKY_DAY = (0.35, 0.73, 0.99, 1.0)
GROUND_FAR = (0.67, 0.86, 0.69, 1.0)
GROUND_MAIN = (0.39, 0.69, 0.43, 1.0)
GROUND_FRONT = (0.22, 0.52, 0.31, 1.0)
GROUND_LINE = (0.90, 0.96, 0.90, 1.0)
MOUNTAIN_L = (0.45, 0.74, 0.54, 1.0)
MOUNTAIN_R = (0.40, 0.69, 0.50, 1.0)
MOUNTAIN_C = (0.35, 0.63, 0.46, 1.0)
SNOW = (0.98, 0.99, 1.00, 1.0)

R_CYL = rx(PI / 2.0)
GOAL_LEFT_X = -0.74
GOAL_LEFT_SCALE = 0.44
GOAL_LEFT_DEPTH = 0.22
# Align goal back bottom with the white mountain/floor separator line.
GOAL_LEFT_Y = (GROUND_Y + 0.001) + 0.27 * GOAL_LEFT_SCALE

glfw.show_window(window)
glEnable(GL_DEPTH_TEST)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

while not glfw.window_should_close(window):
    glfw.poll_events()

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glClearColor(*SKY_DAY)

    if wireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    else:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    # ------------------------------------------------------------------------
    # Background (medium detail)
    # ------------------------------------------------------------------------

    glDisable(GL_DEPTH_TEST)
    glDepthMask(GL_FALSE)

    # Far ground layer behind mountains
    m_far = mm(mt(0.0, GROUND_Y - 0.06), ms(1.10, 0.40, 1.0))
    draw("ground", GROUND_FAR, m_far)

    # Triangular mountain ranges with attached snow caps
    draw_mountain_with_snow(-0.79, GROUND_Y - 0.10, 1.20, 0.68, MOUNTAIN_L, SNOW, 0.31)
    draw_mountain_with_snow(0.80, GROUND_Y - 0.10, 1.24, 0.66, MOUNTAIN_R, SNOW, 0.31)
    draw_mountain_with_snow(-0.08, GROUND_Y - 0.10, 0.82, 0.46, MOUNTAIN_C, SNOW, 0.34)

    # Main floor plane (top edge aligned with GROUND_Y) + foreground strip
    m_main = mm(mt(0.0, GROUND_Y - 0.31), ms(1.12, 1.00, 1.0))
    draw("ground", GROUND_MAIN, m_main)
    draw("ground_line", GROUND_LINE, mt(0.0, GROUND_Y + 0.001))
    draw_goal_left(GOAL_LEFT_X, GOAL_LEFT_Y, GOAL_LEFT_SCALE, GOAL_LEFT_DEPTH)

    m_front = mm(mt(0.0, -0.90), ms(1.16, 0.34, 1.0))
    draw("ground", GROUND_FRONT, m_front)

    # Sun (day scene)
    draw("sun_rays", (1.00, 0.83, 0.25, 1.0), mt(0.73, 0.68, 0.01))
    draw("sun_disk", (1.00, 0.93, 0.35, 1.0), mt(0.73, 0.68, 0.02))
    draw("sun_disk", (1.00, 0.97, 0.58, 1.0), mm(mt(0.73, 0.68, 0.03), ms(0.72, 0.72, 1.0)))

    # Keep clouds away from thrown hat region (left upper-middle)
    m_cloud_a = mm(mt(-0.90, 0.74), ms(1.10, 0.78, 1.0))
    m_cloud_b = mm(mt(-0.77, 0.77), ms(0.86, 0.66, 1.0))
    m_cloud_c = mm(mt(-1.00, 0.77), ms(0.68, 0.55, 1.0))
    m_cloud_d = mm(mt(0.45, 0.62), ms(0.74, 0.53, 1.0))
    m_cloud_e = mm(mt(0.58, 0.64), ms(0.55, 0.44, 1.0))
    draw("cloud", (0.98, 0.99, 1.00, 1.0), m_cloud_a)
    draw("cloud", (0.97, 0.98, 1.00, 1.0), m_cloud_b)
    draw("cloud", (0.95, 0.97, 0.99, 1.0), m_cloud_c)
    draw("cloud", (0.93, 0.95, 0.99, 1.0), m_cloud_d)
    draw("cloud", (0.90, 0.94, 0.98, 1.0), m_cloud_e)

    # ------------------------------------------------------------------------
    # Character core
    # ------------------------------------------------------------------------

    glDepthMask(GL_TRUE)
    glEnable(GL_DEPTH_TEST)

    body_x = char_x
    body_y = 0.217 - 0.020 * t_stomp

    m_shadow = mm(mt(body_x + 0.03, GROUND_Y + 0.004, 0.72), ms(1.18, 0.17, 1.0))
    draw("shadow", (0.16, 0.16, 0.21, 1.0), m_shadow)

    m_body = mt(body_x, body_y, 0.0)
    draw_sphere_striped("sphere_body", m_body, [-0.26 / 3.0, 0.26 / 3.0], [BLUE, BLACK, WHITE])

    draw("star", (0.60, 0.42, 0.20, 1.0), mt(body_x - 0.068, body_y + 0.332, 0.0))
    draw("star", (0.75, 0.75, 0.82, 1.0), mt(body_x, body_y + 0.362, 0.0))
    draw("star", (1.00, 0.86, 0.05, 1.0), mt(body_x + 0.068, body_y + 0.332, 0.0))

    # ------------------------------------------------------------------------
    # Legs and boots (multi-part segmented)
    # ------------------------------------------------------------------------

    # Right leg (stomping) with constrained bend direction
    thigh_len_r = 0.23
    shin_len_r = 0.20
    hip_r = (body_x + 0.10, body_y - 0.16 - 0.028 * t_stomp)
    ankle_r = (body_x + 0.165 + 0.010 * t_stomp, -0.295 - 0.050 * t_stomp)
    knee_r = solve_ik_knee(hip_r, ankle_r, thigh_len_r, shin_len_r, bend_sign=1.0)

    draw_blob(hip_r, (0.026, 0.026, 0.030), (0.05, 0.05, 0.06, 1.0), z=0.05)
    draw_segment(hip_r, knee_r, 0.030, (0.04, 0.04, 0.05, 1.0), z=0.04)
    draw_blob(knee_r, (0.022, 0.022, 0.026), (0.90, 0.90, 0.95, 1.0), z=0.05)
    draw_segment(knee_r, ankle_r, 0.024, (0.97, 0.97, 0.99, 1.0), z=0.04)
    draw_segment((ankle_r[0], ankle_r[1] + 0.008), (ankle_r[0], ankle_r[1] - 0.010), 0.020, (0.04, 0.04, 0.05, 1.0), z=0.05)

    foot_r_angle = 0.20
    foot_r_core = (ankle_r[0] + 0.020, ankle_r[1] - 0.018)
    draw_box_oriented(foot_r_core, (0.128, 0.018, 0.055), foot_r_angle, (0.02, 0.02, 0.03, 1.0), z=0.06)
    draw_blob((foot_r_core[0] - 0.012, foot_r_core[1] + 0.022), (0.057, 0.028, 0.060), (0.06, 0.06, 0.08, 1.0), z=0.07)
    draw_blob((foot_r_core[0] + 0.060, foot_r_core[1] + 0.012), (0.032, 0.019, 0.036), (0.02, 0.02, 0.03, 1.0), z=0.07)
    draw_box_oriented((foot_r_core[0] - 0.004, foot_r_core[1] + 0.009), (0.082, 0.010, 0.040), foot_r_angle, (0.96, 0.96, 0.98, 1.0), z=0.075)
    draw_box_oriented((foot_r_core[0] + 0.045, foot_r_core[1] + 0.020), (0.028, 0.004, 0.016), foot_r_angle, (0.86, 0.86, 0.90, 1.0), z=0.078)

    # Left leg (support)
    thigh_len_l = 0.24
    shin_len_l = 0.22
    hip_l = (body_x - 0.11, body_y - 0.18)
    ankle_l = (body_x - 0.030, GROUND_Y + 0.016)
    knee_l = solve_ik_knee(hip_l, ankle_l, thigh_len_l, shin_len_l, bend_sign=-1.0)

    draw_blob(hip_l, (0.026, 0.026, 0.030), (0.05, 0.05, 0.06, 1.0), z=0.03)
    draw_segment(hip_l, knee_l, 0.030, (0.04, 0.04, 0.05, 1.0), z=0.02)
    draw_blob(knee_l, (0.022, 0.022, 0.026), (0.92, 0.92, 0.96, 1.0), z=0.03)
    draw_segment(knee_l, ankle_l, 0.024, (0.97, 0.97, 0.99, 1.0), z=0.02)
    draw_segment((ankle_l[0], ankle_l[1] + 0.008), (ankle_l[0], ankle_l[1] - 0.010), 0.020, (0.04, 0.04, 0.05, 1.0), z=0.03)

    foot_l_angle = -0.02
    foot_l_core = (ankle_l[0] - 0.008, GROUND_Y)
    draw_box_oriented(foot_l_core, (0.132, 0.019, 0.055), foot_l_angle, (0.02, 0.02, 0.03, 1.0), z=0.04)
    draw_blob((foot_l_core[0] - 0.015, foot_l_core[1] + 0.022), (0.062, 0.029, 0.060), (0.06, 0.06, 0.08, 1.0), z=0.05)
    draw_blob((foot_l_core[0] + 0.062, foot_l_core[1] + 0.010), (0.031, 0.019, 0.035), (0.03, 0.03, 0.04, 1.0), z=0.05)
    draw_box_oriented((foot_l_core[0] - 0.006, foot_l_core[1] + 0.009), (0.086, 0.010, 0.040), foot_l_angle, (0.94, 0.94, 0.97, 1.0), z=0.055)
    draw_box_oriented((foot_l_core[0] + 0.042, foot_l_core[1] + 0.018), (0.030, 0.004, 0.018), foot_l_angle, (0.84, 0.84, 0.89, 1.0), z=0.058)

    # ------------------------------------------------------------------------
    # Arms, hands and sword (multi-part)
    # ------------------------------------------------------------------------

    shoulder_r = (body_x + 0.215, body_y + 0.050)
    shoulder_l = (body_x - 0.215, body_y + 0.030)
    upper_len = 0.13
    fore_len = 0.14

    # Right arm with slash control
    upper_a_r = 1.35 + slash_angle * 0.85
    fore_a_r = 1.95 + slash_angle * 1.10
    elbow_r = (
        shoulder_r[0] + math.sin(upper_a_r) * upper_len,
        shoulder_r[1] - math.cos(upper_a_r) * upper_len,
    )
    hand_r = (
        elbow_r[0] + math.sin(fore_a_r) * fore_len,
        elbow_r[1] - math.cos(fore_a_r) * fore_len,
    )
    dir_r = (math.sin(fore_a_r), -math.cos(fore_a_r))
    perp_r = (-dir_r[1], dir_r[0])

    draw_blob(shoulder_r, (0.024, 0.024, 0.026), (0.02, 0.14, 0.38, 1.0), z=0.09)
    draw_segment(shoulder_r, elbow_r, 0.022, (0.02, 0.14, 0.38, 1.0), z=0.08)
    draw_blob(elbow_r, (0.020, 0.020, 0.024), (0.86, 0.88, 0.93, 1.0), z=0.09)
    draw_segment(elbow_r, hand_r, 0.019, (0.88, 0.90, 0.95, 1.0), z=0.08)
    draw_segment((hand_r[0] - dir_r[0] * 0.010, hand_r[1] - dir_r[1] * 0.010), (hand_r[0] + dir_r[0] * 0.010, hand_r[1] + dir_r[1] * 0.010), 0.017, (0.04, 0.04, 0.05, 1.0), z=0.10)

    palm_r = (hand_r[0] + dir_r[0] * 0.020, hand_r[1] + dir_r[1] * 0.020)
    draw_box_oriented(palm_r, (0.040, 0.018, 0.045), fore_a_r, SKIN, z=0.11)
    thumb_r = (palm_r[0] + perp_r[0] * 0.016, palm_r[1] + perp_r[1] * 0.016)
    draw_box_oriented(thumb_r, (0.018, 0.009, 0.020), fore_a_r + 0.55, SKIN, z=0.12)

    # Left arm (empty hand)
    upper_a_l = -2.35
    fore_a_l = -2.05
    elbow_l = (
        shoulder_l[0] + math.sin(upper_a_l) * upper_len,
        shoulder_l[1] - math.cos(upper_a_l) * upper_len,
    )
    hand_l = (
        elbow_l[0] + math.sin(fore_a_l) * 0.12,
        elbow_l[1] - math.cos(fore_a_l) * 0.12,
    )
    dir_l = (math.sin(fore_a_l), -math.cos(fore_a_l))
    perp_l = (-dir_l[1], dir_l[0])

    draw_blob(shoulder_l, (0.024, 0.024, 0.026), (0.02, 0.14, 0.38, 1.0), z=0.07)
    draw_segment(shoulder_l, elbow_l, 0.022, (0.02, 0.14, 0.38, 1.0), z=0.06)
    draw_blob(elbow_l, (0.020, 0.020, 0.024), (0.86, 0.88, 0.93, 1.0), z=0.07)
    draw_segment(elbow_l, hand_l, 0.019, (0.88, 0.90, 0.95, 1.0), z=0.06)
    draw_segment((hand_l[0] - dir_l[0] * 0.010, hand_l[1] - dir_l[1] * 0.010), (hand_l[0] + dir_l[0] * 0.010, hand_l[1] + dir_l[1] * 0.010), 0.017, (0.04, 0.04, 0.05, 1.0), z=0.08)

    palm_l = (hand_l[0] + dir_l[0] * 0.015, hand_l[1] + dir_l[1] * 0.015)
    draw_box_oriented(palm_l, (0.045, 0.020, 0.046), fore_a_l, SKIN, z=0.09)
    for i in range(3):
        off = -0.014 + i * 0.014
        finger_c = (palm_l[0] + perp_l[0] * off + dir_l[0] * 0.020, palm_l[1] + perp_l[1] * off + dir_l[1] * 0.020)
        draw_box_oriented(finger_c, (0.016, 0.006, 0.016), fore_a_l + 0.05, SKIN, z=0.10)

    # Sword attached to right hand
    sword_a = fore_a_r - 0.10
    sword_dir = (math.sin(sword_a), -math.cos(sword_a))
    sword_perp = (-sword_dir[1], sword_dir[0])

    pommel = (hand_r[0] - sword_dir[0] * 0.026, hand_r[1] - sword_dir[1] * 0.026)
    grip_start = (hand_r[0] - sword_dir[0] * 0.016, hand_r[1] - sword_dir[1] * 0.016)
    grip_end = (hand_r[0] + sword_dir[0] * 0.090, hand_r[1] + sword_dir[1] * 0.090)
    guard_center = (hand_r[0] + sword_dir[0] * 0.090, hand_r[1] + sword_dir[1] * 0.090)
    blade_start = (hand_r[0] + sword_dir[0] * 0.118, hand_r[1] + sword_dir[1] * 0.118)
    blade_mid = (hand_r[0] + sword_dir[0] * 0.355, hand_r[1] + sword_dir[1] * 0.355)
    blade_tip = (hand_r[0] + sword_dir[0] * 0.402, hand_r[1] + sword_dir[1] * 0.402)

    draw_blob(pommel, (0.014, 0.014, 0.016), (0.55, 0.50, 0.22, 1.0), z=0.13)
    draw_segment(grip_start, grip_end, 0.014, (0.32, 0.22, 0.12, 1.0), z=0.12)
    draw_box_oriented(guard_center, (0.072, 0.012, 0.020), sword_a + PI / 2.0, (0.72, 0.72, 0.78, 1.0), z=0.14)
    draw_segment((blade_start[0] - sword_dir[0] * 0.020, blade_start[1] - sword_dir[1] * 0.020), blade_start, 0.011, (0.50, 0.50, 0.56, 1.0), z=0.125)
    draw_segment(blade_start, blade_mid, 0.010, (0.84, 0.85, 0.91, 1.0), z=0.125)
    draw_segment(blade_mid, blade_tip, 0.006, (0.94, 0.95, 0.98, 1.0), z=0.125)
    draw_segment((blade_start[0] + sword_dir[0] * 0.010, blade_start[1] + sword_dir[1] * 0.010), (blade_mid[0] - sword_dir[0] * 0.015, blade_mid[1] - sword_dir[1] * 0.015), 0.003, (0.67, 0.69, 0.77, 1.0), z=0.128)
    draw_box_oriented((blade_tip[0] + sword_dir[0] * 0.007, blade_tip[1] + sword_dir[1] * 0.007), (0.012, 0.004, 0.010), sword_a, (0.95, 0.95, 0.99, 1.0), z=0.126)
    draw_box_oriented((guard_center[0] + sword_perp[0] * 0.003, guard_center[1] + sword_perp[1] * 0.003), (0.030, 0.004, 0.008), sword_a, (0.58, 0.58, 0.62, 1.0), z=0.145)

    # ------------------------------------------------------------------------
    # Inter ball with squash (kept)
    # ------------------------------------------------------------------------

    inter_sx = 1.0 + 0.30 * t_stomp
    inter_sy = 1.0 - 0.45 * t_stomp
    inter_x = ankle_r[0] + 0.012
    inter_y = GROUND_Y + 0.08 * inter_sy - 0.015

    m_i_shadow = mm(mt(inter_x, GROUND_Y + 0.002, 0.73), ms(0.62 * inter_sx, 0.10, 1.0))
    draw("shadow", (0.16, 0.16, 0.21, 1.0), m_i_shadow)

    m_inter = mm(mt(inter_x, inter_y, 0.0), ms(inter_sx, inter_sy, 1.0))
    draw_sphere_striped("sphere_inter", m_inter, [0.0], [RED, WHITE])

    # ------------------------------------------------------------------------
    # Hat in throw pose above empty hand (left hand)
    # ------------------------------------------------------------------------

    hat_anchor_x = palm_l[0] - 0.012
    hat_anchor_y = palm_l[1] + 0.160
    hat_tilt = -0.62

    m_hat_brim = mt(hat_anchor_x, hat_anchor_y, -0.10)
    m_hat_brim = mm(m_hat_brim, rz(hat_tilt))
    m_hat_brim = mm(m_hat_brim, ms((0.095 * hat_scale) / 0.05, (0.028 * hat_scale) / 0.05, (0.070 * hat_scale) / 0.05))
    draw("sphere_foot", (0.08, 0.08, 0.10, 1.0), m_hat_brim)

    m_hat_crown = mt(hat_anchor_x + 0.004, hat_anchor_y + 0.042 * hat_scale, -0.095)
    m_hat_crown = mm(m_hat_crown, rz(hat_tilt))
    m_hat_crown = mm(m_hat_crown, R_CYL)
    m_hat_crown = mm(m_hat_crown, ms(0.038 * hat_scale, 0.038 * hat_scale, 0.100 * hat_scale))
    draw("unit_cyl", (0.10, 0.10, 0.12, 1.0), m_hat_crown)

    m_hat_band = mt(hat_anchor_x + 0.003, hat_anchor_y + 0.020 * hat_scale, -0.090)
    m_hat_band = mm(m_hat_band, rz(hat_tilt))
    m_hat_band = mm(m_hat_band, R_CYL)
    m_hat_band = mm(m_hat_band, ms(0.043 * hat_scale, 0.043 * hat_scale, 0.012 * hat_scale))
    draw("unit_cyl", (0.78, 0.74, 0.16, 1.0), m_hat_band)

    draw_box_oriented((hat_anchor_x - 0.045, hat_anchor_y + 0.016), (0.022 * hat_scale, 0.006 * hat_scale, 0.010 * hat_scale), hat_tilt - 0.8, (0.78, 0.74, 0.16, 1.0), z=-0.085)

    glfw.swap_buffers(window)

glfw.terminate()
