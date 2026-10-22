import streamlit as st
import re
import os
import sqlite3
import shutil
import io
import base64
import textwrap
import pandas as pd
from datetime import datetime
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px

# -------------------------------------------------------------
# PALETA OFICIAL GOBERNACIÓN DE NARIÑO
# -------------------------------------------------------------
C_VERDE_PRIN = "#10A13B"
C_AMARILLO_PRIN = "#FFD500"
C_AZUL_CLARO = "#80BEFF"
C_AZUL_INST = "#0071AC"
C_OCRE = "#896633"
C_ROJO = "#DA1C24"

st.set_page_config(
    page_title="Observatorio de Seguridad - Actividades Desarrolladas",
    page_icon="🟢",
    layout="wide"
)

CARPETA_EVIDENCIAS = "evidencias"
CARPETA_ASSETS = "assets"
os.makedirs(CARPETA_EVIDENCIAS, exist_ok=True)
os.makedirs(CARPETA_ASSETS, exist_ok=True)

# -------------------------------------------------------------
# BASE DE DATOS Y TABLAS DE USUARIOS E INVITADOS
# -------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect("pines_observatorio.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # 1. Tabla de Actividades Desarrolladas
    c.execute("""
        CREATE TABLE IF NOT EXISTS pines (
            id_pin TEXT PRIMARY KEY,
            municipio TEXT,
            fecha TEXT,
            hora TEXT,
            lugar TEXT,
            comuna TEXT,
            meta TEXT,
            poblacion TEXT,
            actividad TEXT,
            resultados TEXT,
            objetivo TEXT,
            novedades TEXT,
            participantes TEXT,
            armas_blancas INTEGER DEFAULT 0,
            asistentes INTEGER DEFAULT 0,
            latitud REAL DEFAULT 1.2136,
            longitud REAL DEFAULT -77.2811,
            rutas_fotos TEXT,
            fecha_registro TEXT
        )
    """)
    # 2. Tabla de Usuarios Administradores Registrados
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            password TEXT,
            nombre_completo TEXT,
            rol TEXT DEFAULT 'Administrador'
        )
    """)
    # Insertar usuario admin inicial si no existe
    c.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios VALUES ('admin', 'admin123', 'Administrador Principal', 'Administrador')")

    # 3. Tabla de Auditoría / Registro de Invitados
    c.execute("""
        CREATE TABLE IF NOT EXISTS registro_invitados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            apellido TEXT,
            entidad TEXT,
            cargo TEXT,
            municipio_origen TEXT,
            contacto TEXT,
            fecha_ingreso TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------
# CATÁLOGO DE MUNICIPIOS DE NARIÑO
# -------------------------------------------------------------
MUNICIPIOS_NARINO = {
    "Pasto (Capital)": (1.2136, -77.2811), "Aldana": (0.8797, -77.7003),
    "Ancuya": (1.2608, -77.5303), "Arboleda (Berruecos)": (1.5033, -77.1408),
    "Barbacoas": (1.6719, -78.1397), "Belén": (1.5975, -77.0519),
    "Buesaco": (1.3853, -77.1558), "Chachagüí": (1.3606, -77.2842),
    "Colón (Génova)": (1.6369, -76.9744), "Consacá": (1.2094, -77.4633),
    "Contadero": (0.9108, -77.5622), "Córdoba": (0.8589, -77.5217),
    "Cuaspud (Carlosama)": (0.8767, -77.7289), "Cumbal": (0.9142, -77.7944),
    "Cumbitara": (1.6569, -77.5856), "El Charco": (2.4769, -78.1103),
    "El Peñol": (1.4644, -77.4475), "El Rosario": (1.7456, -77.3400),
    "El Tablón de Gómez": (1.4258, -77.0983), "El Tambo": (1.4172, -77.3967),
    "Francisco Pizarro (Salahonda)": (2.0628, -78.6578), "Funes": (1.0028, -77.5208),
    "Guachucal": (0.9639, -77.7303), "Guaitarilla": (1.1344, -77.5508),
    "Gualmatán": (0.9189, -77.5694), "Iles": (0.9856, -77.5244),
    "Imués": (1.0967, -77.5258), "Ipiales": (0.8242, -77.6389),
    "La Cruz": (1.6044, -76.9714), "La Florida": (1.3006, -77.4042),
    "La Llanada": (1.4489, -77.5861), "La Tola": (2.4044, -78.2197),
    "La Unión": (1.6033, -77.1317), "Leiva": (1.9350, -77.3183),
    "Linares": (1.3789, -77.5028), "Los Andes (Sotomayor)": (1.4880, -77.5250),
    "Magüí Payán": (1.7042, -78.1969), "Mallama (Piedrancha)": (1.1069, -77.8592),
    "Mosquera": (2.5111, -78.4528), "Nariño": (1.2981, -77.3619),
    "Olavaya Herrera (Bocas de Satinga)": (2.3392, -78.3267), "Ospina": (1.0578, -77.5697),
    "Policarpa": (1.7167, -77.4483), "Potosí": (0.8142, -77.5736),
    "Providencia": (1.2403, -77.6019), "Puerres": (0.8925, -77.5083),
    "Pupiales": (0.8711, -77.6439), "Ricaurte": (1.2139, -78.1561),
    "Roberto Payán (San José)": (1.6961, -78.2589), "Samaniego": (1.3389, -77.5956),
    "San Bernardo": (1.5281, -77.0436), "San Lorenzo": (1.5036, -77.2189),
    "San Pablo": (1.6742, -77.0147), "San Pedro de Cartago": (1.5606, -77.1206),
    "Sandoná": (1.2883, -77.4719), "Santa Bárbara (Iscuandé)": (2.4489, -77.9819),
    "Santacruz (Guachavés)": (1.2975, -77.7289), "Sapuyes": (1.0333, -77.7167),
    "Taminango": (1.5878, -77.2750), "Tangua": (1.0967, -77.3958),
    "Tumaco": (1.7986, -78.8156), "Túquerres": (1.0872, -77.6186),
    "Yacuanquer": (1.1206, -77.3986)
}
TOTAL_MUNICIPIOS_NARINO = len(MUNICIPIOS_NARINO)
LISTA_MUNICIPIOS = sorted(list(MUNICIPIOS_NARINO.keys()))

# -------------------------------------------------------------
# FUNCIONES DE GESTIÓN Y PERSISTENCIA
# -------------------------------------------------------------
def guardar_actividad(datos: dict, fotos_subidas):
    rutas = []
    id_formateado = datos["id_pin"].strip()
    carpeta_actividad = os.path.join(CARPETA_EVIDENCIAS, id_formateado)

    if fotos_subidas:
        os.makedirs(carpeta_actividad, exist_ok=True)
        for foto in fotos_subidas:
            ruta_foto = os.path.join(carpeta_actividad, foto.name)
            with open(ruta_foto, "wb") as f:
                f.write(foto.getbuffer())
            rutas.append(ruta_foto)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO pines VALUES (
            :id_pin, :municipio, :fecha, :hora, :lugar, :comuna, :meta, :poblacion,
            :actividad, :resultados, :objetivo, :novedades, :participantes,
            :armas_blancas, :asistentes, :latitud, :longitud, :rutas_fotos, :fecha_registro
        )
    """, {
        **datos,
        "id_pin": id_formateado,
        "rutas_fotos": "; ".join(rutas),
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    conn.commit()
    conn.close()

def cargar_datos():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM pines ORDER BY id_pin ASC", conn)
    conn.close()
    return df

def generar_excel_estadisticas(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Actividades_General", index=False)
        res_mun = df.groupby("municipio").agg(
            Total_Actividades=("id_pin", "count"),
            Poblacion_Impactada=("asistentes", "sum"),
            Armas_Blancas=("armas_blancas", "sum")
        ).reset_index().sort_values(by="Total_Actividades", ascending=False)
        res_mun.to_excel(writer, sheet_name="Resumen_Municipios", index=False)
    return output.getvalue()

def cargar_imagen_b64(ruta_imagen: str) -> str:
    if os.path.exists(ruta_imagen):
        with open(ruta_imagen, "rb") as f:
            datos = base64.b64encode(f.read()).decode("utf-8")
            extension = os.path.splitext(ruta_imagen)[1].replace(".", "").lower()
            return f"data:image/{extension};base64,{datos}"
    return ""

def extraer_campo(patron: str, texto: str, multiline: bool = False) -> str:
    flags = re.IGNORECASE | (re.DOTALL if multiline else 0)
    regex = rf"(?:^|\n)[^\w\n]*{patron}\s*[:：\-]\s*(.*?)(?=\n[^\w\n]*(?:META|FECHA|HORA|LUGAR|POBLACI|ACTIVIDAD|RESULTADOS|OBJETIVO|NOVEDADES|PARTICIPANTES|PIN|ACTIVIDAD)\b|\Z)"
    match = re.search(regex, texto, flags)
    return match.group(1).strip() if match else ""

def parsear_texto_actividad(raw_text: str) -> dict:
    if not raw_text.strip():
        return {}
    m_id = re.search(r"(?:PIN|ACTIVIDAD)\s*(?:INFORMATIVO)?\s*No?\.?\s*(\d+)", raw_text, re.I)
    fecha = extraer_campo(r"(?:FECHA|DIA)", raw_text)
    hora = extraer_campo(r"HORA", raw_text)
    lugar = extraer_campo(r"LUGAR", raw_text)
    meta = extraer_campo(r"(?:META|NO\s+DE\s+META)", raw_text)
    poblacion = extraer_campo(r"POBLACI[OÓ]N\s*(?:IMPACTADA)?", raw_text)
    actividad = extraer_campo(r"ACTIVIDAD", raw_text)
    resultados = extraer_campo(r"RESULTADOS?", raw_text, multiline=True)
    objetivo = extraer_campo(r"OBJETIVO", raw_text, multiline=True)
    novedades = extraer_campo(r"NOVEDADES?", raw_text)
    participantes = extraer_campo(r"PARTICIPANTES?", raw_text, multiline=True)

    municipio_detectado = "Pasto (Capital)"
    texto_l = raw_text.lower()
    for m in LISTA_MUNICIPIOS:
        n_base = re.sub(r"\s*\(.*?\)", "", m).strip().lower()
        if re.search(rf"\b{n_base}\b", texto_l):
            municipio_detectado = m
            break

    comuna_det = "Sin especificar"
    m_comuna = re.search(r"Comuna\s*(\d+)", raw_text, re.I)
    if m_comuna:
        comuna_det = f"Comuna {m_comuna.group(1)}"

    armas = 0
    m_armas = re.search(r"(\d+)\s*armas", raw_text, re.I)
    if m_armas:
        armas = int(m_armas.group(1))

    asistentes = 0
    m_asist = re.search(r"(\d[\d\.\,]*)\s*(?:aproximadamente|personas|habitantes|familias|asistentes)", poblacion, re.I)
    if m_asist:
        c_limpia = re.sub(r"[^\d]", "", m_asist.group(1))
        if c_limpia.isdigit():
            asistentes = int(c_limpia)

    return {
        "id": f"ACT_{m_id.group(1).zfill(3)}" if m_id else "",
        "municipio": municipio_detectado, "fecha": fecha, "hora": hora,
        "lugar": lugar, "comuna": comuna_det, "meta": meta if meta else "PISCC",
        "poblacion": poblacion, "actividad": actividad, "resultados": resultados,
        "objetivo": objetivo, "novedades": novedades if novedades else "NINGUNA",
        "participantes": participantes, "armas": armas, "asistentes": asistentes
    }

# -------------------------------------------------------------
# ESTILOS CSS GLOBALES
# -------------------------------------------------------------
st.markdown(f"""
<style>
    .main {{ background-color: #F8F9FA; }}
    .kpi-container {{
        background: #FFFFFF;
        border-radius: 8px;
        padding: 16px 18px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        border-top: 4px solid {C_VERDE_PRIN};
        border-left: 1px solid #E0E0E0;
        border-right: 1px solid #E0E0E0;
        border-bottom: 1px solid #E0E0E0;
    }}
    .kpi-title {{
        color: #555555;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .kpi-value {{
        color: {C_VERDE_PRIN};
        font-size: 26px;
        font-weight: 800;
        margin-top: 4px;
    }}
    .kpi-subtext {{
        color: #777777;
        font-size: 12px;
        margin-top: 2px;
    }}
    .progress-box {{
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 12px 18px;
        margin: 15px 0 20px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .badge-narino {{
        background-color: {C_AMARILLO_PRIN};
        color: #000000;
        font-weight: bold;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: #EAECEF;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        color: #333333;
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {C_VERDE_PRIN} !important;
        color: #FFFFFF !important;
    }}
    button[kind="primary"], .stButton>button {{
        background-color: {C_VERDE_PRIN} !important;
        color: #FFFFFF !important;
        font-weight: bold;
        border: none;
        border-radius: 6px;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background-color: #0C7A2C !important;
        color: {C_AMARILLO_PRIN} !important;
    }}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# GESTIÓN DE SESIÓN (LOGIN / INVITADO)
# -------------------------------------------------------------
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["rol"] = None
    st.session_state["nombre_usuario"] = ""

ruta_logo_sub = os.path.join(CARPETA_ASSETS, "logo_subsecretaria.png")
ruta_logo_obs = os.path.join(CARPETA_ASSETS, "logo_observatorio.png")
logo_sub_b64 = cargar_imagen_b64(ruta_logo_sub)
logo_obs_b64 = cargar_imagen_b64(ruta_logo_obs)

# Render del encabezado superior institucional
header_html = textwrap.dedent(f"""
<div style="display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 10px 0 15px 0; border-bottom: 4px solid {C_VERDE_PRIN}; margin-bottom: 20px;">
    <div style="flex: 1; display: flex; justify-content: flex-start; align-items: center;">
        {f'<img src="{logo_sub_b64}" style="height: 60px; width: auto; object-fit: contain;">' if logo_sub_b64 else '<span style="color:#888; font-size:12px;">logo_subsecretaria.png</span>'}
    </div>
    <div style="flex: 2; text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center;">
        <h2 style="color: {C_VERDE_PRIN}; margin: 0; padding: 0; font-size: 23px; font-weight: 800; letter-spacing: -0.5px; line-height: 1.2;">
            Subsecretaría de Seguridad Ciudadana
        </h2>
        <div style="color: #555555; font-size: 13px; font-weight: 600; margin-top: 3px; line-height: 1.2;">
            Observatorio de Paz, Seguridad y Convivencia • Actividades Desarrolladas
        </div>
    </div>
    <div style="flex: 1; display: flex; justify-content: flex-end; align-items: center;">
        {f'<img src="{logo_obs_b64}" style="height: 60px; width: auto; object-fit: contain;">' if logo_obs_b64 else '<span style="color:#888; font-size:12px;">logo_observatorio.png</span>'}
    </div>
</div>
""")
st.markdown(header_html, unsafe_allow_html=True)

# =============================================================
# PANTALLA DE ACCESO (SI NO HA INICIADO SESIÓN)
# =============================================================
if not st.session_state["autenticado"]:
    st.markdown("<h3 style='text-align:center; color:#333333;'>Acceso al Sistema de Información</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#666666; font-size:14px;'>Selecciona la modalidad de ingreso según tu rol institucional</p>", unsafe_allow_html=True)

    col_vacia1, col_login, col_vacia2 = st.columns([1, 2.2, 1])

    with col_login:
        tab_login_user, tab_login_invitado = st.tabs(["🔐 Usuario Registrado (Administrador)", "👤 Ingreso como Invitado"])

        # 1. Ingreso de Administradores
        with tab_login_user:
            with st.form("form_auth"):
                st.markdown("##### Credenciales de Funcionario")
                user_input = st.text_input("Usuario")
                pass_input = st.text_input("Contraseña", type="password")
                btn_login = st.form_submit_button("Ingresar como Administrador", use_container_width=True)

                if btn_login:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM usuarios WHERE usuario = ? AND password = ?", (user_input.strip(), pass_input.strip()))
                    cuenta = c.fetchone()
                    conn.close()

                    if cuenta:
                        st.session_state["autenticado"] = True
                        st.session_state["rol"] = cuenta["rol"]
                        st.session_state["nombre_usuario"] = cuenta["nombre_completo"]
                        st.success(f"Bienvenido/a, {cuenta['nombre_completo']}.")
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas. Verifique usuario o contraseña.")

        # 2. Ingreso como Invitado
        with tab_login_invitado:
            with st.form("form_invitado"):
                st.markdown("##### Registro de Visita y Consulta")
                c_inv1, c_inv2 = st.columns(2)
                with c_inv1:
                    inv_nombre = st.text_input("Nombre(s) *")
                    inv_entidad = st.text_input("Entidad / Dependencia *")
                    inv_mpio = st.selectbox("Municipio de procedencia", LISTA_MUNICIPIOS)
                with c_inv2:
                    inv_apellido = st.text_input("Apellido(s) *")
                    inv_cargo = st.text_input("Cargo / Función *")
                    inv_contacto = st.text_input("Correo electrónico o celular")

                btn_invitado = st.form_submit_button("Ingresar al Tablero de Consulta", use_container_width=True)

                if btn_invitado:
                    if not inv_nombre.strip() or not inv_apellido.strip() or not inv_entidad.strip() or not inv_cargo.strip():
                        st.error("Por favor completa los campos obligatorios (*).")
                    else:
                        # Guardar en registro de invitados
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO registro_invitados (nombre, apellido, entidad, cargo, municipio_origen, contacto, fecha_ingreso)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            inv_nombre.strip(), inv_apellido.strip(), inv_entidad.strip(),
                            inv_cargo.strip(), inv_mpio, inv_contacto.strip(),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))
                        conn.commit()
                        conn.close()

                        st.session_state["autenticado"] = True
                        st.session_state["rol"] = "Invitado"
                        st.session_state["nombre_usuario"] = f"{inv_nombre.strip()} {inv_apellido.strip()} ({inv_entidad.strip()})"
                        st.success("Acceso concedido en modo Invitado.")
                        st.rerun()
    st.stop()

# =============================================================
# BARRA DE USUARIO ACTIVO Y CONTROL DE SESIÓN
# =============================================================
c_sesion1, c_sesion2 = st.columns([4, 1])
with c_sesion1:
    es_admin = (st.session_state["rol"] == "Administrador")
    badge_color = C_VERDE_PRIN if es_admin else C_AZUL_INST
    st.markdown(f"""
    <div style="font-size:13px; color:#444; margin-bottom:10px;">
        👤 Sesión iniciada como: <b>{st.session_state['nombre_usuario']}</b> | 
        <span style="background:{badge_color}; color:#FFF; padding:2px 8px; border-radius:10px; font-weight:bold; font-size:11px;">
            {st.session_state['rol']}
        </span>
    </div>
    """, unsafe_allow_html=True)
with c_sesion2:
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["rol"] = None
        st.session_state["nombre_usuario"] = ""
        st.rerun()

# =============================================================
# ENRUTAMIENTO DINÁMICO DE PESTAÑAS SEGÚN ROL
# =============================================================
if st.session_state["rol"] == "Administrador":
    # El Administrador cuenta con las 6 herramientas completas
    tab_dash, tab_mural, tab_nlp, tab_auto, tab_manual, tab_editar = st.tabs([
        "🗺️ Tablero y Mapa",
        "📷 Mural de Evidencias",
        "🔤 Analítica Textual",
        "⚡ Ingesta WhatsApp",
        "📝 Formulario Manual",
        "✏️ Gestión y Edición"
    ])
else:
    # El Invitado solo visualiza información (sin ingesta ni edición)
    tab_dash, tab_mural, tab_nlp = st.tabs([
        "🗺️ Tablero y Mapa",
        "📷 Mural de Evidencias",
        "🔤 Analítica Textual"
    ])

# =============================================================
# 1. TABLERO Y MAPA DEPARTAMENTAL
# =============================================================
with tab_dash:
    df_actividades = cargar_datos()

    if df_actividades.empty:
        st.info("Aún no hay actividades registradas en el sistema.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        total_act = len(df_actividades)
        mun_impactados = df_actividades["municipio"].nunique()
        total_asistentes = int(df_actividades["asistentes"].sum())
        total_armas = int(df_actividades["armas_blancas"].sum())

        with k1:
            st.markdown(f"""
            <div class="kpi-container" style="border-top-color:{C_VERDE_PRIN};">
                <div class="kpi-title">Actividades Registradas</div>
                <div class="kpi-value">{total_act}</div>
                <div class="kpi-subtext">Operativos y jornadas territoriales</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-container" style="border-top-color:{C_AMARILLO_PRIN};">
                <div class="kpi-title">Municipios Alcanzados</div>
                <div class="kpi-value" style="color:#B8860B;">{mun_impactados} <span style="font-size:16px; color:#666;">/ {TOTAL_MUNICIPIOS_NARINO}</span></div>
                <div class="kpi-subtext">Cobertura departamental</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-container" style="border-top-color:{C_AZUL_INST};">
                <div class="kpi-title">Población Impactada</div>
                <div class="kpi-value" style="color:{C_AZUL_INST};">{total_asistentes:,}</div>
                <div class="kpi-subtext">Ciudadanos beneficiados</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-container" style="border-top-color:{C_ROJO};">
                <div class="kpi-title">Armas Entregadas / Desarme</div>
                <div class="kpi-value" style="color:{C_ROJO};">{total_armas}</div>
                <div class="kpi-subtext">Armas cortopunzantes</div>
            </div>
            """, unsafe_allow_html=True)

        porcentaje_cobertura = (mun_impactados / TOTAL_MUNICIPIOS_NARINO) * 100
        st.markdown(f"""
        <div class="progress-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:600; color:#333333; font-size:14px;">Cobertura Territorial Departamental:</span>
                <span class="badge-narino">{mun_impactados} de {TOTAL_MUNICIPIOS_NARINO} Municipios ({porcentaje_cobertura:.1f}%)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(porcentaje_cobertura / 100.0)

        st.markdown("### 🗺️ Georreferenciación de Actividades en el Territorio")
        c_map1, c_map2 = st.columns([1, 2])
        with c_map1:
            capa_sel = st.radio("Capa en el mapa:", ["🔥 Mapa de Calor", "📍 Puntos por Municipio"], horizontal=True)
        with c_map2:
            peso_calor = st.selectbox("Ponderación del calor:", ["Cantidad de Actividades", "Población Impactada", "Armas Blancas"])

        m = folium.Map(location=[1.3500, -77.5000], zoom_start=9, tiles="OpenStreetMap")

        for idx, row in df_actividades.iterrows():
            if pd.isna(row["latitud"]) or pd.isna(row["longitud"]) or row["latitud"] == 0:
                coords = MUNICIPIOS_NARINO.get(row["municipio"], (1.2136, -77.2811))
                df_actividades.at[idx, "latitud"] = coords[0]
                df_actividades.at[idx, "longitud"] = coords[1]

        if capa_sel.startswith("🔥"):
            puntos_calor = []
            resumen_mun = df_actividades.groupby("municipio").agg({
                "id_pin": "count", "asistentes": "sum", "armas_blancas": "sum",
                "latitud": "first", "longitud": "first"
            }).reset_index()

            for _, r in resumen_mun.iterrows():
                lat = float(r["latitud"])
                lon = float(r["longitud"])
                if peso_calor.startswith("Población"):
                    peso = max(1.0, float(r["asistentes"]))
                elif peso_calor.startswith("Armas"):
                    peso = max(1.0, float(r["armas_blancas"]))
                else:
                    peso = float(r["id_pin"])
                puntos_calor.append([lat, lon, peso])
            HeatMap(puntos_calor, radius=32, blur=22, min_opacity=0.45).add_to(m)
        else:
            cluster = MarkerCluster().add_to(m)
            for _, r in df_actividades.iterrows():
                popup_html = f"""
                <div style='font-family:sans-serif; font-size:12px; width:220px;'>
                    <b style='color:{C_VERDE_PRIN};'>{r['id_pin']} - {r['municipio']}</b><br>
                    <b>Actividad:</b> {r['actividad']}<br>
                    <b>Lugar:</b> {r['lugar']}<br>
                    <b>Asistentes:</b> {r['asistentes']}
                </div>
                """
                folium.Marker(
                    location=[float(r["latitud"]), float(r["longitud"])],
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=f"{r['municipio']}: {r['id_pin']}",
                    icon=folium.Icon(color="green", icon="info-sign")
                ).add_to(cluster)

        st_folium(m, width="100%", height=480)
        
        st.markdown("---")
        c_d1, c_d2 = st.columns([1, 2])
        with c_d1:
            excel_data = generar_excel_estadisticas(df_actividades)
            st.download_button(
                label="📊 Descargar Actividades en Excel (.xlsx)",
                data=excel_data,
                file_name=f"Actividades_Observatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with c_d2:
            st.caption("Libro consolidado con la matriz completa y hoja de resumen por municipio, compatible con Google Sheets.")

# =============================================================
# 2. MURAL DE EVIDENCIAS FOTOGRÁFICAS
# =============================================================
with tab_mural:
    st.subheader("📷 Mural Interactivo de Evidencias Fotográficas - EN CONSTRUCCION")
    st.write("Registro visual de las intervenciones, jornadas y operativos en territorio.")

    df_fotos = cargar_datos()
    if df_fotos.empty:
        st.info("No hay datos disponibles.")
    else:
        muns_con_fotos = ["Todos los municipios"] + sorted(df_fotos["municipio"].unique().tolist())
        mun_seleccionado = st.selectbox("Filtrar evidencias por municipio:", muns_con_fotos)

        df_filtrado = df_fotos if mun_seleccionado == "Todos los municipios" else df_fotos[df_fotos["municipio"] == mun_seleccionado]

        galeria = []
        for _, fila in df_filtrado.iterrows():
            rutas_str = str(fila["rutas_fotos"]).strip()
            if rutas_str and rutas_str != "None":
                for r in [x.strip() for x in rutas_str.split(";") if x.strip()]:
                    if os.path.exists(r):
                        galeria.append({
                            "ruta": r,
                            "id": fila["id_pin"],
                            "municipio": fila["municipio"],
                            "actividad": fila["actividad"],
                            "fecha": fila["fecha"]
                        })

        if not galeria:
            st.warning(f"No hay fotografías vinculadas para {mun_seleccionado}.")
        else:
            st.caption(f"Mostrando {len(galeria)} fotografías registradas:")
            cols_galeria = st.columns(3)
            for idx, item in enumerate(galeria):
                with cols_galeria[idx % 3]:
                    st.image(item["ruta"], use_container_width=True)
                    st.markdown(f"**{item['id']}** ({item['municipio']})")
                    st.caption(f"📅 {item['fecha']} | {item['actividad'][:50]}...")
                    st.markdown("---")

# =============================================================
# 3. ANALÍTICA TEXTUAL
# =============================================================
with tab_nlp:
    st.subheader("🔤 Analítica Textual de Resultados y Objetivos")
    st.write("Frecuencia de términos clave y patrones narrativos en las actividades desarrolladas.")

    df_texto = cargar_datos()
    if df_texto.empty:
        st.info("Sin registros para procesar.")
    else:
        stopwords = {
            "de", "la", "el", "en", "y", "a", "los", "las", "del", "para", "por", "un", "una",
            "con", "se", "su", "al", "que", "lo", "como", "sus", "mas", "o", "no", "este",
            "esta", "entre", "sobre", "son", "fue", "ser", "mediante", "así", "parte", "cada",
            "este", "estos", "estas", "ninguna", "subsecretaría", "seguridad", "ciudadana",
            "desarrolló", "realizó", "sector", "municipio", "pasto", "nariño", "actividad"
        }

        todo_texto = " ".join(df_texto["resultados"].fillna("") + " " + df_texto["objetivo"].fillna(""))
        palabras = re.findall(r"\b[a-záéíóúñ]{4,}\b", todo_texto.lower())
        palabras_filtradas = [p for p in palabras if p not in stopwords]

        if palabras_filtradas:
            serie_palabras = pd.Series(palabras_filtradas).value_counts().head(20).reset_index()
            serie_palabras.columns = ["Término", "Frecuencia"]

            c_n1, c_n2 = st.columns([1.5, 1])
            with c_n1:
                st.markdown("#### Conceptos Clave Recurrentes")
                fig_barras = px.bar(
                    serie_palabras.head(12),
                    x="Frecuencia",
                    y="Término",
                    orientation="h",
                    color="Frecuencia",
                    color_continuous_scale=[C_AZUL_CLARO, C_VERDE_PRIN],
                    text="Frecuencia"
                )
                fig_barras.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, b=20, l=10, r=10))
                st.plotly_chart(fig_barras, use_container_width=True)

            with c_n2:
                st.markdown("#### Matriz de Términos Estratégicos")
                st.dataframe(serie_palabras, use_container_width=True, height=360)
        else:
            st.info("No se encontraron suficientes textos narrativos para procesar.")

# =============================================================
# SECCIONES EXCLUSIVAS PARA ADMINISTRADORES
# =============================================================
if st.session_state["rol"] == "Administrador":

    # 4. INGESTA WHATSAPP
    with tab_auto:
        st.subheader("⚡ Ingesta Rápida (Copia y pega desde WhatsApp)")
        raw_text = st.text_area("Pega el texto del reporte de actividad aquí:", height=150, key="txt_auto")
        parsed = parsear_texto_actividad(raw_text)

        with st.form("form_auto"):
            c1, c2, c3 = st.columns(3)
            with c1:
                id_a = st.text_input("Código / Identificador (ej. ACT_001)", value=parsed.get("id", ""))
                idx_m = LISTA_MUNICIPIOS.index(parsed["municipio"]) if parsed.get("municipio") in LISTA_MUNICIPIOS else LISTA_MUNICIPIOS.index("Pasto (Capital)")
                municipio_a = st.selectbox("Municipio de Nariño", LISTA_MUNICIPIOS, index=idx_m, key="mun_a")
                fecha_a = st.text_input("Fecha", value=parsed.get("fecha", ""))
                hora_a = st.text_input("Hora", value=parsed.get("hora", ""))
            with c2:
                opc_com = ["Sin especificar"] + [f"Comuna {i}" for i in range(1, 13)] + ["Corregimiento"]
                idx_c = opc_com.index(parsed["comuna"]) if parsed.get("comuna") in opc_com else 0
                comuna_a = st.selectbox("Comuna / Corregimiento", opc_com, index=idx_c, key="com_a")
                lugar_a = st.text_input("Lugar / Sector específico", value=parsed.get("lugar", ""))
                meta_a = st.text_input("Meta / Línea Estratégica", value=parsed.get("meta", "PISCC"))
            with c3:
                armas_a = st.number_input("Armas cortopunzantes", min_value=0, step=1, value=parsed.get("armas", 0), key="arm_a")
                asistentes_a = st.number_input("Población aproximada impactada", min_value=0, step=10, value=parsed.get("asistentes", 0), key="asis_a")
                poblacion_txt_a = st.text_input("Descripción Población", value=parsed.get("poblacion", ""))

            actividad_a = st.text_input("Nombre de la Actividad", value=parsed.get("actividad", ""))
            objetivo_a = st.text_area("Objetivo", value=parsed.get("objetivo", ""), height=75)
            resultados_a = st.text_area("Resultados", value=parsed.get("resultados", ""), height=90)
            novedades_a = st.text_input("Novedades", value=parsed.get("novedades", "NINGUNA"))
            participantes_a = st.text_area("Participantes", value=parsed.get("participantes", ""), height=75)

            fotos_a = st.file_uploader("Evidencias fotográficas", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="fotos_a")

            if st.form_submit_button("💾 Guardar Actividad Desarrollada"):
                if not id_a:
                    st.error("Ingresa el código o identificador de la actividad.")
                else:
                    lat_m, lon_m = MUNICIPIOS_NARINO[municipio_a]
                    data = {
                        "id_pin": id_a, "municipio": municipio_a, "fecha": fecha_a, "hora": hora_a,
                        "lugar": lugar_a, "comuna": comuna_a, "meta": meta_a, "poblacion": poblacion_txt_a,
                        "actividad": actividad_a, "resultados": resultados_a, "objetivo": objetivo_a,
                        "novedades": novedades_a, "participantes": participantes_a,
                        "armas_blancas": armas_a, "asistentes": asistentes_a,
                        "latitud": lat_m, "longitud": lon_m
                    }
                    guardar_actividad(data, fotos_a)
                    st.success(f"✅ Actividad {id_a} guardada correctamente.")
                    st.rerun()

    # 5. FORMULARIO MANUAL
    with tab_manual:
        st.subheader("📝 Diligenciamiento Manual de Actividad")
        with st.form("form_manual"):
            col1, col2, col3 = st.columns(3)
            with col1:
                id_m = st.text_input("Código / Identificador (ej. ACT_030)")
                municipio_m = st.selectbox("Municipio de Nariño", LISTA_MUNICIPIOS, index=LISTA_MUNICIPIOS.index("Pasto (Capital)"), key="mun_m")
                fecha_m = st.date_input("Fecha").strftime("%d/%m/%Y")
                hora_m = st.text_input("Hora (ej. 09:00 am)")
            with col2:
                comuna_m = st.selectbox("Comuna / Corregimiento", ["Sin especificar"] + [f"Comuna {i}" for i in range(1, 13)] + ["Corregimiento"], key="com_m")
                lugar_m = st.text_input("Lugar / Barrio")
                meta_m = st.selectbox("Línea PISCC / Componente", ["PISCC", "Meta 11 - Observatorio", "Meta 13 - Prevención", "Meta 17 - Cultivos", "Acción Unificada"])
            with col3:
                armas_m = st.number_input("Armas cortopunzantes", min_value=0, step=1, value=0, key="arm_m")
                asistentes_m = st.number_input("Población aproximada impactada", min_value=0, step=10, value=0, key="asis_m")
                poblacion_txt_m = st.text_input("Descripción Población")

            actividad_m = st.text_input("Nombre de la Actividad")
            objetivo_m = st.text_area("Objetivo", height=75)
            resultados_m = st.text_area("Resultados obtenidos", height=90)
            novedades_m = st.text_input("Novedades", value="NINGUNA")
            participantes_m = st.text_area("Entidades y Participantes", height=75)

            fotos_m = st.file_uploader("Evidencias fotográficas", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="fotos_m")

            if st.form_submit_button("💾 Guardar Actividad"):
                if not id_m:
                    st.error("Debes ingresar el identificador de la actividad.")
                else:
                    lat_m, lon_m = MUNICIPIOS_NARINO[municipio_m]
                    data = {
                        "id_pin": id_m, "municipio": municipio_m, "fecha": fecha_m, "hora": hora_m,
                        "lugar": lugar_m, "comuna": comuna_m, "meta": meta_m, "poblacion": poblacion_txt_m,
                        "actividad": actividad_m, "resultados": resultados_m, "objetivo": objetivo_m,
                        "novedades": novedades_m, "participantes": participantes_m,
                        "armas_blancas": armas_m, "asistentes": asistentes_m,
                        "latitud": lat_m, "longitud": lon_m
                    }
                    guardar_actividad(data, fotos_m)
                    st.success(f"✅ Actividad {id_m} guardada con éxito.")
                    st.rerun()

    # 6. GESTIÓN Y EDICIÓN
    with tab_editar:
        st.subheader("✏️ Gestión, Edición y Auditoría de Actividades")
        df_edit = cargar_datos()

        if df_edit.empty:
            st.info("No hay actividades para editar.")
        else:
            act_seleccionada = st.selectbox("Selecciona la actividad a modificar:", df_edit["id_pin"].tolist(), key="p_edit")
            registro_actual = df_edit[df_edit["id_pin"] == act_seleccionada].iloc[0]

            with st.form("form_edicion"):
                st.markdown(f"#### Editando registro: **{act_seleccionada}**")
                c_id1, c_id2 = st.columns([1, 2])
                with c_id1:
                    nuevo_id = st.text_input("Identificador (Código)", value=registro_actual["id_pin"])
                with c_id2:
                    idx_m_act = LISTA_MUNICIPIOS.index(registro_actual["municipio"]) if registro_actual["municipio"] in LISTA_MUNICIPIOS else LISTA_MUNICIPIOS.index("Pasto (Capital)")
                    nuevo_municipio = st.selectbox("Municipio de Nariño", LISTA_MUNICIPIOS, index=idx_m_act)

                e1, e2, e3 = st.columns(3)
                with e1:
                    nueva_fecha = st.text_input("Fecha", value=registro_actual["fecha"])
                    nueva_hora = st.text_input("Hora", value=registro_actual["hora"])
                with e2:
                    opc_c = ["Sin especificar"] + [f"Comuna {i}" for i in range(1, 13)] + ["Corregimiento"]
                    idx_c_act = opc_c.index(registro_actual["comuna"]) if registro_actual["comuna"] in opc_c else 0
                    nueva_comuna = st.selectbox("Comuna / Corregimiento", opc_c, index=idx_c_act)
                    nuevo_lugar = st.text_input("Lugar / Sector", value=registro_actual["lugar"])
                with e3:
                    nueva_meta = st.text_input("Meta / Línea", value=registro_actual["meta"])
                    nuevas_armas = st.number_input("Armas cortopunzantes", min_value=0, step=1, value=int(registro_actual["armas_blancas"]))
                    nuevos_asistentes = st.number_input("Población impactada", min_value=0, step=10, value=int(registro_actual["asistentes"]))

                nueva_poblacion = st.text_input("Descripción Población", value=registro_actual["poblacion"])
                nueva_actividad = st.text_input("Nombre de la Actividad", value=registro_actual["actividad"])
                nuevos_resultados = st.text_area("Resultados", value=registro_actual["resultados"], height=90)
                nuevo_objetivo = st.text_area("Objetivo", value=registro_actual["objetivo"], height=80)
                nuevas_novedades = st.text_input("Novedades", value=registro_actual["novedades"])
                nuevos_participantes = st.text_area("Participantes", value=registro_actual["participantes"], height=80)

                st.markdown("##### 📷 Evidencias Fotográficas Actuales")
                rutas_actuales_str = str(registro_actual["rutas_fotos"]).strip()
                if rutas_actuales_str and rutas_actuales_str != "None" and rutas_actuales_str != "":
                    fotos_existentes = [r.strip() for r in rutas_actuales_str.split(";") if r.strip()]
                    cols_img = st.columns(min(len(fotos_existentes), 4))
                    for idx_f, r_foto in enumerate(fotos_existentes):
                        with cols_img[idx_f % 4]:
                            if os.path.exists(r_foto):
                                st.image(r_foto, caption=os.path.basename(r_foto), use_container_width=True)
                            else:
                                st.caption(f"No ubicada: {os.path.basename(r_foto)}")
                else:
                    st.caption("No tiene fotos vinculadas.")

                #nuevas_fotos = st.file_uploader("Adjuntar nuevas fotografías:", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="up_edit")

                if st.form_submit_button("💾 Guardar Cambios"):
                    nuevo_id = nuevo_id.strip()
                    id_ant = registro_actual["id_pin"]
                    conn = get_db_connection()
                    c = conn.cursor()

                    if nuevo_id != id_ant:
                        c.execute("SELECT id_pin FROM pines WHERE id_pin = ?", (nuevo_id,))
                        if c.fetchone():
                            st.error(f"El identificador '{nuevo_id}' ya existe.")
                            conn.close()
                            st.stop()

                    carp_vieja = os.path.join(CARPETA_EVIDENCIAS, id_ant)
                    carp_nueva = os.path.join(CARPETA_EVIDENCIAS, nuevo_id)
                    if nuevo_id != id_ant and os.path.exists(carp_vieja) and not os.path.exists(carp_nueva):
                        os.rename(carp_vieja, carp_nueva)

                    fotos_finales = []
                    if rutas_actuales_str and rutas_actuales_str != "None":
                        for rf in [r.strip() for r in rutas_actuales_str.split(";") if r.strip()]:
                            rf_upd = rf.replace(f"\\{id_ant}\\", f"\\{nuevo_id}\\").replace(f"/{id_ant}/", f"/{nuevo_id}/")
                            fotos_finales.append(rf_upd)

                    if nuevas_fotos:
                        os.makedirs(carp_nueva, exist_ok=True)
                        for foto in nuevas_fotos:
                            ruta_nueva = os.path.join(carp_nueva, foto.name)
                            with open(ruta_nueva, "wb") as f:
                                f.write(foto.getbuffer())
                            if ruta_nueva not in fotos_finales:
                                fotos_finales.append(ruta_nueva)

                    lat_m, lon_m = MUNICIPIOS_NARINO.get(nuevo_municipio, (1.2136, -77.2811))

                    if nuevo_id != id_ant:
                        c.execute("DELETE FROM pines WHERE id_pin = ?", (id_ant,))

                    c.execute("""
                        INSERT OR REPLACE INTO pines VALUES (
                            :id_pin, :municipio, :fecha, :hora, :lugar, :comuna, :meta, :poblacion,
                            :actividad, :resultados, :objetivo, :novedades, :participantes,
                            :armas_blancas, :asistentes, :latitud, :longitud, :rutas_fotos, :fecha_registro
                        )
                    """, {
                        "id_pin": nuevo_id, "municipio": nuevo_municipio, "fecha": nueva_fecha,
                        "hora": nueva_hora, "lugar": nuevo_lugar, "comuna": nueva_comuna,
                        "meta": nueva_meta, "poblacion": nueva_poblacion, "actividad": nueva_actividad,
                        "resultados": nuevos_resultados, "objetivo": nuevo_objetivo,
                        "novedades": nuevas_novedades, "participantes": nuevos_participantes,
                        "armas_blancas": nuevas_armas, "asistentes": nuevos_asistentes,
                        "latitud": lat_m, "longitud": lon_m,
                        "rutas_fotos": "; ".join(fotos_finales),
                        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Actividad '{nuevo_id}' actualizada.")
                    st.rerun()

            st.markdown("---")
            with st.expander("🗑️ Zona de Riesgo: Eliminar Actividad"):
                if st.button(f"Confirmar eliminación definitiva de {act_seleccionada}", type="primary"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM pines WHERE id_pin = ?", (act_seleccionada,))
                    conn.commit()
                    conn.close()
                    carp_del = os.path.join(CARPETA_EVIDENCIAS, act_seleccionada)
                    if os.path.exists(carp_del):
                        shutil.rmtree(carp_del)
                    st.success(f"Actividad {act_seleccionada} eliminada.")
                    st.rerun()