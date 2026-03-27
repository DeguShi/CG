import glfw
from OpenGL.GL import *
import numpy as np
import math
import ctypes
import base64
import zlib

try:
    from _logo_payloads import LOGO_W, LOGO_H, LOGO_PRETO_B64, LOGO_BRANCO_B64, LOGO_AZUL_B64
except ModuleNotFoundError:
    from projeto_1._logo_payloads import LOGO_W, LOGO_H, LOGO_PRETO_B64, LOGO_BRANCO_B64, LOGO_AZUL_B64

# =========================================================
# GLFW
# =========================================================

if not glfw.init():
    raise RuntimeError("Falha ao inicializar GLFW")

glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
window = glfw.create_window(900, 900, "Estudo - Esfera Gremio", None, None)
if not window:
    glfw.terminate()
    raise RuntimeError("Falha ao criar janela")

glfw.make_context_current(window)

# =========================================================
# Shaders
# =========================================================

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

# =========================================================
# Helpers
# =========================================================

PI = 3.141592


def gerar_esfera(raio, num_sectors, num_stacks):
    sector_step = (PI * 2) / num_sectors
    stack_step = PI / num_stacks

    def F(u, v, r):
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
            un = PI * 2 if i + 1 == num_sectors else (i + 1) * sector_step
            vn = PI if j + 1 == num_stacks else (j + 1) * stack_step

            p0 = F(u, v, raio)
            p1 = F(u, vn, raio)
            p2 = F(un, v, raio)
            p3 = F(un, vn, raio)

            verts += [p0, p2, p1, p3, p1, p2]

    return verts


def gerar_circulo(raio, n):
    verts = []
    for i in range(n):
        a = (i + 1) * 2 * PI / n
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


def gerar_estrela(r_outer, r_inner, pontas=5):
    pts = []
    for i in range(pontas * 2):
        ang = i * PI / pontas - PI / 2.0
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((math.cos(ang) * r, math.sin(ang) * r, 0.0))

    verts = []
    centro = (0.0, 0.0, 0.0)
    for i in range(len(pts)):
        p0 = pts[i]
        p1 = pts[(i + 1) % len(pts)]
        verts += [centro, p0, p1]
    return verts


def decodificar_mascara_logo(payload_b64, w, h):
    packed = zlib.decompress(base64.b64decode(payload_b64))
    bits = np.unpackbits(np.frombuffer(packed, dtype=np.uint8), bitorder="little")
    return bits[:w * h].reshape((h, w)).astype(np.uint8)


def gerar_triangulos_mascara(mask):
    h, w = mask.shape
    cx = w / 2.0
    cy = h / 2.0
    s = w / 2.0

    verts = []
    for y in range(h):
        row = mask[y]
        x = 0
        while x < w:
            if row[x] == 0:
                x += 1
                continue

            run_start = x
            while x < w and row[x] != 0:
                x += 1
            run_end = x

            xl = (run_start - cx) / s
            xr = (run_end - cx) / s
            yt = (cy - y) / s
            yb = (cy - (y + 1)) / s

            verts += [
                (xl, yt, 0.0), (xr, yt, 0.0), (xl, yb, 0.0),
                (xr, yt, 0.0), (xr, yb, 0.0), (xl, yb, 0.0),
            ]
    return verts


# =========================================================
# Object registry
# =========================================================

objetos = {}
todos_vertices = []


def reg(nome, verts, prim="T"):
    inicio = len(todos_vertices)
    todos_vertices.extend(verts)
    objetos[nome] = (inicio, len(verts), prim)


# Body
reg("corpo", gerar_esfera(0.28, 30, 30), "T")

# Shadow
reg("sombra", gerar_circulo(0.20, 40), "F")
reg("estrela", gerar_estrela(0.030, 0.013, 5), "T")

# Gremio badge geometry from reference image (sem textura, sem texto)
logo_preto_mask = decodificar_mascara_logo(LOGO_PRETO_B64, LOGO_W, LOGO_H)
logo_branco_mask = decodificar_mascara_logo(LOGO_BRANCO_B64, LOGO_W, LOGO_H)
logo_azul_mask = decodificar_mascara_logo(LOGO_AZUL_B64, LOGO_W, LOGO_H)

reg("logo_preto", gerar_triangulos_mascara(logo_preto_mask), "T")
reg("logo_branco", gerar_triangulos_mascara(logo_branco_mask), "T")
reg("logo_azul", gerar_triangulos_mascara(logo_azul_mask), "T")

# =========================================================
# Upload to GPU
# =========================================================

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

# =========================================================
# Matrix helpers
# =========================================================

def mm(a, b):
    return np.dot(a.reshape(4, 4), b.reshape(4, 4)).reshape(1, 16).astype(np.float32)


def mt(tx, ty, tz=0.0):
    return np.array([
        1, 0, 0, tx,
        0, 1, 0, ty,
        0, 0, 1, tz,
        0, 0, 0, 1
    ], np.float32)


def ms(sx, sy, sz=1.0):
    return np.array([
        sx, 0,  0,  0,
        0,  sy, 0,  0,
        0,  0,  sz, 0,
        0,  0,  0,  1
    ], np.float32)


def ry(a):
    c = math.cos(a)
    s = math.sin(a)
    return np.array([
         c, 0, s, 0,
         0, 1, 0, 0,
        -s, 0, c, 0,
         0, 0, 0, 1
    ], np.float32)


# =========================================================
# Drawing helpers
# =========================================================

def draw(nome, cor, mat):
    ini, cnt, prim = objetos[nome]
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, mat)
    glUniform4f(loc_color, *cor)

    if prim == "T":
        glDrawArrays(GL_TRIANGLES, ini, cnt)
    elif prim == "S":
        glDrawArrays(GL_TRIANGLE_STRIP, ini, cnt)
    elif prim == "F":
        glDrawArrays(GL_TRIANGLE_FAN, ini, cnt)


# =========================================================
# Scene params
# =========================================================

rot_y = 0.0
body_x = 0.0
body_y = 0.02

# =========================================================
# Window
# =========================================================

glfw.show_window(window)
glEnable(GL_DEPTH_TEST)

# =========================================================
# Main loop
# =========================================================

while not glfw.window_should_close(window):
    glfw.poll_events()

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glClearColor(0.97, 0.97, 0.98, 1.0)

    # ---------------------------------------------
    # Shadow under sphere (fake shadow, still allowed stylistically)
    # ---------------------------------------------
    m_shadow = mm(mt(body_x, -0.35, -0.05), ms(1.4, 0.35, 1.0))
    draw("sombra", (0.15, 0.15, 0.18, 0.35), m_shadow)

    # ---------------------------------------------
    # Main sphere body
    # ---------------------------------------------
    m_body = mm(mt(body_x, body_y, 0.0), ry(rot_y))
    draw("corpo", (0.00, 0.24, 0.60, 1.0), m_body)
    glDisable(GL_DEPTH_TEST)

    # ---------------------------------------------
    # Front badge - extraido da referencia (formas geometricas, sem texto)
    # ---------------------------------------------
    # Match the sphere projection while keeping the crest fully inside.
    logo_scale = 0.279
    m_logo = mm(mt(body_x, body_y, 0.346), ms(logo_scale, logo_scale, 1.0))
    draw("logo_preto", (0.00, 0.00, 0.00, 1.0), m_logo)
    draw("logo_branco", (1.00, 1.00, 1.00, 1.0), m_logo)
    draw("logo_azul", (13.0 / 255.0, 128.0 / 255.0, 191.0 / 255.0, 1.0), m_logo)

    # ---------------------------------------------
    # Stars above
    # ---------------------------------------------
    draw("estrela", (0.60, 0.42, 0.20, 1.0), mt(body_x - 0.06, body_y + 0.36, 0.0))
    draw("estrela", (0.75, 0.75, 0.82, 1.0), mt(body_x,         body_y + 0.39, 0.0))
    draw("estrela", (1.00, 0.86, 0.05, 1.0), mt(body_x + 0.06, body_y + 0.36, 0.0))
    glEnable(GL_DEPTH_TEST)

    glfw.swap_buffers(window)

glfw.terminate()
