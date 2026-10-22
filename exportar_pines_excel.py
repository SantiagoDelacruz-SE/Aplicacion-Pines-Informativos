import sqlite3
import pandas as pd
from datetime import datetime
import os

BD_PATH = "pines_observatorio.db"
NOMBRE_SALIDA = f"Consolidado_Pines_Observatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

if not os.path.exists(BD_PATH):
    print(f"❌ Error: No se encontró la base de datos '{BD_PATH}'.")
    exit()

# 1. Leer los datos desde SQLite
conn = sqlite3.connect(BD_PATH)
df_pines = pd.read_sql_query("SELECT * FROM pines ORDER BY id_pin ASC", conn)
conn.close()

if df_pines.empty:
    print("⚠️ La base de datos está vacía. No hay pines para exportar.")
    exit()

# Limpieza de nulos para agregaciones numéricas
df_pines["asistentes"] = df_pines["asistentes"].fillna(0).astype(int)
df_pines["armas_blancas"] = df_pines["armas_blancas"].fillna(0).astype(int)

# 2. Generar hojas de análisis y resúmenes

# Hoja 2: Consolidado por Municipio
resumen_municipios = df_pines.groupby("municipio").agg(
    Total_Pines=("id_pin", "count"),
    Poblacion_Impactada_Total=("asistentes", "sum"),
    Armas_Incautadas_Entregadas=("armas_blancas", "sum")
).reset_index().sort_values(by="Total_Pines", ascending=False)

# Hoja 3: Consolidado por Comuna / Sector
resumen_comunas = df_pines[df_pines["comuna"] != "Sin especificar"].groupby("comuna").agg(
    Total_Pines=("id_pin", "count"),
    Poblacion_Impactada=("asistentes", "sum"),
    Armas_Blancas=("armas_blancas", "sum")
).reset_index().sort_values(by="Total_Pines", ascending=False)

# Hoja 4: Consolidado por Meta / Línea PISCC
resumen_metas = df_pines.groupby("meta").agg(
    Total_Actividades=("id_pin", "count"),
    Poblacion_Total=("asistentes", "sum")
).reset_index().sort_values(by="Total_Actividades", ascending=False)

# 3. Escribir el libro Excel con formato
with pd.ExcelWriter(NOMBRE_SALIDA, engine="openpyxl") as writer:
    # Hoja principal con todos los campos
    df_pines.to_excel(writer, sheet_name="Matriz_Pines_General", index=False)
    # Hojas analíticas para tablas dinámicas
    resumen_municipios.to_excel(writer, sheet_name="Resumen_Municipios", index=False)
    resumen_comunas.to_excel(writer, sheet_name="Resumen_Comunas_Pasto", index=False)
    resumen_metas.to_excel(writer, sheet_name="Resumen_Metas_PISCC", index=False)

print("="*60)
print(f"✅ Exportación completada con éxito.")
print(f"📁 Archivo generado: {NOMBRE_SALIDA}")
print(f"📊 Total de registros procesados: {len(df_pines)}")
print("="*60)