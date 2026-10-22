import os
import re
import openpyxl
import pdfplumber

def extraer_datos_contrato(ruta_pdf, nombre_carpeta_contratista):
    """
    Extrae la información de cada anexo contractual PDF.
    """
    with pdfplumber.open(ruta_pdf) as pdf:
        texto = "\n".join([pagina.extract_text() or "" for pagina in pdf.pages])
    
    # 1. Número de Contrato (ej. GN3214-2026, GN0138-2026)
    num_contrato = ""
    m_num = re.search(r'CONTRATO\s+N[°o\.]*\s*:?\s*([A-Z0-9\-\s]+?)(?:DE\s+PRESTACI[OÓ]N|\n)', texto, re.IGNORECASE)
    if m_num:
        num_contrato = re.sub(r'\s+', '', m_num.group(1).strip())
    else:
        # Búsqueda alternativa por formato GNxxxx-2026
        m_gn = re.search(r'(GN\s*\d{3,5}\s*-\s*202\d)', texto, re.IGNORECASE)
        if m_gn:
            num_contrato = re.sub(r'\s+', '', m_gn.group(1))

    # 2. Contratista (Prioriza el nombre de la subcarpeta que ya viene normalizado)
    contratista = nombre_carpeta_contratista.strip()

    # 3. Objeto Contractual
    objeto = ""
    m_obj = re.search(r'OBJETO\s+(?:DEL\s+CONTRATO)?\s*:\s*[\“\"]?(.*?)(?:[\”\"]?\s*SEGUNDA|\.\s*SEGUNDA)', texto, re.IGNORECASE | re.DOTALL)
    if m_obj:
        objeto = re.sub(r'\s+', ' ', m_obj.group(1)).strip('“"” .')

    # 4. Valor Total
    valor_total = ""
    m_val = re.search(r'VALOR\s+DEL\s+CONTRATO\s*:\s*.*?\(\s*\$\s*([\d\.\,]+)\s*\)', texto, re.IGNORECASE | re.DOTALL)
    if not m_val:
        m_val = re.search(r'\(\s*\$\s*([\d\.\,]+)\s*\)\s*M', texto, re.IGNORECASE)
    
    if m_val:
        val_str = m_val.group(1).replace(".", "").replace(",", ".")
        try:
            valor_total = float(val_str)
        except ValueError:
            valor_total = m_val.group(1).strip()

    # 5. Plazo de Ejecución
    plazo = ""
    m_plz = re.search(r'PLAZO\s+DE\s+EJECUCI[OÓ]N\s*:\s*(.*?)(?:CUARTA|\n\n)', texto, re.IGNORECASE | re.DOTALL)
    if m_plz:
        plazo = re.sub(r'\s+', ' ', m_plz.group(1)).strip()

    # 6. Fecha de Disponibilidad Presupuestal / Suscripción (Cláusula SEXTA)
    fecha_suscripcion = ""
    m_sexta = re.search(r'SEXTA.*?(?=S[EÉ]PTIMA)', texto, re.DOTALL | re.IGNORECASE)
    if m_sexta:
        m_fecha = re.search(r'(\d{2}/\d{2}/202\d)', m_sexta.group(0))
        if m_fecha:
            fecha_suscripcion = m_fecha.group(1)

    # 7. Fuente de Financiación
    if "FONSET" in texto:
        fuente = "FONSET"
    elif "FONDELIBERTAD" in texto:
        fuente = "FONDELIBERTAD"
    elif "SGP" in texto:
        fuente = "SGP"
    else:
        fuente = "Recursos Propios"

    # 8. Estado y Actas
    estado_ejecucion = "En ejecución"
    actas_comites = "Expediente Contractual Digital"

    return [
        num_contrato,
        objeto,
        contratista,
        valor_total,
        plazo,
        fecha_suscripcion,
        estado_ejecucion,
        fuente,
        actas_comites
    ]

def procesar_todas_las_carpetas(directorio_raiz, archivo_plantilla):
    wb = openpyxl.load_workbook(archivo_plantilla)
    hoja = wb.active

    # La fila 3 contiene los encabezados; los registros inician en la fila 4
    fila_actual = 4
    while hoja.cell(row=fila_actual, column=1).value is not None:
        fila_actual += 1

    total_procesados = 0
    print(f"[*] Escaneando subcarpetas en: {directorio_raiz}")

    for carpeta_actual, _, archivos in sorted(os.walk(directorio_raiz)):
        nombre_carpeta = os.path.basename(carpeta_actual)
        
        # Omitir la carpeta raíz si no contiene directamente los PDFs
        if carpeta_actual == directorio_raiz:
            continue

        for archivo in sorted(archivos):
            if archivo.lower().endswith(".pdf") and not archivo.startswith("._"):
                ruta_pdf = os.path.join(carpeta_actual, archivo)
                try:
                    datos = extraer_datos_contrato(ruta_pdf, nombre_carpeta)
                    
                    for col_idx, valor in enumerate(datos, start=1):
                        celda = hoja.cell(row=fila_actual, column=col_idx)
                        celda.value = valor
                        
                        # Formato de moneda para la columna VALOR TOTAL (columna 4)
                        if col_idx == 4 and isinstance(valor, (int, float)):
                            celda.number_format = '$#,##0'
                    
                    print(f" [+] Registrado: {nombre_carpeta} -> {archivo} ({datos[0] or 'Sin No.'})")
                    fila_actual += 1
                    total_procesados += 1
                except Exception as e:
                    print(f" [!] Error al procesar {archivo}: {e}")

    salida_excel = "MATRIZ_DILIGENCIADA.xlsx"
    wb.save(salida_excel)
    print(f"\n[OK] Diligenciamiento completado: {total_procesados} contratos guardados en '{salida_excel}'.")

if __name__ == "__main__":
    # Nombre tal cual aparece en tu explorador de archivos
    DIRECTORIO = "extracted_contratos"
    PLANTILLA = "MATRIZ.xlsx"

    if os.path.exists(DIRECTORIO) and os.path.exists(PLANTILLA):
        procesar_todas_las_carpetas(DIRECTORIO, PLANTILLA)
    else:
        print("Asegúrate de que la carpeta 'extrated_contratos' y el archivo 'MATRIZ.xlsx' estén en la misma ruta.")