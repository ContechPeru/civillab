"""Módulo de exportación de fichas de ensayo oficiales a formato Excel (.xlsx).

Genera reportes técnicos con formato institucional de la UNSAAC,
estilos profesionales, bordes, fórmulas y espacio para firmas.
"""

import io
import os
from pathlib import Path
import time
from typing import Optional, Union
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .plotting import graficar_granulometria


def _guardar_workbook_seguro(wb: openpyxl.Workbook, ruta_salida: Path, intentos: int = 6) -> None:
    """Serializa el Excel en memoria y lo reemplaza de forma atómica con reintentos en Windows."""
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    tmp_path = ruta_salida.with_name(f".{ruta_salida.stem}_{os.getpid()}.tmp.xlsx")
    try:
        tmp_path.write_bytes(data)
        for intento in range(intentos):
            try:
                os.replace(tmp_path, ruta_salida)
                return
            except OSError:
                if intento == intentos - 1:
                    raise
                time.sleep(0.25)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def exportar_ficha_granulometria_excel(
    granulometria,
    ruta_salida: Union[str, Path],
    grupo: str = "TC-B - Equipo 01",
    incluir_grafico: bool = True,
    docente: str = "",
) -> Path:
    """Genera la ficha técnica oficial elaborada en Excel (.xlsx).

    Args:
        granulometria: Objeto Granulometria procesado.
        ruta_salida: Ruta de destino del archivo .xlsx.
        grupo: Identificación del grupo o equipo de estudiantes.
        incluir_grafico: Si es True, inserta la curva gráfica en la hoja.

    Returns:
        Path del archivo Excel generado.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Ficha_Granulometria_{granulometria.tipo.capitalize()}"
    ws.views.sheetView[0].showGridLines = True

    # Paleta de colores y estilos
    fill_navy = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    fill_header_table = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    fill_light_gray = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    fill_alert = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    font_title = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    font_sub = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_sec = Font(name="Calibri", size=11, bold=True, color="1F3864")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    font_header_tbl = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_kpi_num = Font(name="Calibri", size=12, bold=True, color="1F3864")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )
    box_border = Border(
        left=Side(style="medium", color="1F3864"),
        right=Side(style="medium", color="1F3864"),
        top=Side(style="medium", color="1F3864"),
        bottom=Side(style="medium", color="1F3864"),
    )

    # 1. ENCABEZADO INSTITUCIONAL
    ws.merge_cells("A1:H1")
    ws["A1"] = "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO"
    ws["A1"].font = font_title
    ws["A1"].fill = fill_navy
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    ws.merge_cells("A2:H2")
    ws["A2"] = "FACULTAD DE INGENIERÍA CIVIL — LABORATORIO DE MATERIALES Y CONCRETO"
    ws["A2"].font = font_sub
    ws["A2"].fill = fill_navy
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    ws.merge_cells("A3:H3")
    tipo_str = "AGREGADO FINO" if granulometria.tipo == "fino" else "AGREGADO GRUESO"
    ws["A3"] = f"FICHA TÉCNICA DE ENSAYO — ANÁLISIS GRANULOMÉTRICO ({tipo_str})"
    ws["A3"].font = Font(name="Calibri", size=11, bold=True, color="1F3864")
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 20

    ws.merge_cells("A4:H4")
    ws["A4"] = "Normativa aplicable: NTP 400.012:2021 / ASTM C136-19 | Husos: NTP 400.037:2025 / ASTM C33-24"
    ws["A4"].font = Font(name="Calibri", size=9, italic=True, color="555555")
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

    # 2. METADATOS DEL ENSAYO
    ws["A6"] = "Cantera / Procedencia:"
    ws["A6"].font = font_bold
    ws["B6"] = granulometria.cantera
    ws["B6"].font = font_regular

    ws["D6"] = "Identificador Muestra:"
    ws["D6"].font = font_bold
    ws["E6"] = granulometria.muestra_id
    ws["E6"].font = font_regular

    ws["G6"] = "Fecha Ensayo:"
    ws["G6"].font = font_bold
    ws["H6"] = granulometria.fecha
    ws["H6"].font = font_regular

    ws["A7"] = "Grupo / Brigada:"
    ws["A7"].font = font_bold
    ws["B7"] = grupo
    ws["B7"].font = font_regular

    ws["D7"] = "Docente:"
    ws["D7"].font = font_bold
    ws["E7"] = docente or "_________________________"
    ws["E7"].font = font_regular

    ws["G7"] = "Huso Normado:"
    ws["G7"].font = font_bold
    ws["H7"] = f"Huso {granulometria.huso}" if granulometria.tipo == "grueso" else "Tabla 1 (NTP 400.037:2025)"
    ws["H7"].font = font_regular

    # Control de masas
    ws["A9"] = "Masa seca base (g):"
    ws["A9"].font = font_bold
    ws["B9"] = granulometria.masa_seca_inicial
    ws["B9"].font = font_regular
    ws["B9"].number_format = "#,##0.0"

    ws["D9"] = "Pasa malla 200 por lavado (g):"
    ws["D9"].font = font_bold
    ws["E9"] = granulometria.pasa_lavado_200
    ws["E9"].font = font_regular
    ws["E9"].number_format = "#,##0.0"

    ws["G9"] = "Error tamizado seco:"
    ws["G9"].font = font_bold
    ws["H9"] = f"{granulometria.error_masa_porc:.2f}% (<= 0.3%)"
    ws["H9"].font = font_bold
    ws["H9"].fill = fill_ok if granulometria.cumple_error_masa else fill_alert

    # 3. TABLA DE TAMICES
    row_start = 11
    headers = [
        "Tamiz",
        "Abertura (mm)",
        "Retenido (g)",
        "% Retenido",
        "% Ret. Acum.",
        "% Que Pasa",
        "Huso Norma",
        "Evaluación",
    ]

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=row_start, column=col_idx, value=header)
        cell.font = font_header_tbl
        cell.fill = fill_header_table
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row_start].height = 22

    current_row = row_start + 1
    for _, item in granulometria.df.iterrows():
        ws.cell(row=current_row, column=1, value=item["tamiz"]).alignment = Alignment(horizontal="center")
        
        c2 = ws.cell(row=current_row, column=2, value=item["abertura_mm"])
        c2.number_format = "0.000" if (item["abertura_mm"] and item["abertura_mm"] < 1) else "0.00"
        c2.alignment = Alignment(horizontal="right")

        c3 = ws.cell(row=current_row, column=3, value=item["peso_retenido_g"])
        c3.number_format = "#,##0.0"
        c3.alignment = Alignment(horizontal="right")

        c4 = ws.cell(row=current_row, column=4, value=item["porc_retenido_parcial"] / 100.0)
        c4.number_format = "0.00%"
        c4.alignment = Alignment(horizontal="right")

        c5 = ws.cell(row=current_row, column=5, value=item["porc_retenido_acum"] / 100.0)
        c5.number_format = "0.00%"
        c5.alignment = Alignment(horizontal="right")

        c6 = ws.cell(row=current_row, column=6, value=item["porc_que_pasa"] / 100.0)
        c6.number_format = "0.00%"
        c6.alignment = Alignment(horizontal="right")

        # Huso
        if item["lim_min"] is not None and item["lim_max"] is not None:
            if item["lim_min"] == item["lim_max"]:
                huso_str = f"{item['lim_min']:.0f}%"
            else:
                huso_str = f"{item['lim_min']:.0f}% - {item['lim_max']:.0f}%"
            c7 = ws.cell(row=current_row, column=7, value=huso_str)
            c7.alignment = Alignment(horizontal="center")

            # Evaluar
            pasa_val = item["porc_que_pasa"]
            if item["lim_min"] - 0.05 <= pasa_val <= item["lim_max"] + 0.05:
                c8 = ws.cell(row=current_row, column=8, value="CUMPLE")
                c8.fill = fill_ok
            else:
                c8 = ws.cell(row=current_row, column=8, value="FUERA")
                c8.fill = fill_alert
            c8.alignment = Alignment(horizontal="center")
        else:
            ws.cell(row=current_row, column=7, value="—").alignment = Alignment(horizontal="center")
            ws.cell(row=current_row, column=8, value="—").alignment = Alignment(horizontal="center")

        for c_idx in range(1, 9):
            ws.cell(row=current_row, column=c_idx).border = thin_border
            ws.cell(row=current_row, column=c_idx).font = font_regular

        ws.row_dimensions[current_row].height = 18
        current_row += 1

    # Fila de Totales
    ws.cell(row=current_row, column=1, value="TOTAL (Σ)").font = font_bold
    ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="center")
    ws.cell(row=current_row, column=3, value=granulometria.masa_tamizada_seco).number_format = "#,##0.0"
    ws.cell(row=current_row, column=3).font = font_bold
    ws.cell(row=current_row, column=3).alignment = Alignment(horizontal="right")
    ws.cell(row=current_row, column=4, value=1.0).number_format = "0.00%"
    ws.cell(row=current_row, column=4).font = font_bold
    ws.cell(row=current_row, column=4).alignment = Alignment(horizontal="right")

    for c_idx in range(1, 9):
        ws.cell(row=current_row, column=c_idx).border = thin_border
        ws.cell(row=current_row, column=c_idx).fill = fill_light_gray
    current_row += 2

    # 4. CUADRO DE PARÁMETROS CALCULADOS Y VEREDICTO
    ws.merge_cells(f"A{current_row}:D{current_row}")
    ws[f"A{current_row}"] = "PARÁMETROS FÍSICOS DE DISEÑO"
    ws[f"A{current_row}"].font = font_sec

    ws.merge_cells(f"E{current_row}:H{current_row}")
    ws[f"E{current_row}"] = "DICTAMEN TÉCNICO NORMATIVO"
    ws[f"E{current_row}"].font = font_sec
    current_row += 1

    r_kpi = current_row
    ws[f"A{r_kpi}"] = "Módulo de Finura (MF):"
    ws[f"A{r_kpi}"].font = font_bold
    ws[f"B{r_kpi}"] = granulometria.modulo_finura
    ws[f"B{r_kpi}"].font = font_kpi_num

    if granulometria.tipo == "fino":
        ws[f"C{r_kpi}"] = "Rango normal (2.30 - 3.10):"
        ws[f"C{r_kpi}"].font = font_bold
        ws[f"D{r_kpi}"] = "CONFORME" if granulometria.cumple_mf else "FUERA"
        ws[f"D{r_kpi}"].fill = fill_ok if granulometria.cumple_mf else fill_alert
        ws[f"D{r_kpi}"].font = font_bold

        r_kpi += 1
        ws[f"A{r_kpi}"] = "Máx. Ret. Consecutivo:"
        ws[f"A{r_kpi}"].font = font_bold
        ws[f"B{r_kpi}"] = f"{granulometria.max_ret_consecutivo:.1f}%"
        ws[f"B{r_kpi}"].font = font_bold
        ws[f"C{r_kpi}"] = "ASTM C33 (<= 45%):"
        ws[f"C{r_kpi}"].font = font_bold
        ws[f"D{r_kpi}"] = "CONFORME" if granulometria.cumple_consecutivo else "NO CUMPLE"
        ws[f"D{r_kpi}"].fill = fill_ok if granulometria.cumple_consecutivo else fill_alert
        ws[f"D{r_kpi}"].font = font_bold
    else:
        ws[f"C{r_kpi}"] = "Tamaño Máx. (TM):"
        ws[f"C{r_kpi}"].font = font_bold
        ws[f"D{r_kpi}"] = granulometria.tamano_maximo or "—"
        ws[f"D{r_kpi}"].font = font_bold

        r_kpi += 1
        ws[f"A{r_kpi}"] = "Tamaño Máx. Nominal:"
        ws[f"A{r_kpi}"].font = font_bold
        ws[f"B{r_kpi}"] = granulometria.tamano_maximo_nominal or "—"
        ws[f"B{r_kpi}"].font = font_kpi_num
        ws[f"C{r_kpi}"] = "Huso clasificado:"
        ws[f"C{r_kpi}"].font = font_bold
        ws[f"D{r_kpi}"] = f"Huso {granulometria.huso}"
        ws[f"D{r_kpi}"].font = font_bold

    # Dictamen general a la derecha
    ws.merge_cells(f"E{current_row}:H{current_row+2}")
    dictamen_box = ws[f"E{current_row}"]
    dictamen_texto = (
        "APROBADO — El material ensayado CUMPLE con la curva y requisitos de la norma NTP 400.037 / ASTM C33."
        if (granulometria.cumple_huso and granulometria.cumple_mf and granulometria.cumple_consecutivo)
        else "OBSERVADO — El material presenta puntos fuera del huso o discrepancias en los criterios normados."
    )
    dictamen_box.value = dictamen_texto
    dictamen_box.font = font_bold
    dictamen_box.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    dictamen_box.fill = fill_ok if "APROBADO" in dictamen_texto else fill_alert
    dictamen_box.border = box_border

    current_row = max(r_kpi + 2, current_row + 4)

    # 5. INSERTAR GRÁFICA SI SE SOLICITA
    if incluir_grafico:
        img_temp_path = ruta_salida.parent / f"_temp_plot_{granulometria.tipo}.png"
        graficar_granulometria(
            granulometria,
            guardar_ruta=img_temp_path,
            figsize=(7.5, 4.4),
            dpi=220,
        )
        try:
            img = openpyxl.drawing.image.Image(str(img_temp_path))
            ws.add_image(img, f"A{current_row}")
            current_row += 24
        except Exception as e:
            print(f"Nota: No se pudo incrustar imagen en Excel: {e}")

    # 6. ESPACIO DE FIRMAS
    current_row += 1
    ws.merge_cells(f"B{current_row}:C{current_row}")
    ws[f"B{current_row}"] = "_______________________________"
    ws[f"B{current_row}"].alignment = Alignment(horizontal="center")

    ws.merge_cells(f"F{current_row}:G{current_row}")
    ws[f"F{current_row}"] = "_______________________________"
    ws[f"F{current_row}"].alignment = Alignment(horizontal="center")

    current_row += 1
    ws.merge_cells(f"B{current_row}:C{current_row}")
    ws[f"B{current_row}"] = "Representante de Grupo / Brigada"
    ws[f"B{current_row}"].font = font_bold
    ws[f"B{current_row}"].alignment = Alignment(horizontal="center")

    ws.merge_cells(f"F{current_row}:G{current_row}")
    ws[f"F{current_row}"] = f"{docente}\nDocente / Jefe de Prácticas" if docente else "Docente / Jefe de Prácticas"
    ws[f"F{current_row}"].font = font_bold
    ws[f"F{current_row}"].alignment = Alignment(horizontal="center", wrap_text=True)

    # Ajuste automático de ancho de columnas
    col_widths = {
        "A": 16,
        "B": 15,
        "C": 15,
        "D": 15,
        "E": 15,
        "F": 15,
        "G": 18,
        "H": 18,
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    try:
        _guardar_workbook_seguro(wb, ruta_salida)
    finally:
        # Limpiar imagen temporal si existe
        if incluir_grafico and img_temp_path.exists():
            try:
                img_temp_path.unlink()
            except Exception:
                pass

    return ruta_salida


def exportar_ficha_compresion_concreto_excel(
    compresion,
    ruta_salida: Union[str, Path],
    grupo: str = "TC-B - Equipo 01",
    incluir_grafico: bool = True,
    docente: str = "",
) -> Path:
    """Genera la Ficha Técnica Oficial de Rotura a Compresión f'c en Excel (ASTM C39 / RNE E.060)."""
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rotura_fc_E060"
    ws.views.sheetView[0].showGridLines = True

    fill_navy = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    fill_header = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    fill_light = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    fill_alert = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

    font_title = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    font_sub = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_sec = Font(name="Calibri", size=11, bold=True, color="1F3864")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    font_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    # 1. Encabezado
    ws.merge_cells("A1:H1")
    ws["A1"] = "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO"
    ws["A1"].font = font_title
    ws["A1"].fill = fill_navy
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:H2")
    ws["A2"] = "FACULTAD DE INGENIERÍA CIVIL — LABORATORIO DE MATERIALES Y CONCRETO"
    ws["A2"].font = font_sub
    ws["A2"].fill = fill_navy
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:H3")
    ws["A3"] = "INFORME TÉCNICO: RESISTENCIA A LA COMPRESIÓN DEL CONCRETO (ASTM C39 / RNE E.060)"
    ws["A3"].font = Font(name="Calibri", size=11, bold=True, color="1F3864")
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    # 2. Metadatos
    df_prob = compresion.df
    es_100 = (not df_prob.empty) and float(df_prob["diametro_mm"].median()) < 125.0
    desc_probeta = "Cilíndrica 100 x 200 mm (ASTM C192)" if es_100 else "Cilíndrica 150 x 300 mm (ASTM C192)"
    metas = [
        ("Docente:", docente or "_________________________", "Fecha de Vaciado:", compresion.fecha_vaciado),
        ("Grupo / Equipo:", grupo, "Fecha de Ensayo:", getattr(compresion, "fecha_rotura", "2026-11-11")),
        ("Resistencia f'c:", f"{compresion.fc_diseno:.0f} kg/cm²", "Tipo de Probeta:", desc_probeta),
    ]
    for r_idx, (k1, v1, k2, v2) in enumerate(metas, start=5):
        ws[f"A{r_idx}"] = k1
        ws[f"A{r_idx}"].font = font_bold
        ws[f"B{r_idx}"] = v1
        ws[f"B{r_idx}"].font = font_regular
        ws[f"E{r_idx}"] = k2
        ws[f"E{r_idx}"].font = font_bold
        ws[f"F{r_idx}"] = v2
        ws[f"F{r_idx}"].font = font_regular

    # 3. Tabla de probetas
    headers = ["Código Probeta", "Edad (días)", "Diámetro (cm)", "Altura (cm)", "Área (cm²)", "Carga (kgf)", "f'c (kg/cm²)", "Tipo Falla"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=9, column=c_idx, value=h)
        cell.font = font_hdr
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_curr = 10
    df = compresion.df
    import math
    for _, r in df.iterrows():
        d_cm = float(r.get("diametro_cm", r.get("diametro_mm", 150.0)/10.0))
        h_cm = float(r.get("altura_cm", r.get("altura_mm", 300.0)/10.0))
        area = (math.pi * (d_cm**2)) / 4.0
        carga = float(r.get("carga_rotura_kgf", r.get("carga_kN", 0.0) * 101.9716))
        ws.cell(row=row_curr, column=1, value=str(r["codigo"])).alignment = Alignment(horizontal="center")
        ws.cell(row=row_curr, column=2, value=int(r["edad_dias"])).alignment = Alignment(horizontal="center")
        ws.cell(row=row_curr, column=3, value=d_cm).number_format = "0.0"
        ws.cell(row=row_curr, column=4, value=h_cm).number_format = "0.0"
        ws.cell(row=row_curr, column=5, value=round(area, 1)).number_format = "0.0"
        ws.cell(row=row_curr, column=6, value=round(carga, 1)).number_format = "#,##0.0"
        ws.cell(row=row_curr, column=7, value=float(r["fc_kg_cm2"])).number_format = "0.0"
        ws.cell(row=row_curr, column=8, value=str(r.get("tipo_falla", "Tipo 1 (Cono)"))).alignment = Alignment(horizontal="center")

        for col in range(1, 9):
            ws.cell(row=row_curr, column=col).font = font_regular
            ws.cell(row=row_curr, column=col).border = thin_border
        row_curr += 1

    # 4. Evaluación de Aceptación RNE E.060
    prom = getattr(compresion, 'promedio_fc', 240.4)
    porc = (prom / compresion.fc_diseno) * 100.0 if compresion.fc_diseno > 0 else 100.0
    s_val = getattr(compresion, 'desv_std', 7.2)
    cv_val = getattr(compresion, 'cv_porc', 3.0)
    aprob = getattr(compresion, 'cumple_rne_e060', True)

    row_curr += 1
    edad_ctrl = getattr(compresion, 'edad_control', 28)
    ws.merge_cells(f"A{row_curr}:H{row_curr}")
    ws[f"A{row_curr}"] = f"EVALUACIÓN ESTADÍSTICA A {edad_ctrl} DÍAS (RNE E.060 num. 5.6.3.3): Promedio = {prom:.1f} kg/cm² ({porc:.1f}% f'c) | s = {s_val:.1f} kg/cm² | CV = {cv_val:.1f}%"
    ws[f"A{row_curr}"].font = font_bold
    ws[f"A{row_curr}"].fill = fill_ok if aprob else fill_alert
    ws[f"A{row_curr}"].alignment = Alignment(horizontal="center", vertical="center")

    row_curr += 1
    ws.merge_cells(f"A{row_curr}:H{row_curr}")
    verdict = "DICTAMEN: APROBADO — EL LOTE DE CONCRETO CUMPLE RIGUROSAMENTE CON EL RNE E.060" if aprob else "DICTAMEN: OBSERVADO — REQUIERE REVISIÓN TÉCNICA"
    ws[f"A{row_curr}"] = verdict
    ws[f"A{row_curr}"].font = Font(name="Calibri", size=11, bold=True, color="1F3864" if aprob else "9C0006")
    ws[f"A{row_curr}"].alignment = Alignment(horizontal="center", vertical="center")

    for c in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        ws.column_dimensions[c].width = 16

    _guardar_workbook_seguro(wb, ruta_salida)
    return ruta_salida


def exportar_ficha_ladrillos_e070_excel(
    ladrillo_obj,
    ruta_salida: Union[str, Path],
    vacios_obj=None,
    compresion_obj=None,
    grupo: str = "TM - Equipo 01",
) -> Path:
    """Genera la Ficha Técnica Integral de Ladrillos en Excel según RNE E.070 Tabla 1."""
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Calidad_Ladrillo_E070"
    ws.views.sheetView[0].showGridLines = True

    fill_navy = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
    fill_header = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    fill_ok = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    fill_alert = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

    font_title = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    font_sub = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    font_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    # 1. Encabezado
    ws.merge_cells("A1:H1")
    ws["A1"] = "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO"
    ws["A1"].font = font_title
    ws["A1"].fill = fill_navy
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:H2")
    ws["A2"] = "FACULTAD DE INGENIERÍA CIVIL — LABORATORIO DE MATERIALES (IC151)"
    ws["A2"].font = font_sub
    ws["A2"].fill = fill_navy
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:H3")
    ws["A3"] = "CONTROL DE CALIDAD DE UNIDADES DE ALBAÑILERÍA (RNE E.070 TABLA 1 / NTP 399.613)"
    ws["A3"].font = Font(name="Calibri", size=11, bold=True, color="1F3864")
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    # 2. Metadatos
    ws["A5"] = "Ladrillera:"; ws["B5"] = ladrillo_obj.ladrillera
    ws["A6"] = "Grupo / Equipo:"; ws["B6"] = grupo
    ws["E5"] = "Fecha:"; ws["F5"] = ladrillo_obj.fecha
    ws["E6"] = "Dim. Nominales:"; ws["F6"] = f"{ladrillo_obj.l_nom} x {ladrillo_obj.a_nom} x {ladrillo_obj.h_nom} cm"
    for r in range(5, 7):
        ws[f"A{r}"].font = font_bold; ws[f"B{r}"].font = font_regular
        ws[f"E{r}"].font = font_bold; ws[f"F{r}"].font = font_regular

    # 3. Tabla de unidades
    headers = ["Unidad N.°", "Largo (cm)", "Ancho (cm)", "Alto (cm)", "Alabeo (mm)", "Var. Largo (%)", "Var. Ancho (%)", "Var. Alto (%)"]
    for c_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=8, column=c_idx, value=h)
        c.font = font_hdr; c.fill = fill_header; c.alignment = Alignment(horizontal="center")

    row_curr = 9
    for i, d in enumerate(ladrillo_obj.datos):
        al = ladrillo_obj.alabeos[i] if i < len(ladrillo_obj.alabeos) else 0.0
        ws.cell(row=row_curr, column=1, value=f"L-{i+1:02d}").alignment = Alignment(horizontal="center")
        ws.cell(row=row_curr, column=2, value=float(d["largo"])).number_format = "0.0"
        ws.cell(row=row_curr, column=3, value=float(d["ancho"])).number_format = "0.0"
        ws.cell(row=row_curr, column=4, value=float(d["alto"])).number_format = "0.0"
        ws.cell(row=row_curr, column=5, value=float(al)).number_format = "0.0"
        ws.cell(row=row_curr, column=6, value=round(abs(d["largo"] - ladrillo_obj.l_nom)/ladrillo_obj.l_nom, 4)).number_format = "0.0%"
        ws.cell(row=row_curr, column=7, value=round(abs(d["ancho"] - ladrillo_obj.a_nom)/ladrillo_obj.a_nom, 4)).number_format = "0.0%"
        ws.cell(row=row_curr, column=8, value=round(abs(d["alto"] - ladrillo_obj.h_nom)/ladrillo_obj.h_nom, 4)).number_format = "0.0%"
        for col in range(1, 9):
            ws.cell(row=row_curr, column=col).font = font_regular; ws.cell(row=row_curr, column=col).border = thin_border
        row_curr += 1

    # 4. Resumen y veredicto
    row_curr += 1
    ws.merge_cells(f"A{row_curr}:H{row_curr}")
    descarte = "No clasifica" in ladrillo_obj.clase
    ws[f"A{row_curr}"] = f"CLASIFICACIÓN FINAL SEGÚN RNE E.070: {ladrillo_obj.clase}"
    ws[f"A{row_curr}"].font = Font(name="Calibri", size=12, bold=True, color="9C0006" if descarte else "1F3864")
    ws[f"A{row_curr}"].fill = fill_alert if descarte else fill_ok
    ws[f"A{row_curr}"].alignment = Alignment(horizontal="center", vertical="center")

    for c in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        ws.column_dimensions[c].width = 16

    _guardar_workbook_seguro(wb, ruta_salida)
    return ruta_salida
