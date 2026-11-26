"""Módulo de diseño de mezclas de concreto de peso normal.

Implementa el procedimiento de ACI PRC-211.1-22, capítulo 5 (pasos 1 a 9):
- Paso 3: agua de mezclado y aire (Tabla 5.3.3) y ajustes de agua (Tabla 5.3.3.1)
- Paso 4: relación agua/material cementante (Tabla 5.3.4)
- Paso 5: contenido de cemento
- Paso 6: agregado grueso (Tabla 5.3.6)
- Paso 7: agregado fino por volúmenes absolutos
- Paso 8: resumen de pesos de diseño (condición SSS)
- Corrección por humedad de los agregados (num. 4.7.8) y pesos por tanda

La resistencia promedio requerida f'cr, cuando no hay registro de ensayos,
se toma del RNE E.060, Tabla 5.3 (num. 5.3.2.2).

La norma ACI PRC-211.1-22 está en unidades de pulgada-libra. El cálculo se hace
en esas unidades, con los valores de sus tablas, y los resultados se convierten
a kg/m³ y kg/cm². Así, el ejemplo 9.2 de la norma se reproduce sin diferencias.

Criterios propios (no están escritos en la norma):
- La relación a/mc interpolada se trunca a dos decimales (lado conservador);
  el ejemplo 9.2 pasa de 0,625 a 0,62.
- En la Tabla 5.3.6 se interpola linealmente entre módulos de finura.
- Para asentamientos intermedios se usa la fila del rango inmediato superior
  (p. ej., 2,5 pulg usa la fila «3 a 4»).
"""

import math
from typing import Dict, Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Conversión de unidades
# ---------------------------------------------------------------------------
LB_YD3_A_KG_M3 = 0.45359237 / 0.764554857984      # 0,593276
LB_FT3_A_KG_M3 = 0.45359237 / 0.028316846592      # 16,01846
PSI_A_KG_CM2 = 0.0703069579640
MPA_A_KG_CM2 = 10.1971621298
DENSIDAD_AGUA_LB_FT3 = 62.4                        # valor usado en ACI PRC-211.1-22, cap. 9
FT3_POR_YD3 = 27.0
MASA_BOLSA_CEMENTO_KG = 42.5

# ---------------------------------------------------------------------------
# Tablas de ACI PRC-211.1-22
# ---------------------------------------------------------------------------
TMN_VALIDOS = ("3/8", "1/2", "3/4", "1", "1-1/2", "2", "3")
_TMN_ALIAS = {
    '3/8"': "3/8", "9.5": "3/8", "9,5": "3/8",
    '1/2"': "1/2", "12.5": "1/2", "12,5": "1/2",
    '3/4"': "3/4", "19": "3/4", "19.0": "3/4",
    '1"': "1", "25": "1", "25.0": "1",
    '1 1/2"': "1-1/2", "1 1/2": "1-1/2", "1-1/2\"": "1-1/2", "1.5": "1-1/2", "37.5": "1-1/2", "37,5": "1-1/2",
    '2"': "2", "50": "2",
    '3"': "3", "75": "3",
}

# Tabla 5.3.3 — agua de mezclado, lb/yd³, por rango de asentamiento (pulg) y TMN
# Filas: límite superior del rango de asentamiento.
AGUA_SIN_AIRE_LB_YD3 = {
    2.0: (350, 335, 315, 300, 275, 260, 220),   # 1 a 2
    4.0: (385, 365, 340, 325, 300, 285, 245),   # 3 a 4
    6.0: (400, 375, 350, 330, 305, 290, 255),   # 5 a 6
    7.0: (410, 385, 360, 340, 315, 300, 270),   # 6 a 7
}
AGUA_CON_AIRE_LB_YD3 = {
    2.0: (305, 295, 280, 270, 250, 240, 205),
    4.0: (340, 325, 305, 295, 275, 265, 225),
    6.0: (355, 335, 315, 300, 280, 270, 240),
    7.0: (365, 345, 325, 310, 290, 280, 260),
}
# Tabla 5.3.3 — aire, %
AIRE_ATRAPADO_PCT = (3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.3)
AIRE_TOTAL_PCT = {
    "F1": (6.0, 5.5, 5.0, 4.5, 4.5, 4.0, 3.5),
    "F2": (7.5, 7.0, 6.0, 6.0, 5.5, 5.0, 4.5),
    "F3": (7.5, 7.0, 6.0, 6.0, 5.5, 5.0, 4.5),
}

# Tabla 5.3.3.1 — ajustes del agua estimada, %
AJUSTE_AGREGADO_REDONDEADO_PCT = -8.0
AJUSTE_ARENA_MANUFACTURADA_PCT = 5.0
AJUSTE_REDUCTOR_AGUA_PCT = -5.0
AJUSTE_REDUCTOR_ALTO_RANGO_PCT = -12.0

# Tabla 5.3.4 — relación a/mc en peso según la resistencia a 28 días, psi
WCM_SIN_AIRE = ((2000, 0.82), (3000, 0.68), (4000, 0.57), (5000, 0.48), (6000, 0.41), (7000, 0.34))
WCM_CON_AIRE = ((2000, 0.74), (3000, 0.59), (4000, 0.48), (5000, 0.40), (6000, 0.33))

# Tabla 5.3.6 — volumen de agregado grueso seco y compactado por unidad de volumen de concreto
MF_TABLA = (2.40, 2.60, 2.80, 3.00)
VOLUMEN_GRUESO = {
    "3/8": (0.50, 0.48, 0.46, 0.44),
    "1/2": (0.59, 0.57, 0.55, 0.53),
    "3/4": (0.66, 0.64, 0.62, 0.60),
    "1": (0.71, 0.69, 0.67, 0.65),
    "1-1/2": (0.75, 0.73, 0.71, 0.69),
    "2": (0.78, 0.76, 0.74, 0.72),
    "3": (0.82, 0.80, 0.78, 0.76),
}


def resistencia_promedio_requerida_e060(fc_kg_cm2: float) -> float:
    """f'cr sin registro de ensayos, RNE E.060 Tabla 5.3 (num. 5.3.2.2). Entrada y salida en kg/cm².

    La tabla está en MPa (f'c < 21: +7,0; 21 a 35: +8,5; > 35: 1,1 f'c + 5,0). Se aplica con la
    equivalencia nominal 1 MPa = 10 kg/cm², de modo que f'c = 210 kg/cm² corresponde a 21 MPa.
    """
    fc = float(fc_kg_cm2)
    if fc < 210.0:
        return fc + 70.0
    if fc <= 350.0:
        return fc + 85.0
    return 1.1 * fc + 50.0


def _interpolar(x: float, puntos) -> float:
    for (x0, y0), (x1, y1) in zip(puntos[:-1], puntos[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError("valor fuera de la tabla")


class DisenoMezclaACI211:
    """Diseño de mezcla de concreto de peso normal según ACI PRC-211.1-22.

    Parámetros principales (unidades del laboratorio):
        fc_kg_cm2: resistencia especificada f'c.
        asentamiento_pulg: asentamiento de diseño (1 a 7 pulg).
        tmn: tamaño máximo nominal del agregado grueso ("3/8", "1/2", "3/4", "1", "1-1/2", "2", "3").
        modulo_finura: módulo de finura del agregado fino (2,40 a 3,00).
        puc_grueso_kg_m3: peso unitario compactado seco del agregado grueso (ASTM C29).
        g_sss_grueso, g_sss_fino: peso específico saturado con superficie seca (ASTM C127 / C128).
        abs_grueso_pct, abs_fino_pct: absorción, %.
        humedad_grueso_pct, humedad_fino_pct: humedad total (ASTM C566), %. Si se omiten, no se corrige.
        pe_cemento: peso específico del cemento (dato del fabricante; 3,15 es el del ejemplo de la norma).
        aire_incorporado: True si el concreto lleva aire incorporado; `exposicion` = "F1", "F2" o "F3".
        fcr_kg_cm2: resistencia promedio requerida; si se omite, RNE E.060 Tabla 5.3.
        wcm_max: relación a/mc máxima por durabilidad, si la hay.
    """

    def __init__(
        self,
        fc_kg_cm2: float,
        asentamiento_pulg: float,
        tmn: str,
        modulo_finura: float,
        puc_grueso_kg_m3: float,
        g_sss_grueso: float,
        abs_grueso_pct: float,
        g_sss_fino: float,
        abs_fino_pct: float,
        humedad_grueso_pct: Optional[float] = None,
        humedad_fino_pct: Optional[float] = None,
        pe_cemento: float = 3.15,
        aire_incorporado: bool = False,
        exposicion: str = "F1",
        fcr_kg_cm2: Optional[float] = None,
        wcm_max: Optional[float] = None,
        agregado_redondeado: bool = False,
        arena_manufacturada: bool = False,
        reductor_agua: Optional[str] = None,
        descripcion: str = "",
    ):
        self.fc = float(fc_kg_cm2)
        self.asentamiento_pulg = float(asentamiento_pulg)
        self.tmn = self._normalizar_tmn(tmn)
        self.mf = float(modulo_finura)
        self.puc_grueso = float(puc_grueso_kg_m3)
        self.g_sss_grueso = float(g_sss_grueso)
        self.abs_grueso = float(abs_grueso_pct)
        self.g_sss_fino = float(g_sss_fino)
        self.abs_fino = float(abs_fino_pct)
        self.hum_grueso = None if humedad_grueso_pct is None else float(humedad_grueso_pct)
        self.hum_fino = None if humedad_fino_pct is None else float(humedad_fino_pct)
        self.pe_cemento = float(pe_cemento)
        self.aire_incorporado = bool(aire_incorporado)
        self.exposicion = exposicion.upper()
        self.wcm_max = None if wcm_max is None else float(wcm_max)
        self.agregado_redondeado = bool(agregado_redondeado)
        self.arena_manufacturada = bool(arena_manufacturada)
        self.reductor_agua = reductor_agua
        self.descripcion = descripcion

        if fcr_kg_cm2 is None:
            self.fcr = resistencia_promedio_requerida_e060(self.fc)
            self.origen_fcr = "RNE E.060, Tabla 5.3"
        else:
            self.fcr = float(fcr_kg_cm2)
            self.origen_fcr = "dato del usuario"

        self._validar()
        self._calcular()

    # ------------------------------------------------------------------
    @staticmethod
    def _normalizar_tmn(tmn) -> str:
        s = str(tmn).strip().replace("”", '"').replace("pulg", "").strip()
        s = _TMN_ALIAS.get(s, s)
        if s not in TMN_VALIDOS:
            raise ValueError(f"TMN «{tmn}» no está en la Tabla 5.3.3 de ACI PRC-211.1-22. Use uno de: {', '.join(TMN_VALIDOS)}.")
        return s

    def _validar(self):
        if not 1.0 <= self.asentamiento_pulg <= 7.0:
            raise ValueError("La Tabla 5.3.3 cubre asentamientos de 1 a 7 pulg; sobre 7 pulg se requiere aditivo reductor de agua.")
        if not MF_TABLA[0] <= self.mf <= MF_TABLA[-1]:
            raise ValueError("La Tabla 5.3.6 cubre módulos de finura de 2,40 a 3,00.")
        if self.aire_incorporado and self.exposicion not in AIRE_TOTAL_PCT:
            raise ValueError("Con aire incorporado, la exposición debe ser F1, F2 o F3.")
        if self.reductor_agua not in (None, "WRA", "HRWRA"):
            raise ValueError("reductor_agua debe ser None, 'WRA' o 'HRWRA'.")
        for nombre, valor in (("PUC del grueso", self.puc_grueso), ("G_SSS del grueso", self.g_sss_grueso),
                              ("G_SSS del fino", self.g_sss_fino), ("peso específico del cemento", self.pe_cemento)):
            if valor <= 0:
                raise ValueError(f"El {nombre} debe ser mayor que cero.")

    # ------------------------------------------------------------------
    def _calcular(self):
        i = TMN_VALIDOS.index(self.tmn)

        # Paso 3 — agua y aire (Tabla 5.3.3)
        tabla = AGUA_CON_AIRE_LB_YD3 if self.aire_incorporado else AGUA_SIN_AIRE_LB_YD3
        limite = next(l for l in sorted(tabla) if self.asentamiento_pulg <= l)
        self.rango_asentamiento = {2.0: "1 a 2", 4.0: "3 a 4", 6.0: "5 a 6", 7.0: "6 a 7"}[limite]
        agua_tabla = float(tabla[limite][i])
        self.ajuste_agua_pct = 0.0
        if self.agregado_redondeado:
            self.ajuste_agua_pct += AJUSTE_AGREGADO_REDONDEADO_PCT
        if self.arena_manufacturada:
            self.ajuste_agua_pct += AJUSTE_ARENA_MANUFACTURADA_PCT
        if self.reductor_agua == "WRA":
            self.ajuste_agua_pct += AJUSTE_REDUCTOR_AGUA_PCT
        elif self.reductor_agua == "HRWRA":
            self.ajuste_agua_pct += AJUSTE_REDUCTOR_ALTO_RANGO_PCT
        agua = round(agua_tabla * (1 + self.ajuste_agua_pct / 100.0))
        self.aire_pct = AIRE_TOTAL_PCT[self.exposicion][i] if self.aire_incorporado else AIRE_ATRAPADO_PCT[i]

        # Paso 4 — relación a/mc (Tabla 5.3.4)
        fcr_psi = self.fcr / PSI_A_KG_CM2
        puntos = WCM_CON_AIRE if self.aire_incorporado else WCM_SIN_AIRE
        if not puntos[0][0] <= fcr_psi <= puntos[-1][0]:
            raise ValueError(
                f"f'cr = {self.fcr:.0f} kg/cm² ({fcr_psi:.0f} psi) está fuera de la Tabla 5.3.4 "
                f"({puntos[0][0]} a {puntos[-1][0]} psi)."
            )
        wcm_resistencia = math.floor(_interpolar(fcr_psi, puntos) * 100 + 1e-9) / 100
        self.wcm_resistencia = wcm_resistencia
        self.wcm = min(wcm_resistencia, self.wcm_max) if self.wcm_max else wcm_resistencia
        self.gobierna = "durabilidad" if self.wcm < wcm_resistencia else "resistencia"

        # Paso 5 — cemento
        cemento = round(agua / self.wcm)

        # Paso 6 — agregado grueso (Tabla 5.3.6)
        self.b_b0 = _interpolar(self.mf, tuple(zip(MF_TABLA, VOLUMEN_GRUESO[self.tmn])))
        puc_lb_ft3 = self.puc_grueso / LB_FT3_A_KG_M3
        grueso_seco = round(self.b_b0 * puc_lb_ft3 * FT3_POR_YD3)
        grueso_sss = round(grueso_seco * (1 + self.abs_grueso / 100.0))

        # Paso 7 — agregado fino por volúmenes absolutos
        v_agua = agua / DENSIDAD_AGUA_LB_FT3
        v_cemento = cemento / (self.pe_cemento * DENSIDAD_AGUA_LB_FT3)
        v_grueso = grueso_sss / (self.g_sss_grueso * DENSIDAD_AGUA_LB_FT3)
        v_aire = self.aire_pct / 100.0 * FT3_POR_YD3
        v_fino = FT3_POR_YD3 - (v_agua + v_cemento + v_grueso + v_aire)
        if v_fino <= 0:
            raise ValueError("El volumen de agregado fino resulta nulo o negativo: revise los datos de entrada.")
        fino_sss = round(v_fino * self.g_sss_fino * DENSIDAD_AGUA_LB_FT3)

        self._lb_yd3 = {"agua": agua, "cemento": cemento, "grueso_seco": grueso_seco,
                        "grueso_sss": grueso_sss, "fino_sss": fino_sss}
        self._vol_ft3 = {"agua": v_agua, "cemento": v_cemento, "grueso": v_grueso, "aire": v_aire, "fino": v_fino}

        # Paso 8 — resumen en kg/m³ (condición SSS)
        k = LB_YD3_A_KG_M3
        self.agua = agua * k
        self.cemento = cemento * k
        self.grueso_sss = grueso_sss * k
        self.fino_sss = fino_sss * k
        self.bolsas_por_m3 = self.cemento / MASA_BOLSA_CEMENTO_KG
        self.densidad_teorica = self.agua + self.cemento + self.grueso_sss + self.fino_sss

        # Corrección por humedad (num. 4.7.8)
        self.corregido = self.hum_grueso is not None and self.hum_fino is not None
        if self.corregido:
            grueso_h = round(grueso_sss * (1 + self.hum_grueso / 100.0) / (1 + self.abs_grueso / 100.0))
            fino_h = round(fino_sss * (1 + self.hum_fino / 100.0) / (1 + self.abs_fino / 100.0))
            agua_libre = (grueso_h - grueso_sss) + (fino_h - fino_sss)
            agua_h = agua - agua_libre
            self._lb_yd3.update({"grueso_humedo": grueso_h, "fino_humedo": fino_h,
                                 "agua_libre": agua_libre, "agua_tanda": agua_h})
            self.grueso_humedo = grueso_h * k
            self.fino_humedo = fino_h * k
            self.agua_libre = agua_libre * k
            self.agua_tanda = agua_h * k

    # ------------------------------------------------------------------
    def tabla_diseno(self) -> pd.DataFrame:
        """Pesos y volúmenes absolutos por m³ de concreto, agregados en condición SSS (paso 8)."""
        v = {k: x / FT3_POR_YD3 for k, x in self._vol_ft3.items()}
        filas = [
            ("Agua de mezclado", self.agua, v["agua"]),
            ("Cemento", self.cemento, v["cemento"]),
            ("Agregado grueso (SSS)", self.grueso_sss, v["grueso"]),
            ("Agregado fino (SSS)", self.fino_sss, v["fino"]),
            ("Aire", 0.0, v["aire"]),
        ]
        df = pd.DataFrame(filas, columns=["Material", "Peso (kg/m³)", "Volumen absoluto (m³)"])
        total = pd.DataFrame([("Total", df["Peso (kg/m³)"].sum(), df["Volumen absoluto (m³)"].sum())], columns=df.columns)
        df = pd.concat([df, total], ignore_index=True)
        df["Peso (kg/m³)"] = df["Peso (kg/m³)"].round(0)
        df["Volumen absoluto (m³)"] = df["Volumen absoluto (m³)"].round(4)
        return df

    def _pesos_obra(self) -> Dict[str, float]:
        if self.corregido:
            return {"Agua": self.agua_tanda, "Cemento": self.cemento,
                    "Agregado grueso (húmedo)": self.grueso_humedo, "Agregado fino (húmedo)": self.fino_humedo}
        return {"Agua": self.agua, "Cemento": self.cemento,
                "Agregado grueso (SSS)": self.grueso_sss, "Agregado fino (SSS)": self.fino_sss}

    def tabla_corregida(self) -> pd.DataFrame:
        """Pesos por m³ corregidos por la humedad de los agregados (num. 4.7.8)."""
        if not self.corregido:
            raise ValueError("Indique humedad_grueso_pct y humedad_fino_pct para corregir por humedad.")
        filas = [
            ("Agua", self.agua, self.agua_tanda),
            ("Cemento", self.cemento, self.cemento),
            ("Agregado grueso", self.grueso_sss, self.grueso_humedo),
            ("Agregado fino", self.fino_sss, self.fino_humedo),
        ]
        df = pd.DataFrame(filas, columns=["Material", "Diseño SSS (kg/m³)", "Corregido por humedad (kg/m³)"])
        total = pd.DataFrame([("Total", df.iloc[:, 1].sum(), df.iloc[:, 2].sum())], columns=df.columns)
        return pd.concat([df, total], ignore_index=True).round(0)

    def tanda(self, volumen_litros: float) -> pd.DataFrame:
        """Pesos para una tanda de prueba del volumen indicado (litros), con la corrección por humedad si hay datos."""
        if volumen_litros <= 0:
            raise ValueError("El volumen de la tanda debe ser mayor que cero.")
        f = volumen_litros / 1000.0
        filas = [(m, round(p * f, 2)) for m, p in self._pesos_obra().items()]
        return pd.DataFrame(filas, columns=["Material", f"Peso para {volumen_litros:g} L (kg)"])

    def proporcion_en_peso(self) -> str:
        """Proporción cemento : fino : grueso / agua por kg de cemento, con los pesos de obra."""
        p = self._pesos_obra()
        valores = list(p.values())
        agua, cemento, grueso, fino = valores[0], valores[1], valores[2], valores[3]
        return f"1 : {fino / cemento:.2f} : {grueso / cemento:.2f} / {agua / cemento:.2f}"

    def diagnostico_tecnico(self) -> str:
        tipo_aire = f"incorporado, exposición {self.exposicion}" if self.aire_incorporado else "atrapado"
        lineas = [
            "=== DISEÑO DE MEZCLA — ACI PRC-211.1-22 ===",
            (self.descripcion + "\n" if self.descripcion else "")
            + f"f'c = {self.fc:.0f} kg/cm² | f'cr = {self.fcr:.0f} kg/cm² ({self.origen_fcr})",
            f"Asentamiento: {self.asentamiento_pulg:g} pulg (fila «{self.rango_asentamiento}») | TMN: {self.tmn} pulg | MF del fino: {self.mf:.2f}",
            f"• Paso 3 — Agua: {self.agua:.0f} kg/m³ (Tabla 5.3.3"
            + (f", ajuste {self.ajuste_agua_pct:+.0f} % por Tabla 5.3.3.1" if self.ajuste_agua_pct else "")
            + f") | Aire {tipo_aire}: {self.aire_pct:.1f} %",
            f"• Paso 4 — a/mc = {self.wcm:.2f} (Tabla 5.3.4; gobierna la {self.gobierna})",
            f"• Paso 5 — Cemento: {self.cemento:.0f} kg/m³ ({self.bolsas_por_m3:.1f} bolsas de 42,5 kg)",
            f"• Paso 6 — Agregado grueso: b/b0 = {self.b_b0:.3f} (Tabla 5.3.6) -> {self.grueso_sss:.0f} kg/m³ (SSS)",
            f"• Paso 7 — Agregado fino: {self.fino_sss:.0f} kg/m³ (SSS), por volúmenes absolutos",
            f"• Peso unitario teórico del concreto: {self.densidad_teorica:.0f} kg/m³",
        ]
        if self.corregido:
            lineas += [
                f"• Corrección por humedad (num. 4.7.8): agua libre de los agregados = {self.agua_libre:+.0f} kg/m³",
                f"  Agua a añadir: {self.agua_tanda:.0f} kg/m³ | Grueso húmedo: {self.grueso_humedo:.0f} kg/m³ | Fino húmedo: {self.fino_humedo:.0f} kg/m³",
            ]
        lineas.append(f"• Proporción en peso (cemento : fino : grueso / agua): {self.proporcion_en_peso()}")
        lineas.append("Nota: es una mezcla de prueba. ACI PRC-211.1-22 (num. 5.3.9) pide verificarla y ajustarla con una tanda de laboratorio.")
        return "\n".join(lineas)
