"""Módulo de ensayos de concreto fresco y endurecido.

Implementa:
- Temperatura del concreto fresco (ASTM C1064 / NTP 339.184)
- Asentamiento con cono de Abrams (NTP 339.035 / ASTM C143)
- Elaboración y curado de probetas cilíndricas (NTP 339.183 / ASTM C192)
- Resistencia a la compresión cilíndrica f'c (NTP 339.034 / ASTM C39-23 / RNE E.060)
- Corrección por esbeltez L/D <= 1,75 y dispersión de cilindros compañeros (num. 11.1.1)
"""

import math
from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


class ConcretoFresco:
    """Control de propiedades del concreto fresco."""

    def __init__(
        self,
        temperatura_c: float,
        asentamiento_mm: float,
        slump_especificado_pulg: float = 4.0,
        tolerancia_pulg: Optional[float] = None,
        hora_mezclado: str = "08:30",
        hora_muestreo: Optional[str] = None,
        fc_diseno_kg_cm2: float = 210.0,
        fecha: str = "2026-11-11",
        lugar: str = "Laboratorio FIC - UNSAAC",
        **kwargs,
    ):
        self.temperatura = float(temperatura_c)
        self.asentamiento_mm = float(asentamiento_mm)
        self.asentamiento_pulg = round(self.asentamiento_mm / 25.4, 2)
        self.slump_esp_pulg = float(slump_especificado_pulg)
        self.slump_esp_mm = self.slump_esp_pulg * 25.4
        if tolerancia_pulg is not None:
            self.tolerancia_pulg = float(tolerancia_pulg)
            self.tolerancia_mm = round(self.tolerancia_pulg * 25.4, 1)
            self.criterio_tolerancia = f"Especificado ({self.tolerancia_pulg:.2f}\")"
        else:
            # ASTM C94/C94M-22a num. 7.1 para asentamiento objetivo/nominal
            if self.slump_esp_mm <= 50.0:
                self.tolerancia_mm = 15.0
            elif self.slump_esp_mm <= 100.0:
                self.tolerancia_mm = 25.0
            else:
                self.tolerancia_mm = 40.0
            self.tolerancia_pulg = round(self.tolerancia_mm / 25.4, 2)
            self.criterio_tolerancia = f"ASTM C94 num. 7.1 (±{self.tolerancia_mm:.0f} mm)"
        self.hora = hora_muestreo or hora_mezclado
        self.fc_diseno = float(fc_diseno_kg_cm2)
        self.fecha = fecha
        self.lugar = lugar

        self._evaluar()

    def _evaluar(self):
        # Temperatura: ASTM C1064 / RNE E.060 recomienda entre 10 y 32 °C en colocación
        self.cumple_temp = 10.0 <= self.temperatura <= 32.0

        # Asentamiento: dentro de la tolerancia de diseño (ASTM C94)
        min_slump_mm = max(0.0, self.slump_esp_mm - self.tolerancia_mm)
        max_slump_mm = self.slump_esp_mm + self.tolerancia_mm
        self.cumple_slump = min_slump_mm <= self.asentamiento_mm <= max_slump_mm

        # Clasificación de consistencia
        if self.asentamiento_pulg <= 2.0:
            self.consistencia = "Seca / Firme (0\" - 2\")"
        elif self.asentamiento_pulg <= 4.0:
            self.consistencia = "Plástica (3\" - 4\")"
        elif self.asentamiento_pulg <= 7.0:
            self.consistencia = "Fluida (5\" - 7\")"
        else:
            self.consistencia = "Muy fluida / Segregable (> 7\")"

    def diagnostico_tecnico(self) -> str:
        return (
            f"=== CONTROL DE CONCRETO FRESCO ===\n"
            f"Fecha: {self.fecha} | Hora: {self.hora} | Diseño: f'c = {self.fc_diseno:.0f} kg/cm²\n"
            f"• Temperatura (ASTM C1064): {self.temperatura:.1f} °C -> "
            + ("CONFORME (10 a 32 °C)" if self.cumple_temp else "OBSERVADA")
            + f"\n• Asentamiento (ASTM C143): {self.asentamiento_mm:.0f} mm ({self.asentamiento_pulg:.2f}\") "
            f"[Especificado: {self.slump_esp_pulg:.1f}\" ± {self.tolerancia_pulg:.1f}\"]\n"
            f"  -> Consistencia: {self.consistencia}\n"
            f"  -> Veredicto Slump: "
            + ("CONFORME (Dentro de tolerancia ASTM C94)" if self.cumple_slump else "FUERA DE TOLERANCIA")
        )


class CompresionBriquetas:
    """Ensayo de resistencia a la compresión de probetas cilíndricas de concreto (ASTM C39-23 / RNE E.060)."""

    def __init__(
        self,
        probetas_datos: List[Dict[str, Union[str, float]]],
        fc_diseno_kg_cm2: float = 210.0,
        edad_control_dias: int = 28,
        fecha_vaciado: str = "2026-10-14",
        fecha_rotura: str = "2026-11-11",
        condicion: str = "laboratorio",
    ):
        """Inicializa el conjunto de probetas ensayadas."""
        self.datos_raw = probetas_datos
        self.fc_diseno = float(fc_diseno_kg_cm2)
        self.edad_control = int(edad_control_dias)
        self.fecha_vaciado = fecha_vaciado
        self.fecha_rotura = fecha_rotura
        self.condicion = "campo" if "campo" in condicion.lower() else "laboratorio"

        self._procesar()

    def _factor_esbeltez(self, ld: float) -> float:
        """Factor de corrección por esbeltez L/D <= 1,75 (ASTM C39-23 num. 9.2)."""
        if ld > 1.75:
            return 1.00
        # Interpolación entre puntos de tabla ASTM C39: 1.75->0.98, 1.50->0.96, 1.25->0.93, 1.00->0.87
        xp = [1.00, 1.25, 1.50, 1.75]
        fp = [0.87, 0.93, 0.96, 0.98]
        return float(np.interp(ld, xp, fp))

    def _procesar(self):
        filas = []
        for p in self.datos_raw:
            d = float(p.get("diametro_mm", float(p.get("diametro_cm", 15.0)) * 10.0 if "diametro_cm" in p else 150.0))
            h = float(p.get("altura_mm", float(p.get("altura_cm", 30.0)) * 10.0 if "altura_cm" in p else 300.0))
            if "carga_kN" in p:
                carga_kn = float(p["carga_kN"])
            elif "carga_rotura_kgf" in p:
                carga_kn = float(p["carga_rotura_kgf"]) * 0.00980665
            elif "carga_kgf" in p:
                carga_kn = float(p["carga_kgf"]) * 0.00980665
            else:
                carga_kn = 0.0

            edad = int(p.get("edad_dias", 28))
            falla = str(p.get("tipo_falla", "Tipo 1 (Cono)"))
            refrentado = str(p.get("sistema_refrentado", p.get("refrentado", "Yeso de alta resistencia (ASTM C617)")))

            area_mm2 = math.pi * (d**2) / 4.0
            carga_n = carga_kn * 1000.0
            fc_sin_corregir_mpa = carga_n / area_mm2 if area_mm2 > 0 else 0.0

            esbeltez = h / d if d > 0 else 2.0
            factor_ld = self._factor_esbeltez(esbeltez)

            fc_corregido_mpa = fc_sin_corregir_mpa * factor_ld
            fc_corregido_kg_cm2 = fc_corregido_mpa * 10.197162
            porc_diseno = (fc_corregido_kg_cm2 / self.fc_diseno) * 100.0 if self.fc_diseno > 0 else 0.0

            filas.append({
                "codigo": p.get("codigo", "PROBETA"),
                "edad_dias": edad,
                "diametro_mm": d,
                "altura_mm": h,
                "esbeltez_ld": round(esbeltez, 2),
                "factor_ld": round(factor_ld, 2),
                "carga_kN": round(carga_kn, 2),
                "fc_mpa": round(fc_corregido_mpa, 1),  # Redondeo a 0.1 MPa según ASTM C39 num. 10.1.6
                "fc_kg_cm2": round(fc_corregido_kg_cm2, 1),
                "porc_fc_diseno": round(porc_diseno, 1),
                "tipo_falla": falla,
                "refrentado": refrentado,
            })

        self.df = pd.DataFrame(filas)

        # Estadísticas a la edad de control (ej. 28 días)
        df_control = self.df[self.df["edad_dias"] == self.edad_control]
        if not df_control.empty:
            valores_fc = df_control["fc_kg_cm2"].values
            self.promedio_fc = round(float(np.mean(valores_fc)), 1)
            self.desv_std = round(float(np.std(valores_fc, ddof=1)), 1) if len(valores_fc) > 1 else 0.0
            self.cv_porc = round((self.desv_std / self.promedio_fc) * 100.0, 1) if self.promedio_fc > 0 else 0.0
            self.min_fc = round(float(np.min(valores_fc)), 1)

            # Rango entre cilindros compañeros ASTM C39-23 num. 11.1.1: (max - min) / prom * 100
            self.rango_companeros_porc = (
                round(((np.max(valores_fc) - np.min(valores_fc)) / self.promedio_fc) * 100.0, 1)
                if len(valores_fc) > 1 and self.promedio_fc > 0
                else 0.0
            )
            n_cil = len(valores_fc)
            d_med = float(df_control["diametro_mm"].median())
            es_100 = d_med < 125.0
            tabla_c39 = {
                (False, "laboratorio"): (6.6, 7.8),
                (False, "campo"): (8.0, 9.5),
                (True, "laboratorio"): (9.0, 10.6),
                (True, "campo"): (8.4, 9.9),
            }
            lim2, lim3 = tabla_c39[(es_100, self.condicion)]
            if n_cil <= 2:
                self.limite_rango_c39 = lim2
                self.cumple_rango_c39 = True if n_cil < 2 else (self.rango_companeros_porc <= lim2)
            elif n_cil == 3:
                self.limite_rango_c39 = lim3
                self.cumple_rango_c39 = self.rango_companeros_porc <= lim3
            else:
                self.limite_rango_c39 = None
                self.cumple_rango_c39 = None

            # Criterio doble RNE E.060 num. 5.6.3.3:
            # 1. Promedio de 3 ensayos consecutivos >= f'c
            # 2. Ningún ensayo individual < f'c - 35 kg/cm² (si f'c <= 350 kg/cm²) o < 0.90*f'c (si f'c > 350)
            self.cumple_promedio = self.promedio_fc >= self.fc_diseno
            self.limite_min_individual = (
                (self.fc_diseno - 35.0) if self.fc_diseno <= 350.0 else (0.90 * self.fc_diseno)
            )
            self.cumple_individual = self.min_fc >= self.limite_min_individual
            self.cumple_rne_e060 = self.cumple_promedio and self.cumple_individual
        else:
            self.promedio_fc = 0.0
            self.desv_std = 0.0
            self.cv_porc = 0.0
            self.min_fc = 0.0
            self.rango_companeros_porc = 0.0
            self.limite_rango_c39 = 7.8
            self.cumple_rango_c39 = True
            self.limite_min_individual = self.fc_diseno - 35.0
            self.cumple_rne_e060 = False

    def diagnostico_tecnico(self) -> str:
        lineas = [
            f"=== EVALUACIÓN NORMATIVA — RESISTENCIA A COMPRESIÓN f'c (ASTM C39-23 / RNE E.060) ===",
            f"Diseño: f'c = {self.fc_diseno:.0f} kg/cm² | Edad de control: {self.edad_control} días",
            f"Fecha vaciado: {self.fecha_vaciado} | Fecha ensayo: {self.fecha_rotura}",
            f"Probetas ensayadas a {self.edad_control} días: {len(self.df[self.df['edad_dias'] == self.edad_control])}",
            "",
            f"ESTADÍSTICAS DEL LOTE ({self.edad_control} DÍAS):",
            f"• Resistencia promedio: {self.promedio_fc:.1f} kg/cm² ({self.promedio_fc * 0.0980665:.1f} MPa | {(self.promedio_fc/self.fc_diseno)*100:.1f}% f'c)",
            f"• Desviación estándar (s): {self.desv_std:.1f} kg/cm² | Coeficiente de variación (CV): {self.cv_porc:.1f} %",
            f"• Rango entre probetas compañeras (ASTM C39 num. 11.1.1, {self.condicion}): {self.rango_companeros_porc:.1f} % "
            + (
                f"(Límite un operador: <= {self.limite_rango_c39:.1f} %) -> "
                + ("CONFORME" if self.cumple_rango_c39 else "DISPERSIÓN ALTA")
                if self.limite_rango_c39 is not None
                else "(ASTM C39 Tabla 11.1.1 tabula solo 2 o 3 cilindros)"
            ),
            "",
            "EVALUACIÓN DE ACEPTACIÓN SEGÚN RNE E.060 (num. 5.6.3.3)"
            + (" [REFERENCIAL: edad < 28 d]" if self.edad_control < 28 else "")
            + ":",
            f"1. Promedio >= f'c ({self.promedio_fc:.1f} >= {self.fc_diseno:.0f}): "
            + ("CONFORME" if self.cumple_promedio else "NO CUMPLE"),
            f"2. Ningún ensayo < límite individual ({self.min_fc:.1f} >= {self.limite_min_individual:.1f}): "
            + ("CONFORME" if self.cumple_individual else "NO CUMPLE"),
            "",
            "DICTAMEN ESTRUCTURAL: " + ("APROBADO — CONCRETO CONFORME" if self.cumple_rne_e060 else "OBSERVADO — EVALUAR TESTIGOS"),
        ]
        return "\n".join(lineas)
