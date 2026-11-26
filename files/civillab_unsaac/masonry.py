"""Módulo de ensayos de albañilería estructural: ladrillos y prismas.

Implementa según normas verificadas en raw:
- Dimensionamiento, alabeo y clasificación de unidades (NTP 399.613 / RNE E.070 Tabla 1)
- Determinación de porcentaje de vacíos y clasificación sólido/hueco (RNE E.070 num. 5.3 / ASTM C67)
- Ensayo de compresión en unidades fb y absorción 24 h (ASTM C67 / RNE E.070 num. 5.4, 5.5)
- Ensayo de compresión en pilas/prismas fm (NTP 399.605 / ASTM C1314 / RNE E.070 Tablas 8, 9 y 10)
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


# RNE E.070 num. 5.2, Tabla 1:
# (clase, var_max_hasta_100mm, var_max_101_a_150mm, var_max_mas_150mm, alabeo_max_mm, fb_min_kg_cm2, desc)
RNE_E070_TABLA1: List[Tuple[str, float, float, float, float, float, str]] = [
    ("Ladrillo Tipo V", 3.0, 2.0, 1.0, 2.0, 180.0, "Máxima precisión geométrica"),
    ("Ladrillo Tipo IV", 4.0, 3.0, 2.0, 4.0, 130.0, "Uso estructural muros portantes sísmicos"),
    ("Ladrillo Tipo III", 5.0, 4.0, 3.0, 6.0, 95.0, "Uso estructural muros portantes"),
    ("Ladrillo Tipo II", 7.0, 6.0, 4.0, 8.0, 70.0, "Estructuras de baja carga"),
    ("Ladrillo Tipo I", 8.0, 6.0, 4.0, 10.0, 50.0, "Tabiquería / No portante"),
]


def _a_milimetros(dim: float) -> float:
    """Convierte dimensiones nominales en cm a mm si son < 50; valores >= 50 se asumen en mm."""
    return float(dim) * 10.0 if float(dim) < 50.0 else float(dim)


def limites_e070_para_clase(
    dim_nominales: Tuple[float, float, float],
    tipo: str = "Ladrillo Tipo IV",
) -> Tuple[float, float, float, float, float]:
    """Devuelve (lim_largo_%, lim_ancho_%, lim_alto_%, alabeo_max_mm, fb_min) según RNE E.070 Tabla 1."""
    fila = next((r for r in RNE_E070_TABLA1 if r[0].endswith(tipo) or r[0] == tipo), RNE_E070_TABLA1[1])
    _, lim_100, lim_150, lim_gt150, alabeo_max, fb_min, _ = fila

    def lim_dim(d_val: float) -> float:
        d_mm = _a_milimetros(d_val)
        if d_mm <= 100.0:
            return lim_100
        if d_mm <= 150.0:
            return lim_150
        return lim_gt150

    l_nom, a_nom, h_nom = dim_nominales
    return lim_dim(l_nom), lim_dim(a_nom), lim_dim(h_nom), alabeo_max, fb_min


class EnsayoVaciosLadrillo:
    """Ensayo de porcentaje de vacíos en unidades de albañilería (RNE E.070 num. 5.3 / ASTM C67)."""

    def __init__(
        self,
        muestras: List[Dict[str, float]],
        ladrillera: str = "Ladrillera en estudio",
        fecha: str = "2026-11-11",
    ):
        self.muestras = muestras
        self.ladrillera = ladrillera
        self.fecha = fecha
        self._procesar()

    def _procesar(self):
        filas = []
        for m in self.muestras:
            l = float(m["largo_cm"])
            a = float(m["ancho_cm"])
            h = float(m["alto_cm"])
            v_bruto = l * a * h
            v_neto = float(m["volumen_neto_cm3"])
            v_vacios = v_bruto - v_neto
            porc_vacios = (v_vacios / v_bruto) * 100.0 if v_bruto > 0 else 0.0

            tipo_seccion = "Sólida / Maciza" if porc_vacios <= 30.0 else "Hueca / Alveolar"

            filas.append({
                "codigo": m.get("codigo", "LAD-01"),
                "largo_cm": round(l, 2),
                "ancho_cm": round(a, 2),
                "alto_cm": round(h, 2),
                "vol_bruto_cm3": round(v_bruto, 1),
                "vol_neto_cm3": round(v_neto, 1),
                "vol_vacios_cm3": round(v_vacios, 1),
                "porc_vacios": round(porc_vacios, 1),
                "clasificacion_seccion": tipo_seccion,
            })

        self.df = pd.DataFrame(filas)
        self.vacios_promedio = round(float(self.df["porc_vacios"].mean()), 1)
        self.es_solido = bool(self.vacios_promedio <= 30.0)
        self.tipo_unidad = (
            "Unidad Sólida (Apta para muros portantes sísmicos)"
            if self.es_solido
            else "Unidad Hueca / Tubular (Prohibida en muros portantes según E.070 num. 5.3)"
        )

    def diagnostico_tecnico(self) -> str:
        return (
            f"=== ENSAYO DE PORCENTAJE DE VACÍOS (RNE E.070 num. 5.3 / ASTM C67) ===\n"
            f"Ladrillera: {self.ladrillera} | Unidades ensayadas: {len(self.df)}\n"
            f"• Porcentaje de vacíos promedio: {self.vacios_promedio:.1f} %\n"
            f"• Límite normativo para muros portantes: Máximo 30.0 % (Unidad Sólida)\n"
            f"DICTAMEN ESTRUCTURAL: {self.tipo_unidad}"
        )


class CompresionLadrilloUnidad:
    """Ensayo de compresión fb y absorción 24 h en unidades (NTP 399.613 / ASTM C67-23a / RNE E.070)."""

    def __init__(
        self,
        ensayos: List[Dict[str, float]],
        absorciones_datos: Optional[List[Dict[str, float]]] = None,
        tipo_produccion: str = "artesanal",
        ladrillera: str = "Ladrillera en estudio",
        fecha: str = "2026-11-11",
    ):
        """
        ensayos: lista de dicts con 'codigo', 'largo_cm', 'ancho_cm', 'carga_rotura_kgf' (o 'carga_kN'), 'refrentado'.
                 Opcionalmente 'area_sup_cm2' y 'area_inf_cm2'.
        absorciones_datos: lista opcional de dicts con 'codigo', 'w_seca_g' (Wd) y 'w_sat_g' (Ws tras 24h inmersión).
        tipo_produccion: 'industrial' (CV máx 20 %) o 'artesanal' (CV máx 40 %) según RNE E.070 num. 5.5 a).
        """
        self.ensayos = ensayos
        self.absorciones_datos = absorciones_datos or []
        self.tipo_produccion = tipo_produccion.lower().strip()
        self.ladrillera = ladrillera
        self.fecha = fecha
        self._procesar()

    def _procesar(self):
        filas = []
        for e in self.ensayos:
            l = float(e["largo_cm"])
            a = float(e["ancho_cm"])
            if "area_sup_cm2" in e and "area_inf_cm2" in e:
                area = (float(e["area_sup_cm2"]) + float(e["area_inf_cm2"])) / 2.0
            else:
                area = l * a

            if "carga_rotura_kgf" in e:
                carga = float(e["carga_rotura_kgf"])
            elif "carga_kN" in e:
                carga = float(e["carga_kN"]) * 101.97162
            else:
                carga = 0.0

            fb = carga / area if area > 0 else 0.0

            filas.append({
                "codigo": e.get("codigo", "LAD-01"),
                "largo_cm": round(l, 2),
                "ancho_cm": round(a, 2),
                "area_cm2": round(area, 1),
                "carga_kgf": round(carga, 1),
                "fb_kg_cm2": round(fb, 1),
                "fb_mpa": round(fb * 0.0980665, 2),
                "refrentado": e.get("refrentado", "Pasta de Yeso (<= 3 mm)"),
            })

        self.df = pd.DataFrame(filas)
        valores = self.df["fb_kg_cm2"].values
        self.fb_promedio = round(float(np.mean(valores)), 1)
        self.desv_std = round(float(np.std(valores, ddof=1)), 1) if len(valores) > 1 else 0.0
        self.cv_porc = round((self.desv_std / self.fb_promedio) * 100.0, 1) if self.fb_promedio > 0 else 0.0
        self.limite_cv = 20.0 if "industrial" in self.tipo_produccion else 40.0
        self.cumple_cv = self.cv_porc <= self.limite_cv

        # fb característico = promedio - desviación estándar (RNE E.070 num. 5.4 b)
        self.fb_caracteristico = round(self.fb_promedio - self.desv_std, 1)

        if self.fb_caracteristico >= 180.0:
            self.clase_resistencia = "Ladrillo Tipo V (f'b >= 180 kg/cm²)"
        elif self.fb_caracteristico >= 130.0:
            self.clase_resistencia = "Ladrillo Tipo IV (f'b >= 130 kg/cm²)"
        elif self.fb_caracteristico >= 95.0:
            self.clase_resistencia = "Ladrillo Tipo III (f'b >= 95 kg/cm²)"
        elif self.fb_caracteristico >= 70.0:
            self.clase_resistencia = "Ladrillo Tipo II (f'b >= 70 kg/cm²)"
        elif self.fb_caracteristico >= 50.0:
            self.clase_resistencia = "Ladrillo Tipo I (f'b >= 50 kg/cm²)"
        else:
            self.clase_resistencia = "No apto estructuralmente (f'b < 50 kg/cm²)"

        # Procesar absorción 24 h si se proporcionaron muestras (ASTM C67 num. 8.3.2 / E.070 num. 5.5 b)
        if self.absorciones_datos:
            abs_filas = []
            for item in self.absorciones_datos:
                wd = float(item["w_seca_g"])
                ws = float(item["w_sat_g"])
                ab = round(((ws - wd) / wd) * 100.0, 1) if wd > 0 else 0.0
                abs_filas.append({
                    "codigo": item.get("codigo", "ABS-01"),
                    "w_seca_g": wd,
                    "w_sat_24h_g": ws,
                    "absorcion_porc": ab,
                })
            self.df_absorcion = pd.DataFrame(abs_filas)
            self.absorcion_promedio = round(float(self.df_absorcion["absorcion_porc"].mean()), 1)
            self.cumple_absorcion = self.absorcion_promedio <= 22.0
        else:
            self.df_absorcion = None
            self.absorcion_promedio = None
            self.cumple_absorcion = None

    def diagnostico_tecnico(self) -> str:
        lineas = [
            f"=== COMPRESIÓN (f'b) Y ABSORCIÓN DE LA UNIDAD (ASTM C67 / RNE E.070) ===",
            f"Ladrillera: {self.ladrillera} | Producción: {self.tipo_produccion.capitalize()} | Especímenes: {len(self.df)}",
            f"• Resistencia promedio (f_b): {self.fb_promedio:.1f} kg/cm² | Desviación std (s): {self.desv_std:.1f} kg/cm²",
            f"• Resistencia característica f'b = f_b - s (E.070 num. 5.4 b): {self.fb_caracteristico:.1f} kg/cm² ({self.fb_caracteristico*0.0980665:.1f} MPa)",
            f"• Coeficiente de variación (CV): {self.cv_porc:.1f} % (Límite {self.tipo_produccion}: <= {self.limite_cv:.0f} % según E.070 num. 5.5 a): "
            + ("CONFORME" if self.cumple_cv else "EXCEDE DISPERSIÓN"),
            f"• CLASIFICACIÓN POR RESISTENCIA: {self.clase_resistencia}",
        ]
        if self.absorcion_promedio is not None:
            lineas.append(
                f"• Absorción promedio 24 h (E.070 num. 5.5 b): {self.absorcion_promedio:.1f} % (Máx. 22.0 %): "
                + ("CONFORME" if self.cumple_absorcion else "RECHAZADO (> 22 %)")
            )
        return "\n".join(lineas)


class LadrilloCalidad:
    """Evaluación integral de variación dimensional y alabeo de ladrillos (RNE E.070 Tabla 1)."""

    def __init__(
        self,
        dimensiones_medidas: List[Dict[str, float]],
        dim_nominales: Tuple[float, float, float] = (24.0, 13.0, 9.0),
        alabeos_mm: Optional[List[float]] = None,
        absorciones_porc: Optional[List[float]] = None,
        porc_vacios: Optional[float] = None,
        fb_caracteristico: Optional[float] = None,
        tipo_ladrillo: str = "Arcilla cocida",
        ladrillera: str = "Ladrillera en estudio",
        fecha: str = "2026-11-11",
    ):
        self.datos = dimensiones_medidas
        self.l_nom, self.a_nom, self.h_nom = dim_nominales
        self.alabeos = alabeos_mm or []
        self.absorciones = absorciones_porc or []
        self.porc_vacios = porc_vacios
        self.fb_caracteristico = fb_caracteristico
        self.tipo_ladrillo = tipo_ladrillo
        self.ladrillera = ladrillera
        self.fecha = fecha

        self._procesar()

    def _procesar(self):
        df_m = pd.DataFrame(self.datos)
        self.n_unidades = len(df_m)

        self.largo_prom = round(float(df_m["largo"].mean()), 2)
        self.ancho_prom = round(float(df_m["ancho"].mean()), 2)
        self.alto_prom = round(float(df_m["alto"].mean()), 2)

        self.var_largo = round(abs(self.largo_prom - self.l_nom) / self.l_nom * 100.0, 1)
        self.var_ancho = round(abs(self.ancho_prom - self.a_nom) / self.a_nom * 100.0, 1)
        self.var_alto = round(abs(self.alto_prom - self.h_nom) / self.h_nom * 100.0, 1)

        self.alabeo_max = round(float(np.max(self.alabeos)), 1) if self.alabeos else 0.0
        self.absorcion_prom = round(float(np.mean(self.absorciones)), 1) if self.absorciones else None

        # RNE E.070 num. 5.2, Tabla 1: variación dimensional según tramo (<=100, 101-150, >150 mm) y alabeo
        dims = (self.l_nom, self.a_nom, self.h_nom)
        self.clase_geometrica = "No clasifica / Descarte"
        self.clase = "No clasifica / Descarte"
        for nombre_tipo, _, _, _, _, fb_min, desc in RNE_E070_TABLA1:
            lim_l, lim_a, lim_h, lim_alabeo, _ = limites_e070_para_clase(dims, nombre_tipo)
            cumple_geom = (
                self.var_largo <= lim_l
                and self.var_ancho <= lim_a
                and self.var_alto <= lim_h
                and self.alabeo_max <= lim_alabeo
            )
            if cumple_geom and self.clase_geometrica == "No clasifica / Descarte":
                self.clase_geometrica = f"{nombre_tipo} ({desc})"
            cumple_fb = self.fb_caracteristico is None or self.fb_caracteristico >= fb_min
            if cumple_geom and cumple_fb:
                self.clase = f"{nombre_tipo} ({desc})"
                break

    def diagnostico_tecnico(self) -> str:
        res = (
            f"=== EVALUACIÓN GEOMÉTRICA DE LADRILLOS (RNE E.070 TABLA 1) ===\n"
            f"Ladrillera: {self.ladrillera} | Unidades ensayadas: {self.n_unidades}\n"
            f"Dimensiones Nominales: {self.l_nom} x {self.a_nom} x {self.h_nom} cm\n"
            f"Dimensiones Promedio:  {self.largo_prom:.2f} x {self.ancho_prom:.2f} x {self.alto_prom:.2f} cm\n"
            f"• Variación de Largo: {self.var_largo:.1f} % | Ancho: {self.var_ancho:.1f} % | Alto: {self.var_alto:.1f} %\n"
            f"• Alabeo máximo medido: {self.alabeo_max:.1f} mm\n"
        )
        if self.absorcion_prom is not None:
            res += f"• Absorción promedio: {self.absorcion_prom:.1f} % (Exigencia <= 22 % E.070 num. 5.5 b)\n"
        if self.porc_vacios is not None:
            estado_v = "SÓLIDA (<= 30%)" if self.porc_vacios <= 30 else "HUECA (> 30%)"
            res += f"• Porcentaje de vacíos: {self.porc_vacios:.1f} % -> {estado_v}\n"
        if self.fb_caracteristico is not None:
            res += f"• Resistencia característica f'b: {self.fb_caracteristico:.1f} kg/cm²\n"
        res += f"\nCLASIFICACIÓN GEOMÉTRICA E.070: {self.clase}"
        return res


class CompresionPrismasMortero:
    """Ensayo de compresión en pilas de albañilería fm (NTP 399.605 / ASTM C1314 / RNE E.070 Tablas 8, 9 y 10)."""

    def __init__(
        self,
        pilas: List[Dict[str, float]],
        mortero_tipo: str = "P2 (1:4 cemento-arena)",
        edad_dias: int = 28,
        fb_unidad: Optional[float] = None,
        fecha: str = "2026-11-11",
    ):
        self.pilas = pilas
        self.mortero = mortero_tipo
        self.edad_dias = int(edad_dias)
        self.fb_unidad = float(fb_unidad) if fb_unidad is not None else None
        self.fecha = fecha
        self._procesar()

    def _factor_esbeltez_e070(self, ht: float) -> float:
        """Factor de corrección por esbeltez h/t exacto según RNE E.070 num. 13.9, Tabla 10."""
        xp = [2.0, 2.5, 3.0, 4.0, 4.5, 5.0]
        fp = [0.73, 0.80, 0.91, 0.95, 0.98, 1.00]
        return float(np.interp(ht, xp, fp))

    def _factor_edad_e070(self, dias: int) -> float:
        """Factor de corrección por edad en pilas de arcilla (RNE E.070 num. 13.6, Tabla 8)."""
        if dias <= 14:
            return 1.10
        return 1.00

    def _procesar(self):
        filas = []
        factor_edad = self._factor_edad_e070(self.edad_dias)
        for p in self.pilas:
            h = float(p.get("altura_cm", 28.0))
            t = float(p.get("espesor_cm", 13.0))
            ancho = float(p.get("ancho_cm", 24.0))
            carga = float(p.get("carga_kgf", 15000.0))
            edad_p = int(p.get("edad_dias", self.edad_dias))
            f_edad = self._factor_edad_e070(edad_p)

            area_cm2 = ancho * t
            esbeltez = h / t if t > 0 else 2.0
            factor_esb = self._factor_esbeltez_e070(esbeltez)

            esfuerzo_bruto = carga / area_cm2 if area_cm2 > 0 else 0.0
            fm_corregido = esfuerzo_bruto * factor_esb * f_edad

            filas.append({
                "codigo": p.get("codigo", "PILA-01"),
                "edad_dias": edad_p,
                "altura_cm": round(h, 1),
                "espesor_t_cm": round(t, 1),
                "ancho_b_cm": round(ancho, 1),
                "area_cm2": round(area_cm2, 1),
                "esbeltez_ht": round(esbeltez, 2),
                "factor_esbeltez_E070": round(factor_esb, 3),
                "factor_edad_E070": round(f_edad, 2),
                "carga_kgf": round(carga, 1),
                "esfuerzo_bruto_kg_cm2": round(esfuerzo_bruto, 1),
                "fm_corregido_kg_cm2": round(fm_corregido, 1),
                "fm_corregido_mpa": round(fm_corregido * 0.0980665, 2),
            })

        self.df = pd.DataFrame(filas)
        valores = self.df["fm_corregido_kg_cm2"].values
        self.fm_promedio = round(float(np.mean(valores)), 1)
        self.desv_std = round(float(np.std(valores, ddof=1)), 1) if len(valores) > 1 else 0.0
        # f'm característico según RNE E.070 num. 13.7 = promedio - desviación estándar
        self.fm_caracteristico = round(self.fm_promedio - self.desv_std, 1)
        self.relacion_fm_fb_porc = (
            round((self.fm_caracteristico / self.fb_unidad) * 100.0, 1)
            if self.fb_unidad and self.fb_unidad > 0
            else None
        )

    def diagnostico_tecnico(self) -> str:
        lineas = [
            f"=== COMPRESIÓN DE PILAS DE ALBAÑILERÍA (f'm) — RNE E.070 / ASTM C1314 ===",
            f"Mortero: {self.mortero} | Edad: {self.edad_dias} días | Pilas ensayadas: {len(self.df)}",
            f"Refrentado normativo: Cemento-yeso de alta resistencia (<= 3 mm, ASTM C1552)",
            f"• Resistencia promedio corregida (E.070 Tablas 8 y 10): {self.fm_promedio:.1f} kg/cm² ({self.fm_promedio * 0.0980665:.2f} MPa)",
            f"• Desviación estándar (s): {self.desv_std:.1f} kg/cm²",
            f"• Resistencia característica f'm (RNE E.070 num. 13.7): {self.fm_caracteristico:.1f} kg/cm² ({self.fm_caracteristico * 0.0980665:.2f} MPa)",
        ]
        if self.relacion_fm_fb_porc is not None:
            lineas.append(f"• Relación f'm / f'b: {self.relacion_fm_fb_porc:.1f} % (Referencia histórica ITINTEC 331.017:1978: 25 % a 50 %; vigente NTP 331.017:2003 rev. 2015)")
        lineas.append("• Referencia E.070 Tabla 9 (arcilla 1:4): KK Artesanal = 35 kg/cm² | KK Industrial = 65 kg/cm² | Rejilla = 85 kg/cm²")
        return "\n".join(lineas)
