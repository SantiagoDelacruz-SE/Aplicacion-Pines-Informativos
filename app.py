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
    page_title="Observatorio de Seguridad - Gobernación de Nariño",
    page_icon="🟢",
    layout="wide"
)

CARPETA_EVIDENCIAS = "evidencias"
CARPETA_ASSETS = "assets"
os.makedirs(CARPETA_EVIDENCIAS, exist_ok=True)
os.makedirs(CARPETA_ASSETS, exist_ok=True)

# -------------------------------------------------------------
# ESTILOS CSS INSTITUCIONALES
# -------------------------------------------------------------
st.markdown(f"""
<style>
    .main {{
        background-color: #F8F9FA;
    }}
    .header-bar {{
        border-bottom: 4px solid {C_VERDE_PRIN};
        padding-bottom: 12px;
        margin-bottom: 20px;
    }}
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
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
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
# ENCABEZADO INSTITUCIONAL CON BASE64 Y TEXTWRAP
# -------------------------------------------------------------
def cargar_imagen_b64(ruta_imagen: str) -> str:
    if os.path.exists(ruta_imagen):
        with open(ruta_imagen, "rb") as f:
            datos = base64.b64encode(f.read()).decode("utf-8")
            extension = os.path.splitext(ruta_imagen)[1].replace(".", "").lower()
            return f"data:image/{extension};base64,{datos}"
    return ""

ruta_logo_sub = os.path.join(CARPETA_ASSETS, "logo_subsecretaria.png")
ruta_logo_obs = os.path.join(CARPETA_ASSETS, "logo_observatorio.png")

logo_sub_b64 = cargar_imagen_b64(ruta_logo_sub)
logo_obs_b64 = cargar_imagen_b64(ruta_logo_obs)

header_html = textwrap.dedent(f"""
<div style="display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 10px 0 20px 0; border-bottom: 4px solid {C_VERDE_PRIN}; margin-bottom: 25px;">
    <div style="flex: 1; display: flex; justify-content: flex-start; align-items: center;">
        {f'<img src="{logo_sub_b64}" style="height: 65px; width: auto; object-fit: contain;">' if logo_sub_b64 else '<span style="color:#888; font-size:12px;">logo_subsecretaria.png</span>'}
    </div>
    <div style="flex: 2; text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center;">
        <h2 style="color: {C_VERDE_PRIN}; margin: 0; padding: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; line-height: 1.2;">
            Subsecretaría de Seguridad Ciudadana
        </h2>
        <div style="color: #555555; font-size: 14px; font-weight: 600; margin-top: 4px; line-height: 1.2;">
            Sistema de Monitoreo y Analítica de Pines Informativos
        </div>
    </div>
    <div style="flex: 1; display: flex; justify-content: flex-end; align-items: center;">
        {f'<img src="{logo_obs_b64}" style="height: 65px; width: auto; object-fit: contain;">' if logo_obs_b64 else '<span style="color:#888; font-size:12px;">logo_observatorio.png</span>'}
    </div>
</div>
""")

st.markdown(header_html, unsafe_allow_html=True)

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
# BASE DE DATOS
# -------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect("pines_observatorio.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
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
    conn.commit()
    conn.close()

init_db()

def guardar_pin(datos: dict, fotos_subidas):
    rutas = []
    pin_id_formateado = datos["id_pin"].strip()
    carpeta_pin = os.path.join(CARPETA_EVIDENCIAS, pin_id_formateado)

    if fotos_subidas:
        os.makedirs(carpeta_pin, exist_ok=True)
        for foto in fotos_subidas:
            ruta_foto = os.path.join(carpeta_pin, foto.name)
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
        "id_pin": pin_id_formateado,
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
        df.to_excel(writer, sheet_name="Matriz_Pines_General", index=False)
        res_mun = df.groupby("municipio").agg(
            Total_Pines=("id_pin", "count"),
            Poblacion_Impactada=("asistentes", "sum"),
            Armas_Blancas=("armas_blancas", "sum")
        ).reset_index().sort_values(by="Total_Pines", ascending=False)
        res_mun.to_excel(writer, sheet_name="Resumen_Municipios", index=False)
    return output.getvalue()

# -------------------------------------------------------------
# PARSER DE WHATSAPP
# -------------------------------------------------------------
def extraer_campo(patron: str, texto: str, multiline: bool = False) -> str:
    flags = re.IGNORECASE | (re.DOTALL if multiline else 0)
    regex = rf"(?:^|\n)[^\w\n]*{patron}\s*[:：\-]\s*(.*?)(?=\n[^\w\n]*(?:META|FECHA|HORA|LUGAR|POBLACI|ACTIVIDAD|RESULTADOS|OBJETIVO|NOVEDADES|PARTICIPANTES|PIN)\b|\Z)"
    match = re.search(regex, texto, flags)
    return match.group(1).strip() if match else ""

def parsear_texto_pin(raw_text: str) -> dict:
    if not raw_text.strip():
        return {}
    m_id = re.search(r"PIN\s*(?:INFORMATIVO)?\s*No?\.?\s*(\d+)", raw_text, re.I)
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
        "id": f"PIN_{m_id.group(1).zfill(3)}" if m_id else "",
        "municipio": municipio_detectado, "fecha": fecha, "hora": hora,
        "lugar": lugar, "comuna": comuna_det, "meta": meta if meta else "PISCC",
        "poblacion": poblacion, "actividad": actividad, "resultados": resultados,
        "objetivo": objetivo, "novedades": novedades if novedades else "NINGUNA",
        "participantes": participantes, "armas": armas, "asistentes": asistentes
    }

# -------------------------------------------------------------
# PESTAÑAS DE LA APLICACIÓN
# -------------------------------------------------------------
tab_dash, tab_mural, tab_nlp, tab_auto, tab_manual, tab_editar = st.tabs([
    "🗺️ Tablero y Mapa",
    "📷 Mural de Evidencias (Pto 5)",
    "🔤 Analítica Textual (Pto 6)",
    "⚡ Ingesta WhatsApp",
    "📝 Formulario Manual",
    "✏️ Gestión y Edición"
])

# =============================================================
# 1. TABLERO PRINCIPAL CON MAPA Y PUNTO 7
# =============================================================
with tab_dash:
    df_pines = cargar_datos()

    if df_pines.empty:
        st.info("Aún no hay pines cargados en el sistema.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        total_pines = len(df_pines)
        mun_impactados = df_pines["municipio"].nunique()
        total_asistentes = int(df_pines["asistentes"].sum())
        total_armas = int(df_pines["armas_blancas"].sum())

        with k1:
            st.markdown(f"""
            <div class="kpi-container" style="border-top-color:{C_VERDE_PRIN};">
                <div class="kpi-title">Pines Registrados</div>
                <div class="kpi-value">{total_pines}</div>
                <div class="kpi-subtext">Actividades reportadas</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-container" style="border-top-color:{C_AMARILLO_PRIN};">
                <div class="kpi-title">Municipios Alcanzados</div>
                <div class="kpi-value" style="color:#B8860B;">{mun_impactados} <span style="font-size:16px; color:#666;">/ {TOTAL_MUNICIPIOS_NARINO}</span></div>
                <div class="kpi-subtext">Presencia territorial</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-container" style="border-top-color:{C_AZUL_INST};">
                <div class="kpi-title">Población Impactada</div>
                <div class="kpi-value" style="color:{C_AZUL_INST};">{total_asistentes:,}</div>
                <div class="kpi-subtext">Ciudadanos alcanzados</div>
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

        st.markdown("### 🗺️ Georreferenciación Departamental de Actividades")
        c_map1, c_map2 = st.columns([1, 2])
        with c_map1:
            capa_sel = st.radio("Capa en el mapa:", ["🔥 Mapa de Calor", "📍 Puntos por Municipio"], horizontal=True)
        with c_map2:
            peso_calor = st.selectbox("Ponderación del calor:", ["Cantidad de Pines", "Población Impactada", "Armas Blancas"])

        m = folium.Map(location=[1.3500, -77.5000], zoom_start=9, tiles="OpenStreetMap")

        for idx, row in df_pines.iterrows():
            if pd.isna(row["latitud"]) or pd.isna(row["longitud"]) or row["latitud"] == 0:
                coords = MUNICIPIOS_NARINO.get(row["municipio"], (1.2136, -77.2811))
                df_pines.at[idx, "latitud"] = coords[0]
                df_pines.at[idx, "longitud"] = coords[1]

        if capa_sel.startswith("🔥"):
            puntos_calor = []
            resumen_mun = df_pines.groupby("municipio").agg({
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
            for _, r in df_pines.iterrows():
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
            excel_data = generar_excel_estadisticas(df_pines)
            st.download_button(
                label="📊 Descargar Todo en Excel (.xlsx)",
                data=excel_data,
                file_name=f"Estadisticas_Pines_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with c_d2:
            st.caption("Libro con la matriz consolidada y las hojas de resumen, formateado para Google Sheets.")

# =============================================================
# PUNTO 5: MURAL DE EVIDENCIAS FOTOGRÁFICAS
# =============================================================
with tab_mural:
    st.subheader("📷 Mural Interactivo de Evidencias Fotográficas")
    st.write("Explorador fotográfico de las actividades y operativos desarrollados en el territorio.")

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
                            "pin": fila["id_pin"],
                            "municipio": fila["municipio"],
                            "actividad": fila["actividad"],
                            "fecha": fila["fecha"]
                        })

        if not galeria:
            st.warning(f"No hay fotografías adjuntas registradas para {mun_seleccionado}. Puedes adjuntarlas en la pestaña '✏️ Gestión y Edición'.")
        else:
            st.caption(f"Mostrando {len(galeria)} fotografías registradas:")
            cols_galeria = st.columns(3)
            for idx, item in enumerate(galeria):
                with cols_galeria[idx % 3]:
                    st.image(item["ruta"], use_container_width=True)
                    st.markdown(f"**{item['pin']}** ({item['municipio']})")
                    st.caption(f"📅 {item['fecha']} | {item['actividad'][:50]}...")
                    st.markdown("---")

# =============================================================
# PUNTO 6: ANALÍTICA TEXTUAL Y TÉRMINOS CLAVE
# =============================================================
with tab_nlp:
    st.subheader("🔤 Analítica Textual de Resultados y Objetivos")
    st.write("Detección de patrones y términos recurrentes en las narrativas operativas y comunitarias del PISCC.")

    df_texto = cargar_datos()
    if df_texto.empty:
        st.info("Sin registros para procesar.")
    else:
        stopwords = {
            "de", "la", "el", "en", "y", "a", "los", "las", "del", "para", "por", "un", "una",
            "con", "se", "su", "al", "que", "lo", "como", "sus", "mas", "o", "no", "este",
            "esta", "entre", "sobre", "son", "fue", "ser", "mediante", "así", "parte", "cada",
            "este", "estos", "estas", "ninguna", "subsecretaría", "seguridad", "ciudadana",
            "desarrolló", "realizó", "sector", "municipio", "pasto", "nariño"
        }

        todo_texto = " ".join(df_texto["resultados"].fillna("") + " " + df_texto["objetivo"].fillna(""))
        palabras = re.findall(r"\b[a-záéíóúñ]{4,}\b", todo_texto.lower())
        palabras_filtradas = [p for p in palabras if p not in stopwords]

        if palabras_filtradas:
            serie_palabras = pd.Series(palabras_filtradas).value_counts().head(20).reset_index()
            serie_palabras.columns = ["Término", "Frecuencia"]

            c_n1, c_n2 = st.columns([1.5, 1])
            with c_n1:
                st.markdown("#### Frecuencia de Conceptos Operativos Clave")
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
# INGESTA WHATSAPP
# =============================================================
with tab_auto:
    st.subheader("⚡ Ingesta Rápida (WhatsApp)")
    raw_text = st.text_area("Pega el texto del Pin aquí:", height=150, key="txt_auto")
    parsed = parsear_texto_pin(raw_text)

    with st.form("form_auto"):
        c1, c2, c3 = st.columns(3)
        with c1:
            pin_id_a = st.text_input("Identificador del Pin", value=parsed.get("id", ""))
            idx_m = LISTA_MUNICIPIOS.index(parsed["municipio"]) if parsed.get(
                "municipio") in LISTA_MUNICIPIOS else LISTA_MUNICIPIOS.index("Pasto (Capital)")
            municipio_a = st.selectbox("Municipio de Nariño", LISTA_MUNICIPIOS, index=idx_m, key="mun_a")
            fecha_a = st.text_input("Fecha", value=parsed.get("fecha", ""))
            hora_a = st.text_input("Hora", value=parsed.get("hora", ""))
        with c2:
            opc_com = ["Sin especificar"] + [f"Comuna {i}" for i in range(1, 13)] + ["Corregimiento"]
            idx_c = opc_com.index(parsed["comuna"]) if parsed.get("comuna") in opc_com else 0
            comuna_a = st.selectbox("Comuna / Corregimiento", opc_com, index=idx_c, key="com_a")
            lugar_a = st.text_input("Lugar / Sector", value=parsed.get("lugar", ""))
            meta_a = st.text_input("Meta / Línea Estratégica", value=parsed.get("meta", "PISCC"))
        with c3:
            armas_a = st.number_input("Armas cortopunzantes", min_value=0, step=1, value=parsed.get("armas", 0), key="arm_a")
            asistentes_a = st.number_input("Población aproximada impactada", min_value=0, step=10, value=parsed.get("asistentes", 0), key="asis_a")
            poblacion_txt_a = st.text_input("Descripción Población", value=parsed.get("poblacion", ""))

        actividad_a = st.text_input("Actividad", value=parsed.get("actividad", ""))
        objetivo_a = st.text_area("Objetivo", value=parsed.get("objetivo", ""), height=75)
        resultados_a = st.text_area("Resultados", value=parsed.get("resultados", ""), height=90)
        novedades_a = st.text_input("Novedades", value=parsed.get("novedades", "NINGUNA"))
        participantes_a = st.text_area("Participantes", value=parsed.get("participantes", ""), height=75)

        fotos_a = st.file_uploader("Evidencias fotográficas", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="fotos_a")

        if st.form_submit_button("💾 Guardar Pin"):
            if not pin_id_a:
                st.error("Ingresa el número de Pin.")
            else:
                lat_m, lon_m = MUNICIPIOS_NARINO[municipio_a]
                data = {
                    "id_pin": pin_id_a, "municipio": municipio_a, "fecha": fecha_a, "hora": hora_a,
                    "lugar": lugar_a, "comuna": comuna_a, "meta": meta_a, "poblacion": poblacion_txt_a,
                    "actividad": actividad_a, "resultados": resultados_a, "objetivo": objetivo_a,
                    "novedades": novedades_a, "participantes": participantes_a,
                    "armas_blancas": armas_a, "asistentes": asistentes_a,
                    "latitud": lat_m, "longitud": lon_m
                }
                guardar_pin(data, fotos_a)
                st.success(f"✅ {pin_id_a} guardado correctamente.")
                st.rerun()

# =============================================================
# FORMULARIO MANUAL
# =============================================================
with tab_manual:
    st.subheader("📝 Diligenciamiento Manual")
    with st.form("form_manual"):
        col1, col2, col3 = st.columns(3)
        with col1:
            pin_id_m = st.text_input("Identificador de Pin (ej. PIN_029)")
            municipio_m = st.selectbox("Municipio de Nariño", LISTA_MUNICIPIOS,
                                       index=LISTA_MUNICIPIOS.index("Pasto (Capital)"), key="mun_m")
            fecha_m = st.date_input("Fecha").strftime("%d/%m/%Y")
            hora_m = st.text_input("Hora (ej. 09:00 am)")
        with col2:
            comuna_m = st.selectbox("Comuna / Corregimiento",
                                    ["Sin especificar"] + [f"Comuna {i}" for i in range(1, 13)] + ["Corregimiento"],
                                    key="com_m")
            lugar_m = st.text_input("Lugar / Barrio")
            meta_m = st.selectbox("Línea PISCC",
                                  ["PISCC", "Meta 11 - Observatorio", "Meta 13 - Prevención", "Meta 17 - Cultivos",
                                   "Acción Unificada"])
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

        if st.form_submit_button("💾 Guardar Pin Manual"):
            if not pin_id_m:
                st.error("Debes ingresar el identificador del Pin.")
            else:
                lat_m, lon_m = MUNICIPIOS_NARINO[municipio_m]
                data = {
                    "id_pin": pin_id_m, "municipio": municipio_m, "fecha": fecha_m, "hora": hora_m,
                    "lugar": lugar_m, "comuna": comuna_m, "meta": meta_m, "poblacion": poblacion_txt_m,
                    "actividad": actividad_m, "resultados": resultados_m, "objetivo": objetivo_m,
                    "novedades": novedades_m, "participantes": participantes_m,
                    "armas_blancas": armas_m, "asistentes": asistentes_m,
                    "latitud": lat_m, "longitud": lon_m
                }
                guardar_pin(data, fotos_m)
                st.success(f"✅ {pin_id_m} guardado con éxito.")
                st.rerun()

# =============================================================
# GESTIÓN Y EDICIÓN COMPLETA
# =============================================================
with tab_editar:
    st.subheader("✏️ Gestión y Edición de Pines")
    df_pines_edit = cargar_datos()

    if df_pines_edit.empty:
        st.info("No hay registros para editar.")
    else:
        pin_seleccionado = st.selectbox("Selecciona el Pin que deseas modificar:", df_pines_edit["id_pin"].tolist(), key="p_edit")
        registro_actual = df_pines_edit[df_pines_edit["id_pin"] == pin_seleccionado].iloc[0]

        with st.form("form_edicion"):
            st.markdown(f"#### Modificando: **{pin_seleccionado}**")
            c_id1, c_id2 = st.columns([1, 2])
            with c_id1:
                nuevo_id = st.text_input("Identificador (ID)", value=registro_actual["id_pin"])
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
                nuevos_asistentes = st.number_input("Población impactada (cifra)", min_value=0, step=10, value=int(registro_actual["asistentes"]))

            nueva_poblacion = st.text_input("Descripción Población", value=registro_actual["poblacion"])
            nueva_actividad = st.text_input("Actividad", value=registro_actual["actividad"])
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

            nuevas_fotos = st.file_uploader("Adjuntar nuevas fotografías:", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="up_edit")

            if st.form_submit_button("💾 Guardar Cambios"):
                nuevo_id = nuevo_id.strip()
                id_ant = registro_actual["id_pin"]
                conn = get_db_connection()
                c = conn.cursor()

                if nuevo_id != id_ant:
                    c.execute("SELECT id_pin FROM pines WHERE id_pin = ?", (nuevo_id,))
                    if c.fetchone():
                        st.error(f"El ID '{nuevo_id}' ya existe.")
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
                st.success(f"✅ Pin '{nuevo_id}' actualizado.")
                st.rerun()

        st.markdown("---")
        with st.expander("🗑️ Eliminar Pin"):
            if st.button(f"Confirmar eliminación de {pin_seleccionado}", type="primary"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("DELETE FROM pines WHERE id_pin = ?", (pin_seleccionado,))
                conn.commit()
                conn.close()
                carp_del = os.path.join(CARPETA_EVIDENCIAS, pin_seleccionado)
                if os.path.exists(carp_del):
                    shutil.rmtree(carp_del)
                st.success(f"Registro {pin_seleccionado} eliminado.")
                st.rerun()