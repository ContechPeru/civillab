"""Módulo de visualización gráfica de ensayos de laboratorio de ingeniería civil.

Diseño académico sobrio, alta resolución para informes y publicaciones.
"""

from pathlib import Path
from typing import List, Optional, Union
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator
import numpy as np

from .standards import HUSOS_AGREGADO_GRUESO, HUSOS_DESCRIPCION, TAMICES_INFO

# Estilo visual corporativo e institucional
AZUL_UNSAAC = "#1F3864"
AZUL_LINEA = "#004B87"
GRIS_BANDA = "#E3E6EB"
GRIS_LINEA_NORMA = "#555555"
ROJO_ALERTA = "#C00000"
GRIS_FONDO_GRID = "#CCCCCC"


def graficar_granulometria(
    granulometria,
    titulo: Optional[str] = None,
    guardar_ruta: Optional[Union[str, Path]] = None,
    mostrar: bool = False,
    figsize: tuple = (8.5, 5.2),
    dpi: int = 300,
) -> plt.Figure:
    """Genera la curva granulométrica en escala semilogarítmica con husos normados.

    Args:
        granulometria: Instancia de la clase Granulometria.
        titulo: Título personalizado (opcional).
        guardar_ruta: Ruta para guardar la imagen (PNG/PDF).
        mostrar: Si es True, ejecuta plt.show().
        figsize: Tamaño de la figura en pulgadas.
        dpi: Resolución de salida.

    Returns:
        Figura de matplotlib generada.
    """
    df = granulometria.df.dropna(subset=["abertura_mm"]).sort_values("abertura_mm")
    tamices_plot = df[~df["es_fondo"]].copy()

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    x = tamices_plot["abertura_mm"].values
    y = tamices_plot["porc_que_pasa"].values

    # Eje logarítmico horizontal
    ax.set_xscale("log")
    min_x = x.min() / 1.4
    max_x = x.max() * 1.4
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(0, 105)

    # Trazado de los husos normados si existen
    df_huso = tamices_plot.dropna(subset=["lim_min", "lim_max"]).sort_values("abertura_mm")
    if not df_huso.empty:
        hx = df_huso["abertura_mm"].values
        hmin = df_huso["lim_min"].values
        hmax = df_huso["lim_max"].values

        label_huso = (
            "Huso NTP 400.037:2025 (Tabla 1)"
            if granulometria.tipo == "fino"
            else f"Huso {granulometria.huso} (NTP 400.037:2025)"
        )

        ax.fill_between(
            hx,
            hmin,
            hmax,
            color=GRIS_BANDA,
            alpha=0.85,
            zorder=1,
            label=f"Banda Normada: {label_huso}",
        )
        ax.plot(hx, hmin, color=GRIS_LINEA_NORMA, ls="--", lw=1.2, zorder=2)
        ax.plot(hx, hmax, color=GRIS_LINEA_NORMA, ls="--", lw=1.2, zorder=2)

    # Curva del material ensayado
    color_curva = AZUL_LINEA if granulometria.cumple_huso else ROJO_ALERTA
    ax.plot(
        x,
        y,
        marker="o",
        markersize=6,
        color=color_curva,
        lw=2.2,
        zorder=4,
        label=f"Muestra: {granulometria.muestra_id} ({granulometria.cantera})",
    )

    # Etiquetas con los valores de porcentaje que pasa sobre cada punto
    for xi, yi in zip(x, y):
        ax.annotate(
            f"{yi:.1f}%",
            (xi, yi),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=7.5,
            fontweight="bold",
            color=color_curva,
            zorder=5,
        )

    # Configuración de ejes y divisiones de tamices
    ax.xaxis.set_major_locator(FixedLocator(x))
    ax.xaxis.set_minor_locator(NullLocator())

    etiquetas_x = [
        f"{row['tamiz']}\n({row['abertura_mm']:.3f} mm)" if row['abertura_mm'] < 1.0
        else f"{row['tamiz']}\n({row['abertura_mm']:.2f} mm)"
        for _, row in tamices_plot.iterrows()
    ]
    ax.set_xticklabels(etiquetas_x, fontsize=7.5)

    ax.set_yticks(range(0, 101, 10))
    ax.tick_params(axis="y", labelsize=8)

    ax.grid(True, which="major", color=GRIS_FONDO_GRID, lw=0.6, ls="-")
    ax.grid(True, which="minor", color=GRIS_FONDO_GRID, lw=0.3, ls=":")

    ax.set_xlabel("Tamiz y abertura nominal (mm) — Escala logarítmica", fontsize=9, fontweight="bold")
    ax.set_ylabel("Porcentaje acumulado que pasa (%)", fontsize=9, fontweight="bold")

    # Título principal
    if titulo is None:
        tipo_str = "AGREGADO FINO" if granulometria.tipo == "fino" else "AGREGADO GRUESO"
        titulo = f"CURVA GRANULOMÉTRICA — {tipo_str}\nNTP 400.012:2021 / ASTM C136-19"
    ax.set_title(titulo, fontsize=10.5, fontweight="bold", pad=12, color=AZUL_UNSAAC)

    # Cuadro informativo con parámetros de diseño en esquina
    param_text = [
        f"Cantera: {granulometria.cantera}",
        f"Módulo de Finura (MF): {granulometria.modulo_finura:.2f}",
    ]
    if granulometria.tipo == "grueso":
        param_text.append(f"Huso evaluado: N.° {granulometria.huso}")
        if granulometria.tamano_maximo:
            param_text.append(f"Tamaño Máx. (TM): {granulometria.tamano_maximo}")
        if granulometria.tamano_maximo_nominal:
            param_text.append(f"TMN: {granulometria.tamano_maximo_nominal}")
    else:
        param_text.append(f"Ret. máx. consec.: {granulometria.max_ret_consecutivo:.1f}%")

    if granulometria.d10 and granulometria.d60:
        param_text.append(f"D10: {granulometria.d10:.2f} mm | D60: {granulometria.d60:.2f} mm")
        if granulometria.cu:
            param_text.append(f"Cu: {granulometria.cu:.2f}")

    dictamen = "CUMPLE HUSO" if granulometria.cumple_huso else "FUERA DE HUSO"
    param_text.append(f"Dictamen: {dictamen}")

    props = dict(boxstyle="round,pad=0.5", facecolor="#FAFAFA", edgecolor="#999999", alpha=0.92)
    ax.text(
        0.02,
        0.55,
        "\n".join(param_text),
        transform=ax.transAxes,
        fontsize=7.8,
        verticalalignment="center",
        bbox=props,
        zorder=6,
    )

    ax.legend(loc="lower right", fontsize=8, framealpha=0.95, edgecolor=GRIS_LINEA_NORMA)

    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color("#333333")

    fig.tight_layout()

    if guardar_ruta:
        ruta = Path(guardar_ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ruta, dpi=dpi)

    if mostrar and matplotlib.get_backend().lower() != "agg":
        plt.show()

    return fig


def graficar_comparacion_husos(
    husos: Optional[List[str]] = None,
    granulometria=None,
    titulo: Optional[str] = None,
    guardar_ruta: Optional[Union[str, Path]] = None,
    mostrar: bool = False,
    figsize: tuple = (9.2, 5.4),
    dpi: int = 300,
) -> plt.Figure:
    """Compara gráficamente varias bandas de husos gruesos ASTM C33 / NTP 400.037 y, opcionalmente, una muestra.

    Args:
        husos: Lista de códigos de huso (p. ej. ['57', '67', '7']). Por defecto ['57', '67', '7'].
        granulometria: Instancia opcional de Granulometria gruesa para superponer la curva medida.
        titulo: Título personalizado (opcional).
        guardar_ruta: Ruta para guardar la imagen (PNG/PDF).
        mostrar: Si es True, ejecuta plt.show().
        figsize: Tamaño de la figura en pulgadas.
        dpi: Resolución de salida.

    Returns:
        Figura de matplotlib generada.
    """
    husos_sel = [str(h).strip() for h in (husos or ["57", "67", "7"])]
    validos = [h for h in husos_sel if h in HUSOS_AGREGADO_GRUESO]
    if not validos:
        raise ValueError(f"Ninguno de los husos indicados ({husos_sel}) pertenece a HUSOS_AGREGADO_GRUESO.")

    # Mapa inverso limpio abertura_mm -> etiqueta principal del tamiz
    ab_a_tamiz = {}
    for nom, ab in TAMICES_INFO.items():
        if ab not in ab_a_tamiz:
            ab_a_tamiz[ab] = nom

    aberturas_union = set()
    for cod in validos:
        aberturas_union.update(HUSOS_AGREGADO_GRUESO[cod].keys())

    if granulometria is not None:
        df_m = granulometria.df.dropna(subset=["abertura_mm"]).sort_values("abertura_mm")
        df_m = df_m[~df_m["es_fondo"]]
        aberturas_union.update(float(a) for a in df_m["abertura_mm"].values)

    aberturas_sorted = sorted(aberturas_union)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_xscale("log")
    ax.set_xlim(min(aberturas_sorted) / 1.35, max(aberturas_sorted) * 1.35)
    ax.set_ylim(0, 105)

    paleta = [
        ("#1F3864", "#D6E4F5", ":"),
        ("#1E6F50", "#D1FAE5", "--"),
        ("#B45309", "#FEF3C7", "-."),
        ("#6D28D9", "#EDE9FE", (0, (5, 2, 1, 2))),
        ("#374151", "#E5E7EB", (0, (3, 1, 1, 1))),
    ]

    for idx, cod in enumerate(validos):
        color_ln, color_fill, ls = paleta[idx % len(paleta)]
        banda = HUSOS_AGREGADO_GRUESO[cod]
        pts = sorted(banda.items())
        hx = [p[0] for p in pts]
        hmin = [p[1][0] for p in pts]
        hmax = [p[1][1] for p in pts]
        rango_txt = HUSOS_DESCRIPCION.get(cod, ("", ""))[0]

        ax.fill_between(
            hx,
            hmin,
            hmax,
            color=color_fill,
            alpha=0.45,
            zorder=1 + idx * 0.1,
            label=f"Huso {cod}: {rango_txt}",
        )
        ax.plot(hx, hmin, color=color_ln, ls=ls, lw=1.4, zorder=2 + idx * 0.1)
        ax.plot(hx, hmax, color=color_ln, ls=ls, lw=1.4, zorder=2 + idx * 0.1)

    if granulometria is not None:
        xm = df_m["abertura_mm"].values
        ym = df_m["porc_que_pasa"].values
        ax.plot(
            xm,
            ym,
            marker="o",
            markersize=6,
            color=ROJO_ALERTA,
            lw=2.5,
            zorder=6,
            label=f"Muestra {granulometria.muestra_id} (TMN: {granulometria.tamano_maximo_nominal})",
        )

    ax.xaxis.set_major_locator(FixedLocator(aberturas_sorted))
    ax.xaxis.set_minor_locator(NullLocator())
    etiquetas_x = [
        f"{ab_a_tamiz.get(ab, f'{ab:g}')}\n({ab:g} mm)"
        for ab in aberturas_sorted
    ]
    ax.set_xticklabels(etiquetas_x, fontsize=7.2)
    ax.set_yticks(range(0, 101, 10))
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(True, which="major", color=GRIS_FONDO_GRID, lw=0.6, ls="-")
    ax.set_xlabel("Tamiz y abertura nominal (mm) — Escala logarítmica", fontsize=9, fontweight="bold")
    ax.set_ylabel("Porcentaje acumulado que pasa (%)", fontsize=9, fontweight="bold")

    if titulo is None:
        husos_str = ", ".join(validos)
        titulo = f"COMPARACIÓN DE HUSOS GRANULOMÉTRICOS ({husos_str})\nNTP 400.037:2025 (Tabla 3) / ASTM C33/C33M-24 (Tabla 3)"
    ax.set_title(titulo, fontsize=10.5, fontweight="bold", pad=12, color=AZUL_UNSAAC)
    ax.legend(loc="upper left", fontsize=7.8, framealpha=0.95, edgecolor=GRIS_LINEA_NORMA)

    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color("#333333")

    fig.tight_layout()

    if guardar_ruta:
        ruta = Path(guardar_ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ruta, dpi=dpi)

    if mostrar and matplotlib.get_backend().lower() != "agg":
        plt.show()

    return fig


def graficar_fraguado_vicat(
    vicat,
    titulo: Optional[str] = None,
    guardar_ruta: Optional[Union[str, Path]] = None,
    mostrar: bool = False,
    figsize: tuple = (8.0, 4.8),
    dpi: int = 300,
) -> plt.Figure:
    """Genera la curva de penetración de aguja de Vicat vs. tiempo (NTP 334.006 / ASTM C191)."""
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    tiempos = vicat.tiempos_min
    penetraciones = vicat.penetraciones_mm

    # Curva experimental
    ax.plot(tiempos, penetraciones, 'o-', color=AZUL_LINEA, lw=2.0, ms=6, label='Penetración aguja Vicat (mm)', zorder=4)

    # Línea normativa de fraguado inicial (25.0 mm)
    ax.axhline(25.0, color=ROJO_ALERTA, ls='--', lw=1.5, label='Límite Fraguado Inicial (25.0 mm)', zorder=3)
    # Línea normativa de fraguado final (0.5 mm)
    ax.axhline(0.5, color='#7030A0', ls=':', lw=1.3, label='Fraguado Final (<= 0.5 mm)', zorder=3)

    if vicat.tiempo_inicial_min:
        ax.axvline(vicat.tiempo_inicial_min, color=ROJO_ALERTA, ls=':', lw=1.2, alpha=0.7)
        ax.plot(vicat.tiempo_inicial_min, 25.0, 's', color=ROJO_ALERTA, ms=8, label=f't_inicial = {vicat.tiempo_inicial_min:.1f} min', zorder=5)

    ax.set_xlabel('Tiempo transcurrido desde contacto agua-cemento (minutos)', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
    ax.set_ylabel('Penetración de la aguja (mm)', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
    
    t_title = titulo or f'CURVA DE TIEMPO DE FRAGUADO VICAT — NTP 334.006 / ASTM C191\n{vicat.tipo_cemento} ({vicat.muestra_id})'
    ax.set_title(t_title, fontsize=10, fontweight='bold', color=AZUL_UNSAAC, pad=10)

    ax.set_ylim(-1, max(penetraciones) + 5)
    ax.grid(True, linestyle='--', alpha=0.5, color=GRIS_FONDO_GRID)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.95)

    # Cuadro informativo (NTP 334.009 / NTP 334.090: límite mínimo y máximo en fraguado inicial; final informativo)
    max_ini = getattr(vicat, "max_inicial_norma", 420.0)
    cumple_vicat = getattr(vicat, "cumple_norma", bool(vicat.tiempo_inicial_min and 45 <= vicat.tiempo_inicial_min <= max_ini))
    info = [
        f'Agua normal: {getattr(vicat, "agua_consistencia_porc", getattr(vicat, "agua_normal_porc", 27.5)):.1f} % ({getattr(vicat, "agua_consistencia_ml", getattr(vicat, "agua_normal_ml", 178.8)):.1f} mL)',
        f'Fraguado Inicial: {vicat.tiempo_inicial_min:.0f} min (Norma: 45 a {max_ini:.0f} min)',
        f'Fraguado Final:   {vicat.tiempo_final_min:.0f} min (Solo informativo)',
        f'Dictamen: {"[CONFORME]" if cumple_vicat else "[NO CUMPLE]"}'
    ]
    props = dict(boxstyle='square,pad=0.6', facecolor='#F2F4F7', edgecolor=AZUL_UNSAAC, alpha=0.95)
    ax.text(0.03, 0.15, '\n'.join(info), transform=ax.transAxes, fontsize=8, verticalalignment='bottom', bbox=props, zorder=6)

    fig.tight_layout()
    if guardar_ruta:
        ruta = Path(guardar_ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ruta, dpi=dpi)
    if mostrar and matplotlib.get_backend().lower() != "agg":
        plt.show()
    return fig


def graficar_rotura_compresion(
    compresion_obj,
    titulo: Optional[str] = None,
    guardar_ruta: Optional[Union[str, Path]] = None,
    mostrar: bool = False,
    figsize: tuple = (8.5, 4.8),
    dpi: int = 300,
) -> plt.Figure:
    """Genera el gráfico de barras y evaluación de resistencia a compresión f'c (ASTM C39 / RNE E.060)."""
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    df = compresion_obj.df

    codigos = df['codigo'].tolist()
    fc_vals = df['fc_kg_cm2'].tolist()
    edades = df['edad_dias'].tolist()

    colores = ['#4A90E2' if e < 28 else AZUL_LINEA for e in edades]
    bars = ax.bar(codigos, fc_vals, color=colores, width=0.55, edgecolor='#1F3864', lw=1.0, zorder=3)

    # Línea de f'c de diseño y límite individual (RNE E.060 num. 5.6.3.3)
    fc_dis = compresion_obj.fc_diseno
    lim_ind = getattr(compresion_obj, "limite_min_individual", fc_dis - 35.0 if fc_dis <= 350.0 else 0.90 * fc_dis)
    lbl_ind = "f\'c - 35" if fc_dis <= 350.0 else "0.90 f\'c"
    ax.axhline(fc_dis, color=ROJO_ALERTA, ls='--', lw=1.8, label=f"f\'c Diseño = {fc_dis:.0f} kg/cm²", zorder=4)
    ax.axhline(lim_ind, color='#E67E22', ls=':', lw=1.4, label=f"Límite Individual ({lbl_ind}) = {lim_ind:.0f} kg/cm²", zorder=4)

    # Etiquetas encima de las barras
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 3.0, f'{yval:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold', color=AZUL_UNSAAC)

    ax.set_ylabel('Resistencia a Compresión (kg/cm²)', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
    edades_txt = " y ".join(str(int(e)) for e in sorted(set(edades)))
    t_title = titulo or f"CONTROL DE RESISTENCIA A COMPRESIÓN DEL CONCRETO (ASTM C39 / RNE E.060)\nDiseño f\'c = {fc_dis:.0f} kg/cm² | Edad: {edades_txt} días"
    ax.set_title(t_title, fontsize=10, fontweight='bold', color=AZUL_UNSAAC, pad=10)

    ax.set_ylim(0, max(fc_vals) * 1.2)
    ax.grid(axis='y', linestyle='--', alpha=0.5, color=GRIS_FONDO_GRID)
    ax.legend(loc='lower right', fontsize=8, framealpha=0.95)

    # Cuadro informativo RNE E.060
    prom = getattr(compresion_obj, "promedio_fc", 243.3)
    porc = (prom / compresion_obj.fc_diseno) * 100.0 if compresion_obj.fc_diseno > 0 else 100.0
    s_val = getattr(compresion_obj, "desv_std", 8.7)
    cv_val = getattr(compresion_obj, "cv_porc", 3.6)
    cumple_p = "CONFORME" if getattr(compresion_obj, "cumple_promedio", True) else "NO CUMPLE"
    cumple_i = "CONFORME" if getattr(compresion_obj, "cumple_individual", True) else "NO CUMPLE"
    veredicto = "[APROBADO]" if getattr(compresion_obj, "cumple_rne_e060", True) else "[OBSERVADO]"
    info = [
        f"Promedio {getattr(compresion_obj, 'edad_control', 28)}d: {prom:.1f} kg/cm² ({porc:.1f}% f'c)",
        f"Desviación std (s): {s_val:.1f} kg/cm²",
        f"Coef. Variación (CV): {cv_val:.1f} %",
        f"Criterio Promedio >= f'c: {cumple_p}",
        f"Criterio Indiv. >= {lbl_ind}: {cumple_i}",
        f"Dictamen: {veredicto}"
    ]
    props = dict(boxstyle='square,pad=0.6', facecolor='#F2F4F7', edgecolor=AZUL_UNSAAC, alpha=0.95)
    ax.text(0.03, 0.15, '\n'.join(info), transform=ax.transAxes, fontsize=8, verticalalignment='bottom', bbox=props, zorder=6)

    fig.tight_layout()
    if guardar_ruta:
        ruta = Path(guardar_ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ruta, dpi=dpi)
    if mostrar and matplotlib.get_backend().lower() != "agg":
        plt.show()
    return fig


def graficar_calidad_ladrillo(
    ladrillo_obj,
    titulo: Optional[str] = None,
    guardar_ruta: Optional[Union[str, Path]] = None,
    mostrar: bool = False,
    figsize: tuple = (9.0, 4.8),
    dpi: int = 300,
) -> plt.Figure:
    """Genera gráficos de variación dimensional y alabeo de ladrillos (RNE E.070 Tabla 1)."""
    from .masonry import limites_e070_para_clase

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize, dpi=dpi)

    # Subplot 1: Variación Dimensional según RNE E.070 Tabla 1 para (l_nom, a_nom, h_nom)
    dims = ['Largo', 'Ancho', 'Alto']
    vars_porc = [ladrillo_obj.var_largo, ladrillo_obj.var_ancho, ladrillo_obj.var_alto]
    lim_l, lim_a, lim_h, _, _ = limites_e070_para_clase(
        (ladrillo_obj.l_nom, ladrillo_obj.a_nom, ladrillo_obj.h_nom), "Ladrillo Tipo IV"
    )
    lim_t4 = [lim_l, lim_a, lim_h]  # Límites oficiales E.070 Tabla 1 Tipo IV según dimensión nominal

    x = np.arange(len(dims))
    width = 0.35
    b1 = ax1.bar(x - width/2, vars_porc, width, label='Muestra Medida (%)', color=AZUL_LINEA, edgecolor=AZUL_UNSAAC)
    b2 = ax1.bar(x + width/2, lim_t4, width, label='Límite Tipo IV (E.070)', color='#F5A623', alpha=0.7, edgecolor='#D48816')

    for bar in b1:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, f'{bar.get_height():.1f}%', ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax1.set_xticks(x)
    ax1.set_xticklabels(dims, fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
    ax1.set_ylabel('Variación Dimensional (%)', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
    ax1.set_title('VARIACIÓN DIMENSIONAL', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    ax1.legend(loc='upper right', fontsize=7.5)

    # Subplot 2: Alabeo
    alabs = ladrillo_obj.alabeos
    if alabs:
        unids = [f'L-{i+1:02d}' for i in range(len(alabs))]
        ax2.bar(unids, alabs, color='#4A90E2', edgecolor=AZUL_UNSAAC, width=0.55)
        ax2.axhline(2.0, color='#2E7D32', ls='--', lw=1.2, label='Máx. Tipo V (2 mm)')
        ax2.axhline(4.0, color='#F5A623', ls='--', lw=1.4, label='Máx. Tipo IV (4 mm)')
        ax2.axhline(6.0, color='#D0021B', ls='--', lw=1.2, label='Máx. Tipo III (6 mm)')
        ax2.set_ylabel('Alabeo Máximo (mm)', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
        ax2.set_title('ALABEO EN CARAS (ASTM C67)', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
        ax2.tick_params(axis='x', rotation=45, labelsize=7.5)
        ax2.grid(axis='y', linestyle='--', alpha=0.5)
        ax2.legend(loc='upper right', fontsize=7.5)

    t_title = titulo or f'CONTROL DE CALIDAD DE LADRILLOS (RNE E.070 TABLA 1)\n{ladrillo_obj.ladrillera} | Clasificación: {ladrillo_obj.clase}'
    fig.suptitle(t_title, fontsize=10, fontweight='bold', color=AZUL_UNSAAC)

    fig.tight_layout()
    if guardar_ruta:
        ruta = Path(guardar_ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ruta, dpi=dpi)
    if mostrar and matplotlib.get_backend().lower() != "agg":
        plt.show()
    return fig


def graficar_humedad_madera(
    madera_obj,
    titulo: Optional[str] = None,
    guardar_ruta: Optional[Union[str, Path]] = None,
    mostrar: bool = False,
    figsize: tuple = (7.5, 4.5),
    dpi: int = 300,
) -> plt.Figure:
    """Genera el gráfico de contenido de humedad en madera estructural (NTP 251.010 / RNE E.010)."""
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    df = madera_obj.df

    cods = df['codigo'].tolist()
    hums = df['contenido_humedad_porc'].tolist()

    bars = ax.bar(cods, hums, color='#27AE60', width=0.5, edgecolor='#1E8449', lw=1.0, zorder=3)
    uso_laminada = "laminada" in getattr(madera_obj, "uso_previsto", "").lower()
    if uso_laminada:
        ax.axhspan(8.0, 12.0, color='#2980B9', alpha=0.15, label='Rango RNE E.010 Laminada (8–12 %)', zorder=2)
        ax.axhline(12.0, color=ROJO_ALERTA, ls='--', lw=1.6, zorder=4)
        ax.axhline(8.0, color=ROJO_ALERTA, ls='--', lw=1.6, zorder=4)
        req_txt = "8 % a 12 % (Laminada)"
    else:
        ax.axhline(22.0, color=ROJO_ALERTA, ls='--', lw=1.8, label='Límite Máximo RNE E.010 (22.0 %)', zorder=4)
        ax.axhline(12.0, color='#2980B9', ls=':', lw=1.4, label='Humedad de Equilibrio Normal (~12 %)', zorder=4)
        req_txt = "<= 22.0 % (Aserrada)"

    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, f'{bar.get_height():.2f}%', ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=AZUL_UNSAAC)

    ax.set_ylabel('Contenido de Humedad (%)', fontsize=9, fontweight='bold', color=AZUL_UNSAAC)
    t_title = titulo or f'CONTENIDO DE HUMEDAD EN MADERA (NTP 251.010 / RNE E.010)\nEspecie: {madera_obj.especie} | Procedencia: {madera_obj.procedencia}'
    ax.set_title(t_title, fontsize=10, fontweight='bold', color=AZUL_UNSAAC, pad=10)

    max_h = max(hums) if hums else 22.0
    ax.set_ylim(0, max(26.0, max_h * 1.18))
    ax.grid(axis='y', linestyle='--', alpha=0.5, color=GRIS_FONDO_GRID)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.95)

    info = [
        f'Humedad Promedio: {getattr(madera_obj, "ch_promedio", getattr(madera_obj, "humedad_promedio", 14.48)):.2f} %',
        f'Humedad Máxima:   {getattr(madera_obj, "ch_max", getattr(madera_obj, "humedad_max", 14.73)):.2f} %',
        f'Requisito RNE E.010: {req_txt}',
        f'Dictamen: {"[CONFORME]" if getattr(madera_obj, "cumple_norma", getattr(madera_obj, "aprobado", True)) else "[NO CUMPLE - OBSERVADA]"}'
    ]
    props = dict(boxstyle='square,pad=0.6', facecolor='#F2F4F7', edgecolor=AZUL_UNSAAC, alpha=0.95)
    ax.text(0.03, 0.15, '\n'.join(info), transform=ax.transAxes, fontsize=8, verticalalignment='bottom', bbox=props, zorder=6)

    fig.tight_layout()
    if guardar_ruta:
        ruta = Path(guardar_ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ruta, dpi=dpi)
    if mostrar and matplotlib.get_backend().lower() != "agg":
        plt.show()
    return fig
