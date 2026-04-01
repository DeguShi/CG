import glfw
from OpenGL.GL import *
import numpy as np
import math
import ctypes

PI = 3.141592
NUM_SECTORS = 30
NUM_STACKS = 30


# =========================================================
# GLFW
# =========================================================

if not glfw.init():
    raise RuntimeError("Falha ao inicializar GLFW")

glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
window = glfw.create_window(900, 900, "Estudo - Esfera Inter", None, None)
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


# =========================================================
# Geometry helpers
# =========================================================

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


# =========================================================
# Object registry
# =========================================================

objetos = {}
todos_vertices = []


def reg(nome, verts, prim="T"):
    inicio = len(todos_vertices)
    todos_vertices.extend(verts)
    objetos[nome] = (inicio, len(verts), prim)


# Inter sphere
reg("corpo", gerar_esfera(0.28, NUM_SECTORS, NUM_STACKS), "T")
reg("sombra", gerar_circulo(0.20, 40), "F")


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
loc_use_stripes = glGetUniformLocation(program, "use_stripes")
loc_stripe_count = glGetUniformLocation(program, "stripe_count")
loc_stripe_bound_0 = glGetUniformLocation(program, "stripe_bound_0")
loc_stripe_bound_1 = glGetUniformLocation(program, "stripe_bound_1")
loc_stripe_color_0 = glGetUniformLocation(program, "stripe_color_0")
loc_stripe_color_1 = glGetUniformLocation(program, "stripe_color_1")
loc_stripe_color_2 = glGetUniformLocation(program, "stripe_color_2")


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

def set_solid_mode():
    glUniform1i(loc_use_stripes, 0)


def set_stripe_mode(limites_x, cores_faixas):
    if len(cores_faixas) not in (2, 3):
        raise RuntimeError("apenas 2 ou 3 faixas sao suportadas")
    if len(limites_x) != len(cores_faixas) - 1:
        raise RuntimeError("numero de limites deve ser numero de cores - 1")

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
    ini, cnt, prim = objetos[nome]
    set_solid_mode()
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, mat)
    glUniform4f(loc_color, *cor)

    if prim == "T":
        glDrawArrays(GL_TRIANGLES, ini, cnt)
    elif prim == "F":
        glDrawArrays(GL_TRIANGLE_FAN, ini, cnt)


def draw_esfera_faixas_verticais(nome, mat, limites_x, cores_faixas):
    ini, cnt, prim = objetos[nome]
    if prim != "T":
        raise RuntimeError("draw_esfera_faixas_verticais requer primitiva TRIANGLES")
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, mat)
    set_stripe_mode(limites_x, cores_faixas)
    glDrawArrays(GL_TRIANGLES, ini, cnt)
    set_solid_mode()


# =========================================================
# Scene params
# =========================================================

rot_y = 0.0
body_x = 0.0
body_y = 0.02


# =========================================================
# Main loop
# =========================================================

glfw.show_window(window)
glEnable(GL_DEPTH_TEST)

while not glfw.window_should_close(window):
    glfw.poll_events()

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glClearColor(0.97, 0.97, 0.98, 1.0)

    m_shadow = mm(mt(body_x, -0.35, -0.05), ms(1.4, 0.35, 1.0))
    draw("sombra", (0.15, 0.15, 0.18, 0.35), m_shadow)

    m_body = mm(mt(body_x, body_y, 0.0), ry(rot_y))
    vermelho = (0.82, 0.03, 0.08, 1.0)
    branco = (1.00, 1.00, 1.00, 1.0)
    # Duas faixas verticais: vermelho e branco
    limites_inter = [0.0]
    cores_inter = [vermelho, branco]
    draw_esfera_faixas_verticais("corpo", m_body, limites_inter, cores_inter)

    glfw.swap_buffers(window)

glfw.terminate()
