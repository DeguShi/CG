"""
=============================================================================
Computação Gráfica - Projeto 1
Cena estilizada: Grêmio pisando no Inter

Objetos (6, sendo 3 volumétricos/3D):
  1. Personagem Grêmio (esfera 3D + emblema frontal geométrico + membros)
  2. Esfera Inter (esfera 3D menor + badge frontal, fixa no chão)
  3. Trave (goleira 3D - caixas volumétricas)
  4. Campo de futebol (2D - grama + linhas)
  5. Nuvem (2D - círculos sobrepostos)
  6. Sol (2D - círculo + raios)

Controles:
  A / S          -> parâmetro de pisada (sobe/desce)
  Setas ← → ↑ ↓ -> translação da nuvem
  Z / X          -> escala do sol
  P              -> wireframe
  R              -> reset
=============================================================================
"""

import glfw
from OpenGL.GL import *
import numpy as np
import math
import ctypes

# ============================================================================
# GLFW
# ============================================================================

glfw.init()
glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
window = glfw.create_window(800, 800, "Projeto 1 - Gremio vs Inter", None, None)
if window is None:
    print("Falha ao criar janela GLFW")
    glfw.terminate()
    raise SystemExit

glfw.make_context_current(window)

# ============================================================================
# Shaders
# ============================================================================

vertex_code = """
        attribute vec3 position;
        uniform mat4 mat_transformation;
        void main(){
            gl_Position = mat_transformation * vec4(position,1.0);
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
    error = glGetShaderInfoLog(vertex).decode()
    print(error)
    raise RuntimeError("Erro de compilacao do Vertex Shader")

glCompileShader(fragment)
if not glGetShaderiv(fragment, GL_COMPILE_STATUS):
    error = glGetShaderInfoLog(fragment).decode()
    print(error)
    raise RuntimeError("Erro de compilacao do Fragment Shader")

glAttachShader(program, vertex)
glAttachShader(program, fragment)

glLinkProgram(program)
if not glGetProgramiv(program, GL_LINK_STATUS):
    print(glGetProgramInfoLog(program))
    raise RuntimeError("Linking error")

glUseProgram(program)

# ============================================================================
# Geradores de vértices
# ============================================================================

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
            p0, p1, p2, p3 = F(u, v, raio), F(u, vn, raio), F(un, v, raio), F(un, vn, raio)
            verts += [p0, p2, p1, p3, p1, p2]
    return verts


def gerar_cilindro(raio, altura, ns, nst):
    ss = (PI * 2) / ns
    hs = altura / nst
    z0 = -altura / 2.0

    def C(t, h, r):
        return (r * math.cos(t), r * math.sin(t), h)

    verts = []
    for j in range(nst):
        for i in range(ns):
            u = i * ss
            v = z0 + j * hs
            un = PI * 2 if i + 1 == ns else (i + 1) * ss
            vn = z0 + altura if j + 1 == nst else z0 + (j + 1) * hs

            p0, p1, p2, p3 = C(u, v, raio), C(u, vn, raio), C(un, v, raio), C(un, vn, raio)
            verts += [p0, p2, p1, p3, p1, p2]

            if j == 0:
                verts += [p0, p2, (0, 0, v)]
            if j + 1 == nst:
                verts += [p1, p3, (0, 0, vn)]
    return verts


def gerar_circulo(raio, n):
    verts = []
    for i in range(n):
        a = (i + 1) * 2 * PI / n
        verts.append((math.cos(a) * raio, math.sin(a) * raio, 0.0))
    return verts


def gerar_retangulo(w, h):
    hw, hh = w / 2.0, h / 2.0
    return [(hw, -hh, 0.0), (hw, hh, 0.0), (-hw, -hh, 0.0), (-hw, hh, 0.0)]


def gerar_caixa(w, h, d):
    hw, hh, hd = w / 2.0, h / 2.0, d / 2.0
    return [
        (-hw, -hh, +hd), (+hw, -hh, +hd), (-hw, +hh, +hd), (+hw, +hh, +hd),
        (+hw, -hh, +hd), (+hw, -hh, -hd), (+hw, +hh, +hd), (+hw, +hh, -hd),
        (+hw, -hh, -hd), (-hw, -hh, -hd), (+hw, +hh, -hd), (-hw, +hh, -hd),
        (-hw, -hh, -hd), (-hw, -hh, +hd), (-hw, +hh, -hd), (-hw, +hh, +hd),
        (-hw, -hh, -hd), (+hw, -hh, -hd), (-hw, -hh, +hd), (+hw, -hh, +hd),
        (-hw, +hh, +hd), (+hw, +hh, +hd), (-hw, +hh, -hd), (+hw, +hh, -hd),
    ]


# ============================================================================
# Registro de objetos
# ============================================================================

objetos = {}
todos_vertices = []


def reg(nome, verts, prim="T"):
    inicio = len(todos_vertices)
    todos_vertices.extend(verts)
    objetos[nome] = (inicio, len(verts), prim)


# --- 1. GRÊMIO ---
reg("g_corpo", gerar_esfera(0.25, 24, 24))
reg("g_emb_anel_preto", gerar_circulo(0.21, 40), "F")
reg("g_emb_azul", gerar_circulo(0.18, 36), "F")
reg("g_emb_branco", gerar_circulo(0.13, 32), "F")
reg("g_emb_listra_v", gerar_retangulo(0.06, 0.24), "S")
reg("g_emb_listra_h", gerar_retangulo(0.24, 0.04), "S")
reg("g_estrela", gerar_circulo(0.018, 6), "F")

# Perna de apoio
reg("g_coxa", gerar_cilindro(0.032, 0.12, 10, 3))
reg("g_canela", gerar_cilindro(0.028, 0.14, 10, 3))

# Perna que pisa: coxa mais comprida
reg("g_coxa_stomp", gerar_cilindro(0.040, 0.18, 10, 4))
reg("g_canela_stomp", gerar_cilindro(0.032, 0.14, 10, 3))

reg("g_pe", gerar_esfera(0.04, 8, 8))
reg("g_pe_ap", gerar_esfera(0.04, 8, 8))
reg("g_braco", gerar_cilindro(0.022, 0.18, 8, 3))

# --- 2. INTER ---
reg("i_corpo", gerar_esfera(0.07, 16, 16))
reg("i_badge_branco", gerar_circulo(0.065, 24), "F")
reg("i_badge_vermelho", gerar_circulo(0.050, 20), "F")

# --- 3. TRAVE ---
reg("trave_poste", gerar_caixa(0.022, 0.42, 0.022))
reg("trave_barra", gerar_caixa(0.42, 0.022, 0.022))

# --- 4. CAMPO ---
reg("campo", gerar_retangulo(2.5, 0.70), "S")
reg("campo_linha", gerar_retangulo(0.004, 0.55), "S")
reg("campo_linha_h", gerar_retangulo(1.8, 0.004), "S")
reg("campo_circulo", gerar_circulo(0.07, 28), "F")

# --- 5. NUVEM ---
reg("nuvem", gerar_circulo(0.07, 20), "F")
reg("nuvem_m", gerar_circulo(0.09, 20), "F")
reg("nuvem_p", gerar_circulo(0.055, 20), "F")

# --- 6. SOL ---
reg("sol", gerar_circulo(0.08, 24), "F")
raios = []
for i in range(8):
    a = i * PI / 4
    an = (i + 0.5) * PI / 4
    ap = (i - 0.5) * PI / 4
    raios += [
        (math.cos(ap) * 0.07, math.sin(ap) * 0.07, 0.0),
        (math.cos(an) * 0.07, math.sin(an) * 0.07, 0.0),
        (math.cos(a) * 0.14, math.sin(a) * 0.14, 0.0),
    ]
reg("sol_raios", raios)

# ============================================================================
# VBO
# ============================================================================

total_v = len(todos_vertices)
vertices = np.zeros(total_v, [("position", np.float32, 3)])
vertices["position"] = np.array(todos_vertices)

buf = glGenBuffers(1)
glBindBuffer(GL_ARRAY_BUFFER, buf)
glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
glBindBuffer(GL_ARRAY_BUFFER, buf)

stride = vertices.strides[0]
offset = ctypes.c_void_p(0)
loc_pos = glGetAttribLocation(program, "position")
glEnableVertexAttribArray(loc_pos)
glVertexAttribPointer(loc_pos, 3, GL_FLOAT, False, stride, offset)

loc_color = glGetUniformLocation(program, "color")
loc_mat = glGetUniformLocation(program, "mat_transformation")

# ============================================================================
# Estado
# ============================================================================

t_stomp = 0.5
t_nuvem_x = 0.0
t_nuvem_y = 0.0
s_sol = 1.0
wireframe = False

# ============================================================================
# Teclado
# ============================================================================

def key_event(window, key, scancode, action, mods):
    global t_stomp, t_nuvem_x, t_nuvem_y, s_sol, wireframe

    if key == 65:   # A
        t_stomp = max(0.0, t_stomp - 0.05)
    if key == 83:   # S
        t_stomp = min(1.0, t_stomp + 0.05)

    if key == 263:
        t_nuvem_x -= 0.02
    if key == 262:
        t_nuvem_x += 0.02
    if key == 265:
        t_nuvem_y += 0.02
    if key == 264:
        t_nuvem_y -= 0.02

    if key == 90:
        s_sol += 0.05
    if key == 88:
        s_sol = max(0.3, s_sol - 0.05)

    if key == 80 and action == 1:
        wireframe = not wireframe

    if key == 82:
        t_stomp = 0.5
        t_nuvem_x = 0.0
        t_nuvem_y = 0.0
        s_sol = 1.0
        wireframe = False


glfw.set_key_callback(window, key_event)

# ============================================================================
# Matrizes
# ============================================================================

def mm(a, b):
    return np.dot(a.reshape(4, 4), b.reshape(4, 4)).reshape(1, 16).astype(np.float32)


def mt(tx, ty, tz=0.0):
    return np.array(
        [1, 0, 0, tx,
         0, 1, 0, ty,
         0, 0, 1, tz,
         0, 0, 0, 1], np.float32
    )


def ms(sx, sy, sz=1.0):
    return np.array(
        [sx, 0, 0, 0,
         0, sy, 0, 0,
         0, 0, sz, 0,
         0, 0, 0, 1], np.float32
    )


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(
        [c, -s, 0, 0,
         s,  c, 0, 0,
         0,  0, 1, 0,
         0,  0, 0, 1], np.float32
    )


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(
        [ c, 0, s, 0,
          0, 1, 0, 0,
         -s, 0, c, 0,
          0, 0, 0, 1], np.float32
    )


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(
        [1, 0, 0, 0,
         0, c, -s, 0,
         0, s,  c, 0,
         0, 0, 0, 1], np.float32
    )


# ============================================================================
# Desenho
# ============================================================================

def draw(nome, cor, m):
    ini, cnt, prim = objetos[nome]
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, m)
    glUniform4f(loc_color, *cor)
    if prim == "T":
        glDrawArrays(GL_TRIANGLES, ini, cnt)
    elif prim == "S":
        glDrawArrays(GL_TRIANGLE_STRIP, ini, cnt)
    elif prim == "F":
        glDrawArrays(GL_TRIANGLE_FAN, ini, cnt)


def draw_caixa(nome, cor, m):
    ini, cnt, _ = objetos[nome]
    glUniformMatrix4fv(loc_mat, 1, GL_TRUE, m)
    glUniform4f(loc_color, *cor)
    for f in range(6):
        glDrawArrays(GL_TRIANGLE_STRIP, ini + f * 4, 4)


# ============================================================================
# Constantes de posição
# ============================================================================

CHAO_Y = -0.35

GX = -0.08
GY_BASE = 0.18

Q_DX_DIR = 0.04   # stomping hip slightly more inward
Q_DX_ESQ = -0.07
Q_DY = -0.18      # hips slightly higher to stay inside body

COXA_L = 0.12
COXA_L_STOMP = 0.18
CANELA_L = 0.14

PRESS_COXA_ANG = -0.02
PRESS_CANELA_ANG = 0.0

CONTACT_FOOT_X = (
    GX + Q_DX_DIR
    + math.sin(PRESS_COXA_ANG) * COXA_L_STOMP
    + math.sin(PRESS_CANELA_ANG) * CANELA_L
)

CONTACT_FOOT_Y = (
    GY_BASE + Q_DY
    - math.cos(PRESS_COXA_ANG) * COXA_L_STOMP
    - math.cos(PRESS_CANELA_ANG) * CANELA_L
    - 0.010
)

IX = CONTACT_FOOT_X + 0.004
IY = CONTACT_FOOT_Y - 0.035

TX = 0.58
TY = CHAO_Y + 0.21

NX, NY = -0.50, 0.72
SX, SY = 0.62, 0.74

R_CIL = rx(PI / 2.0)

# ============================================================================
# Main loop
# ============================================================================

glfw.show_window(window)
glEnable(GL_DEPTH_TEST)

while not glfw.window_should_close(window):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glClearColor(0.53, 0.81, 0.98, 1.0)

    if wireframe:
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    else:
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    # Movimento principal da pisada
    gy = GY_BASE
    coxa_ang = 0.35 * (1.0 - t_stomp) - 0.02
    canela_ang = -0.28 * (1.0 - t_stomp)
    press_drop = t_stomp * 0.035

    inter_sy = 1.0 - t_stomp * 0.55
    inter_sx = 1.0 + t_stomp * 0.25

    # ======================================================================
    # Campo
    # ======================================================================

    draw("campo", (0.18, 0.58, 0.18, 1.0), mt(0.0, CHAO_Y - 0.15))
    draw("campo_linha", (1.0, 1.0, 1.0, 1.0), mt(0.0, CHAO_Y - 0.15))
    draw("campo_linha_h", (1.0, 1.0, 1.0, 1.0), mt(0.0, CHAO_Y - 0.05))
    draw("campo_linha_h", (1.0, 1.0, 1.0, 1.0), mt(0.0, CHAO_Y - 0.25))
    draw("campo_circulo", (1.0, 1.0, 1.0, 1.0), mt(0.0, CHAO_Y - 0.15))

    # ======================================================================
    # Trave
    # ======================================================================

    rp = ry(0.25)
    draw_caixa("trave_poste", (0.94, 0.94, 0.94, 1.0), mm(mt(TX - 0.19, TY), rp))
    draw_caixa("trave_poste", (0.90, 0.90, 0.90, 1.0), mm(mt(TX + 0.19, TY), rp))
    draw_caixa("trave_barra", (0.88, 0.88, 0.88, 1.0), mm(mt(TX, TY + 0.21), rp))

    # ======================================================================
    # Inter
    # ======================================================================

    inter_dy = (1.0 - inter_sy) * 0.045
    m_i = mm(mt(IX, IY - inter_dy), ms(inter_sx, inter_sy, 1.0))
    m_i = mm(m_i, ry(0.3))
    draw("i_corpo", (0.82, 0.05, 0.05, 1.0), m_i)

    m_badge = mm(mt(IX, IY - inter_dy, 0.065), ms(inter_sx, inter_sy, 1.0))
    draw("i_badge_branco", (1.0, 1.0, 1.0, 1.0), m_badge)

    m_badge2 = mm(mt(IX, IY - inter_dy, 0.068), ms(inter_sx, inter_sy, 1.0))
    draw("i_badge_vermelho", (0.82, 0.05, 0.05, 1.0), m_badge2)

    # ======================================================================
    # Grêmio body + emblem
    # ======================================================================

    m_corpo = mm(mt(GX, gy), ry(0.3))
    draw("g_corpo", (0.0, 0.20, 0.55, 1.0), m_corpo)

    draw("g_emb_anel_preto", (0.05, 0.05, 0.05, 1.0), mt(GX, gy, 0.24))
    draw("g_emb_azul", (0.0, 0.30, 0.65, 1.0), mt(GX, gy, 0.245))
    draw("g_emb_branco", (1.0, 1.0, 1.0, 1.0), mt(GX, gy, 0.248))
    draw("g_emb_listra_v", (0.0, 0.30, 0.65, 1.0), mt(GX, gy, 0.250))
    draw("g_emb_listra_h", (0.05, 0.05, 0.05, 1.0), mt(GX, gy, 0.252))

    draw("g_estrela", (0.75, 0.65, 0.20, 1.0), mt(GX - 0.06, gy + 0.30, 0.0))
    draw("g_estrela", (0.65, 0.65, 0.70, 1.0), mt(GX, gy + 0.32, 0.0))
    draw("g_estrela", (1.0, 0.85, 0.0, 1.0), mt(GX + 0.06, gy + 0.30, 0.0))

    # ======================================================================
    # Perna direita (pisada) - longer upper leg, connected joints
    # ======================================================================

    q_dir_x = GX + Q_DX_DIR
    q_dir_y = gy + Q_DY - press_drop

    j_x = q_dir_x + math.sin(coxa_ang) * COXA_L_STOMP
    j_y = q_dir_y - math.cos(coxa_ang) * COXA_L_STOMP

    ank_x = j_x + math.sin(canela_ang) * CANELA_L
    ank_y = j_y - math.cos(canela_ang) * CANELA_L

    coxa_cx = (q_dir_x + j_x) / 2.0
    coxa_cy = (q_dir_y + j_y) / 2.0
    m_c = mm(mt(coxa_cx, coxa_cy), rz(coxa_ang))
    m_c = mm(m_c, R_CIL)
    draw("g_coxa_stomp", (0.05, 0.05, 0.05, 1.0), m_c)

    can_cx = (j_x + ank_x) / 2.0
    can_cy = (j_y + ank_y) / 2.0
    m_cn = mm(mt(can_cx, can_cy), rz(canela_ang))
    m_cn = mm(m_cn, R_CIL)
    draw("g_canela_stomp", (1.0, 1.0, 1.0, 1.0), m_cn)

    pe_x = ank_x
    pe_y = ank_y - 0.010
    m_pe = mm(mt(pe_x, pe_y), ms(1.9, 0.6, 1.0))
    m_pe = mm(m_pe, ry(0.3))
    draw("g_pe", (0.05, 0.05, 0.05, 1.0), m_pe)

    # ======================================================================
    # Perna esquerda (apoio)
    # ======================================================================

    q_esq_x = GX + Q_DX_ESQ
    q_esq_y = gy + Q_DY

    coxa_ap_ang = -0.18
    canela_ap_ang = 0.08

    j2_x = q_esq_x + math.sin(coxa_ap_ang) * COXA_L
    j2_y = q_esq_y - math.cos(coxa_ap_ang) * COXA_L

    ank2_x = j2_x + math.sin(canela_ap_ang) * CANELA_L
    ank2_y = j2_y - math.cos(canela_ap_ang) * CANELA_L

    coxa2_cx = (q_esq_x + j2_x) / 2.0
    coxa2_cy = (q_esq_y + j2_y) / 2.0
    m_c2 = mm(mt(coxa2_cx, coxa2_cy), rz(coxa_ap_ang))
    m_c2 = mm(m_c2, R_CIL)
    draw("g_coxa", (0.05, 0.05, 0.05, 1.0), m_c2)

    can2_cx = (j2_x + ank2_x) / 2.0
    can2_cy = (j2_y + ank2_y) / 2.0
    m_cn2 = mm(mt(can2_cx, can2_cy), rz(canela_ap_ang))
    m_cn2 = mm(m_cn2, R_CIL)
    draw("g_canela", (1.0, 1.0, 1.0, 1.0), m_cn2)

    pe_ap_x = ank2_x
    pe_ap_y = ank2_y - 0.010
    m_pe_ap = mm(mt(pe_ap_x, pe_ap_y), ms(1.6, 0.5, 1.0))
    m_pe_ap = mm(m_pe_ap, ry(0.3))
    draw("g_pe_ap", (0.05, 0.05, 0.05, 1.0), m_pe_ap)

    # ======================================================================
    # Braços
    # ======================================================================

    m_bd = mm(mt(GX + 0.23, gy + 0.06), rz(1.1))
    m_bd = mm(m_bd, R_CIL)
    draw("g_braco", (0.0, 0.15, 0.42, 1.0), m_bd)

    m_be = mm(mt(GX - 0.23, gy + 0.06), rz(-0.6))
    m_be = mm(m_be, R_CIL)
    draw("g_braco", (0.0, 0.15, 0.42, 1.0), m_be)

    # ======================================================================
    # Nuvem
    # ======================================================================

    draw("nuvem", (0.93, 0.93, 0.97, 1.0), mt(NX - 0.06 + t_nuvem_x, NY + t_nuvem_y))
    draw("nuvem_m", (0.95, 0.95, 0.99, 1.0), mt(NX + 0.05 + t_nuvem_x, NY + 0.03 + t_nuvem_y))
    draw("nuvem_p", (0.91, 0.91, 0.95, 1.0), mt(NX + 0.13 + t_nuvem_x, NY - 0.01 + t_nuvem_y))

    # ======================================================================
    # Sol
    # ======================================================================

    m_sol = mm(mt(SX, SY), ms(s_sol, s_sol))
    draw("sol", (1.0, 0.88, 0.0, 1.0), m_sol)
    draw("sol_raios", (1.0, 0.72, 0.0, 1.0), m_sol)

    glfw.swap_buffers(window)
    glfw.poll_events()

glfw.terminate()