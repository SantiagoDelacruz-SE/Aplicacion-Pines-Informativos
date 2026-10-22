import re
import os
import sqlite3
from datetime import datetime

# -------------------------------------------------------------
# Catálogo de Coordenadas de los Municipios de Nariño
# -------------------------------------------------------------
MUNICIPIOS_NARINO = {
    "Pasto (Capital)": (1.2136, -77.2811),
    "Aldana": (0.8797, -77.7003),
    "Ancuya": (1.2608, -77.5303),
    "Arboleda (Berruecos)": (1.5033, -77.1408),
    "Barbacoas": (1.6719, -78.1397),
    "Belén": (1.5975, -77.0519),
    "Buesaco": (1.3853, -77.1558),
    "Chachagüí": (1.3606, -77.2842),
    "Colón (Génova)": (1.6369, -76.9744),
    "Consacá": (1.2094, -77.4633),
    "Contadero": (0.9108, -77.5622),
    "Córdoba": (0.8589, -77.5217),
    "Cuaspud (Carlosama)": (0.8767, -77.7289),
    "Cumbal": (0.9142, -77.7944),
    "Cumbitara": (1.6569, -77.5856),
    "El Charco": (2.4769, -78.1103),
    "El Peñol": (1.4644, -77.4475),
    "El Rosario": (1.7456, -77.3400),
    "El Tablón de Gómez": (1.4258, -77.0983),
    "El Tambo": (1.4172, -77.3967),
    "Francisco Pizarro (Salahonda)": (2.0628, -78.6578),
    "Funes": (1.0028, -77.5208),
    "Guachucal": (0.9639, -77.7303),
    "Guaitarilla": (1.1344, -77.5508),
    "Gualmatán": (0.9189, -77.5694),
    "Iles": (0.9856, -77.5244),
    "Imués": (1.0967, -77.5258),
    "Ipiales": (0.8242, -77.6389),
    "La Cruz": (1.6044, -76.9714),
    "La Florida": (1.3006, -77.4042),
    "La Llanada": (1.4489, -77.5861),
    "La Tola": (2.4044, -78.2197),
    "La Unión": (1.6033, -77.1317),
    "Leiva": (1.9350, -77.3183),
    "Linares": (1.3789, -77.5028),
    "Los Andes (Sotomayor)": (1.4880, -77.5250),
    "Magüí Payán": (1.7042, -78.1969),
    "Mallama (Piedrancha)": (1.1069, -77.8592),
    "Mosquera": (2.5111, -78.4528),
    "Nariño": (1.2981, -77.3619),
    "Olavaya Herrera (Bocas de Satinga)": (2.3392, -78.3267),
    "Ospina": (1.0578, -77.5697),
    "Policarpa": (1.7167, -77.4483),
    "Potosí": (0.8142, -77.5736),
    "Providencia": (1.2403, -77.6019),
    "Puerres": (0.8925, -77.5083),
    "Pupiales": (0.8711, -77.6439),
    "Ricaurte": (1.2139, -78.1561),
    "Roberto Payán (San José)": (1.6961, -78.2589),
    "Samaniego": (1.3389, -77.5956),
    "San Bernardo": (1.5281, -77.0436),
    "San Lorenzo": (1.5036, -77.2189),
    "San Pablo": (1.6742, -77.0147),
    "San Pedro de Cartago": (1.5606, -77.1206),
    "Sandoná": (1.2883, -77.4719),
    "Santa Bárbara (Iscuandé)": (2.4489, -77.9819),
    "Santacruz (Guachavés)": (1.2975, -77.7289),
    "Sapuyes": (1.0333, -77.7167),
    "Taminango": (1.5878, -77.2750),
    "Tangua": (1.0967, -77.3958),
    "Tumaco": (1.7986, -78.8156),
    "Túquerres": (1.0872, -77.6186),
    "Yacuanquer": (1.1206, -77.3986)
}

LISTA_MUNICIPIOS = sorted(list(MUNICIPIOS_NARINO.keys()))

# -------------------------------------------------------------
# Conexión y Esquema de Base de Datos
# -------------------------------------------------------------
def inicializar_bd():
    conn = sqlite3.connect("pines_observatorio.db")
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
            latitud REAL,
            longitud REAL,
            rutas_fotos TEXT,
            fecha_registro TEXT
        )
    """)
    conn.commit()
    return conn

# -------------------------------------------------------------
# Parser de Extracción de Campos
# -------------------------------------------------------------
def extraer_valor(campo: str, texto: str) -> str:
    """Extrae el valor del campo considerando separaciones variables de espacios o saltos de línea."""
    patron = rf"{campo}\s*:\s*(.*?)(?=\s+(?:Fecha|Hora|Lugar|Meta|Población|Actividad|Resultados|Objetivo|Novedades|Participantes)\s*:|\Z)"
    match = re.search(patron, texto, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

def inferir_municipio(bloque_texto: str) -> str:
    texto_l = bloque_texto.lower()
    for m in LISTA_MUNICIPIOS:
        nombre_base = re.sub(r"\s*\(.*?\)", "", m).strip().lower()
        # Busca el nombre del municipio como palabra completa
        if re.search(rf"\b{nombre_base}\b", texto_l):
            return m
    return "Pasto (Capital)"

def procesar_archivo_pines(ruta_txt: str):
    if not os.path.exists(ruta_txt):
        print(f"❌ Error: No se encontró el archivo '{ruta_txt}'. Asegúrate de colocarlo en la misma carpeta.")
        return

    with open(ruta_txt, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Dividir el archivo por cada pin (usando el emoji de chincheta como delimitador)
    bloques = re.split(r"(?=📌\s*PIN\s+INFORMATIVO)", contenido)
    
    conn = inicializar_bd()
    c = conn.cursor()
    
    contador_cargados = 0
    conteo_duplicados = {}

    for bloque in bloques:
        if not bloque.strip():
            continue
        
        # 1. Identificar el número de PIN y normalizar su ID
        match_id = re.search(r"📌\s*PIN\s+INFORMATIVO\s*(?:No?\.?\s*)?(\d+)?", bloque, re.I)
        raw_num = match_id.group(1) if (match_id and match_id.group(1)) else None
        
        # Tratamiento para pines sin numeración o repetidos
        if raw_num:
            base_id = f"PIN_{raw_num.zfill(3)}"
        else:
            base_id = "PIN_SIN_NUMERO"
            
        conteo_duplicados[base_id] = conteo_duplicados.get(base_id, 0) + 1
        if conteo_duplicados[base_id] > 1:
            id_final = f"{base_id}_DUP{conteo_duplicados[base_id]}"
        else:
            id_final = base_id

        # 2. Extracción de variables
        fecha = extraer_valor(r"(?:Fecha del mensaje|Fecha)", bloque)
        hora = extraer_valor(r"Hora", bloque)
        lugar = extraer_valor(r"Lugar", bloque)
        meta = extraer_valor(r"Meta", bloque)
        poblacion = extraer_valor(r"Población impactada", bloque)
        actividad = extraer_valor(r"Actividad", bloque)
        resultados = extraer_valor(r"Resultados", bloque)
        objetivo = extraer_valor(r"Objetivo", bloque)
        novedades = extraer_valor(r"Novedades", bloque)
        participantes = extraer_valor(r"Participantes", bloque)

        # 3. Inferencia de Municipio y Coordenadas Oficiales
        municipio = inferir_municipio(bloque)
        lat, lon = MUNICIPIOS_NARINO.get(municipio, (1.2136, -77.2811))

        # 4. Inferencia de Comuna
        m_comuna = re.search(r"Comuna\s*(\d+)", bloque, re.I)
        comuna = f"Comuna {m_comuna.group(1)}" if m_comuna else "Sin especificar"

        # 5. Métricas Numéricas (Armas y Asistentes)
        armas = 0
        m_armas = re.search(r"(\d+)\s*armas", resultados, re.I)
        if m_armas:
            armas = int(m_armas.group(1))

        asistentes = 0
        m_asist = re.search(r"(\d[\d\.\,]*)\s*(?:aproximadamente|personas|habitantes|familias|asistentes)", poblacion, re.I)
        if m_asist:
            cifra = re.sub(r"[^\d]", "", m_asist.group(1))
            if cifra.isdigit():
                asistentes = int(cifra)
        elif poblacion.isdigit():
            asistentes = int(poblacion)

        # 6. Guardar en SQLite
        c.execute("""
            INSERT OR REPLACE INTO pines VALUES (
                :id_pin, :municipio, :fecha, :hora, :lugar, :comuna, :meta, :poblacion,
                :actividad, :resultados, :objetivo, :novedades, :participantes,
                :armas_blancas, :asistentes, :latitud, :longitud, :rutas_fotos, :fecha_registro
            )
        """, {
            "id_pin": id_final,
            "municipio": municipio,
            "fecha": fecha,
            "hora": hora,
            "lugar": lugar,
            "comuna": comuna,
            "meta": meta if meta else "PISCC",
            "poblacion": poblacion,
            "actividad": actividad,
            "resultados": resultados,
            "objetivo": objetivo,
            "novedades": novedades if novedades else "NINGUNA",
            "participantes": participantes,
            "armas_blancas": armas,
            "asistentes": asistentes,
            "latitud": lat,
            "longitud": lon,
            "rutas_fotos": "",
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        contador_cargados += 1
        print(f"✔️ Registrado: {id_final:<18} | Mpio: {municipio:<20} | Comuna: {comuna}")

    conn.commit()
    conn.close()
    print("\n" + "="*60)
    print(f"🚀 ¡ÉXITO! Se cargaron {contador_cargados} pines a 'pines_observatorio.db'.")
    print("="*60)

if __name__ == "__main__":
    procesar_archivo_pines("PIN INFORMATIVO.txt")