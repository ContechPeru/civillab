"""Módulo de análisis de agregados según NTP y ASTM.

Implementa:
- Análisis granulométrico de agregado fino y grueso (NTP 400.012:2021 / ASTM C136)
- Control de tamizado y error de masa (<= 0,3 %)
- Determinación de MF, TM, TMN, D10, D30, D60, Cu y Cc
- Contraste de especificaciones con los 15 husos de NTP 400.037:2025 / ASTM C33-24
- Peso unitario suelto y compactado, calibración de molde y vacíos (ASTM C29-17a)
- Peso específico y absorción de agregados fino y grueso (ASTM C127 / C128)
- Humedad natural (ASTM C566), lavado malla 200 (ASTM C117) y abrasión Los Ángeles (ASTM C131-20)
"""

import math
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .standards import (
    TAMICES_INFO,
    TAMICES_MODULO_FINURA_MM,
    HUSO_AGREGADO_FINO,
    HUSOS_AGREGADO_GRUESO,
    HUSOS_DESCRIPCION,
    HUSOS_METADATOS,
    HUSOS_POR_TMN,
)


class Granulometria:
    """Procesamiento y evaluación normativa de análisis granulométrico."""

    def __init__(
        self,
        tipo: str,
        tamices: Union[Dict[str, float], List[str], None] = None,
        pesos_retenidos: Optional[List[float]] = None,
        masa_seca_inicial: Optional[float] = None,
        masa_lavada: Optional[float] = None,
        pasa_lavado_200: Optional[float] = None,
        huso: Optional[str] = None,
        cantera: str = "Cantera en estudio",
        muestra_id: str = "MUESTRA-01",
        fecha: str = "2026-11-11",
        lecturas_balanza: Optional[Dict[str, float]] = None,
    ):
        """Inicializa el ensayo granulométrico.

        Permite ingresar los datos en un solo diccionario visual:
            Granulometria(tipo='fino', lecturas_balanza={'3/8"': 0.0, 'N° 4': 15.0, ...})
        o bien con `tamices={'3/8"': 0.0, ...}` o listas separadas (`tamices=[...], pesos_retenidos=[...]`).
        """
        self.tipo = tipo.lower().strip()
        if self.tipo not in ["fino", "grueso"]:
            raise ValueError("El tipo debe ser 'fino' o 'grueso'.")

        # Soporte flexible: diccionario único o listas paralelas
        datos_dict = lecturas_balanza if lecturas_balanza is not None else (
            tamices if isinstance(tamices, dict) else None
        )

        if datos_dict is not None:
            self.tamices_raw = list(datos_dict.keys())
            self.pesos_raw = [float(v) for v in datos_dict.values()]
        elif isinstance(tamices, (list, tuple)) and pesos_retenidos is not None:
            if len(tamices) != len(pesos_retenidos):
                raise ValueError("La lista de tamices y pesos retenidos deben tener igual longitud.")
            self.tamices_raw = list(tamices)
            self.pesos_raw = [float(p) for p in pesos_retenidos]
        else:
            raise ValueError(
                "Debe proporcionar `lecturas_balanza={'tamiz': peso}` o las listas `tamices` y `pesos_retenidos`."
            )

        huso_in = str(huso).strip() if huso is not None else "auto"
        self._huso_solicitado = huso_in
        if self.tipo == "fino":
            self.huso = "fino"
        else:
            if huso_in.lower() == "auto":
                self.huso = "auto"
            elif huso_in in HUSOS_AGREGADO_GRUESO:
                self.huso = huso_in
            else:
                raise ValueError(
                    f"Huso '{huso_in}' no reconocido para agregado grueso. "
                    f"Use uno de {list(HUSOS_AGREGADO_GRUESO.keys())} o 'auto'."
                )
        self.cantera = cantera
        self.muestra_id = muestra_id
        self.fecha = fecha

        # Resolver masas (con cálculo automático de finos lavados si se entregan masas inicial y lavada)
        self.masa_tamizada_seco = sum(self.pesos_raw)
        self.masa_lavada = float(masa_lavada) if masa_lavada is not None else self.masa_tamizada_seco

        if pasa_lavado_200 is not None:
            self.pasa_lavado_200 = float(pasa_lavado_200)
        elif masa_seca_inicial is not None and masa_lavada is not None:
            self.pasa_lavado_200 = max(0.0, round(float(masa_seca_inicial) - float(masa_lavada), 2))
        else:
            self.pasa_lavado_200 = 0.0

        self.masa_seca_inicial = (
            float(masa_seca_inicial)
            if masa_seca_inicial is not None
            else (self.masa_tamizada_seco + self.pasa_lavado_200)
        )

        self._procesar()

    def _resolver_abertura(self, nombre: str) -> Optional[float]:
        """Obtiene la abertura en mm según el nombre comercial del tamiz."""
        nombre_clean = nombre.strip().replace("N.°", "N°").replace("#", "N°")
        if nombre_clean in TAMICES_INFO:
            return TAMICES_INFO[nombre_clean]
        for k, v in TAMICES_INFO.items():
            if k.lower().replace(" ", "") == nombre_clean.lower().replace(" ", ""):
                return v
        return None

    @staticmethod
    def _normalizar_tamiz(nombre: Optional[str]) -> str:
        """Normaliza denominaciones equivalentes de tamices (p. ej. 'N.° 4' -> 'N° 4')."""
        if not nombre:
            return ""
        return " ".join(str(nombre).strip().replace("N.°", "N°").replace("#", "N° ").split()).replace("N°  ", "N° ")

    def _pasa_por_abertura(self) -> Dict[float, Tuple[str, float]]:
        """Mapa {abertura_mm: (nombre_tamiz, porc_que_pasa)} de los tamices ensayados."""
        return {
            float(row["abertura_mm"]): (str(row["tamiz"]), float(row["porc_que_pasa"]))
            for _, row in self.df.iterrows()
            if pd.notnull(row["abertura_mm"]) and not row["es_fondo"]
        }

    def _evaluar_banda_grueso(self, codigo_huso: str) -> Dict:
        """Evalúa una banda gruesa ASTM C33 contra la muestra incluyendo monotonía entre tamices."""
        banda = HUSOS_AGREGADO_GRUESO[codigo_huso]
        pasa_map = self._pasa_por_abertura()
        medidos = 0
        observaciones = []
        max_desv = 0.0
        dist_centro = []

        for ab, (lmin, lmax) in banda.items():
            matches = [(nom, val) for k, (nom, val) in pasa_map.items() if math.isclose(k, ab, rel_tol=0.04)]
            if matches:
                nom_t, val = matches[0]
                medidos += 1
                dist_centro.append(abs(val - 0.5 * (lmin + lmax)))
                if val < (lmin - 0.5):
                    desv = round(lmin - val, 2)
                    max_desv = max(max_desv, desv)
                    observaciones.append(f"{nom_t}: {val:.1f}% (< {lmin:.0f}%)")
                elif val > (lmax + 0.5):
                    desv = round(val - lmax, 2)
                    max_desv = max(max_desv, desv)
                    observaciones.append(f"{nom_t}: {val:.1f}% (> {lmax:.0f}%)")
            else:
                # Verificación por monotonía: el % que pasa no decrece al subir abertura
                finer = [val for k, (_, val) in pasa_map.items() if k < ab]
                coarser = [val for k, (_, val) in pasa_map.items() if k > ab]
                if finer and max(finer) > (lmax + 0.5):
                    lb = max(finer)
                    desv = round(lb - lmax, 2)
                    max_desv = max(max_desv, desv)
                    observaciones.append(f"{ab:g} mm (>= {lb:.1f}% > {lmax:.0f}%)")
                elif coarser and min(coarser) < (lmin - 0.5):
                    ub = min(coarser)
                    desv = round(lmin - ub, 2)
                    max_desv = max(max_desv, desv)
                    observaciones.append(f"{ab:g} mm (<= {ub:.1f}% < {lmin:.0f}%)")

        cumple = (len(observaciones) == 0) and (medidos >= 3)
        score_centro = round(sum(dist_centro) / len(dist_centro), 2) if dist_centro else 999.0
        return {
            "huso": codigo_huso,
            "cumple": cumple,
            "medidos": medidos,
            "max_desv": round(max_desv, 1),
            "score_centro": score_centro,
            "observaciones": observaciones,
        }

    def _procesar(self):
        """Ejecuta los cálculos matemáticos normados."""
        # 1. Control de masa en tamizado seco (ASTM C136-19 num. 8.7)
        if self.masa_lavada > 0:
            self.error_masa_porc = (
                abs(self.masa_tamizada_seco - self.masa_lavada) / self.masa_lavada
            ) * 100.0
        else:
            self.error_masa_porc = 0.0
        self.cumple_error_masa = self.error_masa_porc <= 0.3

        base = self.masa_seca_inicial if self.masa_seca_inicial > 0 else self.masa_tamizada_seco
        self.pasa_n200_porc = (self.pasa_lavado_200 / base) * 100.0 if base > 0 else 0.0

        filas = []
        peso_acum = 0.0

        for t_nom, w in zip(self.tamices_raw, self.pesos_raw):
            abertura = self._resolver_abertura(t_nom)
            es_fondo = "fondo" in t_nom.lower() or "platillo" in t_nom.lower()

            peso_item = w
            peso_item_total = peso_item + self.pasa_lavado_200 if (es_fondo and self.pasa_lavado_200 > 0) else peso_item

            ret_parcial_porc = (peso_item_total / base) * 100.0 if base > 0 else 0.0

            if not es_fondo:
                peso_acum += peso_item
                ret_acum_porc = (peso_acum / base) * 100.0 if base > 0 else 0.0
                pasa_porc = max(0.0, 100.0 - ret_acum_porc)
            else:
                ret_acum_porc = 100.0
                pasa_porc = 0.0

            filas.append({
                "tamiz": t_nom,
                "abertura_mm": abertura,
                "peso_retenido_g": w,
                "porc_retenido_parcial": ret_parcial_porc,
                "porc_retenido_acum": ret_acum_porc,
                "porc_que_pasa": pasa_porc,
                "lim_min": None,
                "lim_max": None,
                "es_fondo": es_fondo,
            })

        self.df = pd.DataFrame(filas)

        # 2. Módulo de Finura (ASTM C136-19 num. 9.2)
        suma_ra_mf = 0.0
        tamices_mf_usados = []
        tamices_presentes = {}
        for _, row in self.df.iterrows():
            ab = row["abertura_mm"]
            if pd.notnull(ab) and not row["es_fondo"]:
                tamices_presentes[float(ab)] = (row["tamiz"], float(row["porc_retenido_acum"]))

        aberturas_ordenadas = sorted(tamices_presentes.keys())
        min_abertura_ensayada = aberturas_ordenadas[0] if aberturas_ordenadas else 0.0
        ra_del_mas_fino = tamices_presentes[min_abertura_ensayada][1] if aberturas_ordenadas else 0.0

        for ab_std in TAMICES_MODULO_FINURA_MM:
            encontrado = False
            for ab_real, (nom_t, ra_val) in tamices_presentes.items():
                if math.isclose(ab_real, ab_std, rel_tol=0.04):
                    suma_ra_mf += ra_val
                    tamices_mf_usados.append((nom_t, ra_val))
                    encontrado = True
                    break

            if not encontrado:
                if self.tipo == "grueso" and ab_std < min_abertura_ensayada:
                    suma_ra_mf += ra_del_mas_fino
                    tamices_mf_usados.append((f"[{ab_std} mm omis.]", ra_del_mas_fino))

        self.modulo_finura = round(suma_ra_mf / 100.0, 2)
        self.tamices_mf_usados = tamices_mf_usados

        # 3. Tamaño Máximo y Tamaño Máximo Nominal (NTP 400.037:2025 num. 3.11, 3.12)
        self.tamano_maximo = None
        self.tamano_maximo_nominal = None
        df_tamices = self.df[~self.df["es_fondo"]].copy()

        pasa_100 = df_tamices[df_tamices["porc_que_pasa"] >= 99.95]
        if not pasa_100.empty:
            self.tamano_maximo = pasa_100.iloc[-1]["tamiz"]

        primer_ret = df_tamices[df_tamices["porc_retenido_acum"] > 0.05]
        if not primer_ret.empty:
            self.tamano_maximo_nominal = primer_ret.iloc[0]["tamiz"]

        # 4. Retención máxima entre tamices consecutivos (ASTM C33 num. 6.2: <= 45 %)
        self.max_ret_consecutivo = 0.0
        self.tamiz_max_consecutivo = ""
        for i in range(len(df_tamices) - 1):
            dif = df_tamices.iloc[i + 1]["porc_retenido_parcial"]
            if dif > self.max_ret_consecutivo:
                self.max_ret_consecutivo = dif
                self.tamiz_max_consecutivo = (
                    f"{df_tamices.iloc[i]['tamiz']} - {df_tamices.iloc[i+1]['tamiz']}"
                )

        self.cumple_consecutivo = (
            self.max_ret_consecutivo <= 45.0 if self.tipo == "fino" else True
        )

        # 5. Diámetros característicos (D10, D30, D60) vía interpolación logarítmica
        self.d10 = self._interpolar_diametro(10.0)
        self.d30 = self._interpolar_diametro(30.0)
        self.d60 = self._interpolar_diametro(60.0)

        self.cu = round(self.d60 / self.d10, 2) if (self.d10 and self.d10 > 0 and self.d60) else None
        if self.d10 and self.d30 and self.d60 and (self.d60 * self.d10) > 0:
            self.cc = round((self.d30**2) / (self.d60 * self.d10), 2)
        else:
            self.cc = None

        # 6. Selección automática de huso (si corresponde) y aplicación de límites
        self.huso_sugerido, self.huso_razon_seleccion = self.sugerir_huso()
        if self.tipo == "grueso" and self.huso == "auto":
            self.huso = self.huso_sugerido

        lim_mins = []
        lim_maxs = []
        for _, row in self.df.iterrows():
            ab = row["abertura_mm"]
            lmin, lmax = None, None
            if pd.notnull(ab):
                ab_f = float(ab)
                if self.tipo == "fino" and ab_f in HUSO_AGREGADO_FINO:
                    lmin, lmax = HUSO_AGREGADO_FINO[ab_f]
                elif self.tipo == "grueso" and self.huso in HUSOS_AGREGADO_GRUESO:
                    huso_dict = HUSOS_AGREGADO_GRUESO[self.huso]
                    if ab_f in huso_dict:
                        lmin, lmax = huso_dict[ab_f]
            lim_mins.append(lmin)
            lim_maxs.append(lmax)
        self.df["lim_min"] = lim_mins
        self.df["lim_max"] = lim_maxs

        # 7. Evaluación de cumplimiento del huso seleccionado
        self.discrepancias_huso = []
        for _, row in self.df.iterrows():
            if pd.notnull(row["lim_min"]) and pd.notnull(row["lim_max"]):
                pasa = row["porc_que_pasa"]
                if pasa < (row["lim_min"] - 0.5) or pasa > (row["lim_max"] + 0.5):
                    self.discrepancias_huso.append({
                        "tamiz": row["tamiz"],
                        "abertura_mm": row["abertura_mm"],
                        "obtenido": pasa,
                        "min_norma": row["lim_min"],
                        "max_norma": row["lim_max"],
                    })

        self.cumple_huso = len(self.discrepancias_huso) == 0
        self.cumple_mf = (2.30 <= self.modulo_finura <= 3.10) if self.tipo == "fino" else True

    def identificar_husos_compatibles(self) -> List[str]:
        """Compara la muestra gruesa contra los 15 husos ASTM C33 y devuelve los compatibles."""
        if self.tipo != "grueso":
            return ["Tabla 1 (Fino)"] if self.cumple_huso else []
        return [
            cod for cod in HUSOS_AGREGADO_GRUESO
            if self._evaluar_banda_grueso(cod)["cumple"]
        ]

    def sugerir_huso(self) -> Tuple[str, str]:
        """Sugiere el huso normado más adecuado según TMN calculado y compatibilidad de la curva."""
        if self.tipo == "fino":
            return (
                "fino",
                "Agregado fino: aplica el huso único de NTP 400.037:2025 Tabla 1 / ASTM C33 núm. 6.1.",
            )

        tmn_norm = self._normalizar_tamiz(self.tamano_maximo_nominal)
        candidatos_tmn = HUSOS_POR_TMN.get(tmn_norm, [])
        evals = {cod: self._evaluar_banda_grueso(cod) for cod in HUSOS_AGREGADO_GRUESO}
        compatibles = [cod for cod, ev in evals.items() if ev["cumple"]]

        for cod in candidatos_tmn:
            if cod in compatibles:
                uso = HUSOS_DESCRIPCION[cod][1]
                return (
                    cod,
                    f"TMN detectado = {self.tamano_maximo_nominal} -> corresponde a huso(s) {', '.join(candidatos_tmn)}. "
                    f"Se recomienda Huso {cod} ({uso}) porque cumple íntegramente la banda y prioriza gradación continua.",
                )

        if compatibles:
            mejor = min(compatibles, key=lambda c: evals[c]["score_centro"])
            return (
                mejor,
                f"Aunque el TMN detectado es {self.tamano_maximo_nominal or 'N/D'}, la curva encaja exactamente "
                f"en el Huso {mejor} ({HUSOS_DESCRIPCION[mejor][0]}).",
            )

        if candidatos_tmn:
            mejor = min(candidatos_tmn, key=lambda c: (evals[c]["max_desv"], evals[c]["score_centro"]))
            return (
                mejor,
                f"Ninguno de los 15 husos cumple al 100 %. Para el TMN {self.tamano_maximo_nominal}, el Huso {mejor} "
                f"es el referente más cercano (desviación máx. {evals[mejor]['max_desv']:.1f} %); requiere verificación "
                f"con diseño de mezcla según NTP 400.037:2025 Tabla 3.",
            )

        mejor = min(evals.keys(), key=lambda c: (evals[c]["max_desv"], evals[c]["score_centro"]))
        return (
            mejor,
            f"Ninguno de los 15 husos cumple exactamente; el Huso {mejor} presenta la menor desviación máxima ({evals[mejor]['max_desv']:.1f} %).",
        )

    def tabla_comparacion_husos(self) -> pd.DataFrame:
        """Compara la muestra contra todos los husos ASTM C33 / NTP 400.037 y explica cada ajuste."""
        if self.tipo == "fino":
            estado = "CUMPLE" if self.cumple_huso else "NO CUMPLE"
            obs = "—" if self.cumple_huso else "; ".join(
                f"{d['tamiz']}: {d['obtenido']:.1f}% ({d['min_norma']:.0f}-{d['max_norma']:.0f}%)"
                for d in self.discrepancias_huso
            )
            return pd.DataFrame([{
                "Huso N.°": "Tabla 1 (Fino)",
                "TMN Esperado": '3/8" (9,5 mm)',
                "Coincide TMN": "Sí",
                "Cumple Banda": estado,
                "Desv. Máx. (%)": 0.0 if self.cumple_huso else round(
                    max(max(d["min_norma"] - d["obtenido"], d["obtenido"] - d["max_norma"]) for d in self.discrepancias_huso), 1
                ),
                "Tamices Observados": obs,
                "Uso Recomendado en Obra": "Morteros y concretos en general (MF recomendable 2,30 a 3,10)",
            }])

        tmn_norm = self._normalizar_tamiz(self.tamano_maximo_nominal)
        candidatos_tmn = set(HUSOS_POR_TMN.get(tmn_norm, []))
        filas = []
        for cod, (rango, uso) in HUSOS_DESCRIPCION.items():
            ev = self._evaluar_banda_grueso(cod)
            meta = HUSOS_METADATOS.get(cod, {})
            if ev["cumple"]:
                estado = "CUMPLE"
            elif ev["medidos"] < 3 and not ev["observaciones"]:
                estado = "Tamices insuf."
            else:
                estado = "NO CUMPLE"

            filas.append({
                "Huso N.°": cod,
                "TMN Esperado": f"{meta.get('tmn', '—')}",
                "Coincide TMN": "Sí" if cod in candidatos_tmn else "No",
                "Cumple Banda": estado,
                "Desv. Máx. (%)": ev["max_desv"],
                "Tamices Observados": "—" if not ev["observaciones"] else "; ".join(ev["observaciones"]),
                "Uso Recomendado en Obra": f"{uso} [{rango}]",
                "_ord_cumple": 0 if ev["cumple"] else 1,
                "_ord_tmn": 0 if cod in candidatos_tmn else 1,
                "_ord_score": ev["score_centro"],
            })

        df_comp = pd.DataFrame(filas).sort_values(
            ["_ord_cumple", "_ord_tmn", "Desv. Máx. (%)", "_ord_score"]
        ).drop(columns=["_ord_cumple", "_ord_tmn", "_ord_score"]).reset_index(drop=True)
        return df_comp

    def _interpolar_diametro(self, p_target: float) -> Optional[float]:
        """Calcula el diámetro D_p en mm para un porcentaje pasante target."""
        df_puntos = self.df.dropna(subset=["abertura_mm"]).sort_values("abertura_mm")
        x = df_puntos["abertura_mm"].values
        y = df_puntos["porc_que_pasa"].values

        if len(x) < 2 or p_target < y.min() or p_target > y.max():
            return None

        for i in range(len(y) - 1):
            y1, y2 = y[i], y[i + 1]
            x1, x2 = x[i], x[i + 1]
            if (y1 <= p_target <= y2) or (y2 <= p_target <= y1):
                if y2 == y1:
                    return float(x1)
                log_x1 = np.log10(x1)
                log_x2 = np.log10(x2)
                log_target = log_x1 + ((p_target - y1) / (y2 - y1)) * (log_x2 - log_x1)
                return round(float(10**log_target), 3)

        return None

    def tabla_resumen(self) -> pd.DataFrame:
        """Retorna una tabla formateada para presentación y reporte."""
        df_out = self.df.copy()
        df_out["Abertura (mm)"] = df_out["abertura_mm"].apply(
            lambda x: f"{x:.3f}" if pd.notnull(x) else "—"
        )
        df_out["Retenido (g)"] = df_out["peso_retenido_g"].apply(lambda x: f"{x:.1f}")
        df_out["% Retenido"] = df_out["porc_retenido_parcial"].apply(lambda x: f"{x:.1f}%")
        df_out["% Ret. Acum."] = df_out["porc_retenido_acum"].apply(
            lambda x: f"{x:.1f}%" if pd.notnull(x) else "—"
        )
        df_out["% Pasa"] = df_out["porc_que_pasa"].apply(
            lambda x: f"{x:.1f}%" if pd.notnull(x) else "—"
        )

        def fmt_lim(row):
            if pd.notnull(row["lim_min"]) and pd.notnull(row["lim_max"]):
                if row["lim_min"] == row["lim_max"]:
                    return f"{row['lim_min']:.0f}%"
                return f"{row['lim_min']:.0f}% - {row['lim_max']:.0f}%"
            return "—"

        df_out["Huso Norma"] = df_out.apply(fmt_lim, axis=1)

        cols = [
            "tamiz",
            "Abertura (mm)",
            "Retenido (g)",
            "% Retenido",
            "% Ret. Acum.",
            "% Pasa",
            "Huso Norma",
        ]
        return df_out[cols].rename(columns={"tamiz": "Tamiz"})

    def diagnostico_tecnico(self) -> str:
        """Genera un reporte técnico de conformidad normativa."""
        lineas = [
            f"=== EVALUACIÓN NORMATIVA — GRANULOMETRÍA ({self.tipo.upper()}) ===",
            f"Cantera / Procedencia: {self.cantera} | Muestra: {self.muestra_id} | Fecha: {self.fecha}",
            f"Masa seca inicial: {self.masa_seca_inicial:.1f} g | Fino lavado malla N° 200: {self.pasa_lavado_200:.1f} g ({self.pasa_lavado_200/self.masa_seca_inicial*100:.1f}%)" if self.masa_seca_inicial > 0 else f"Masa seca: {self.masa_seca_inicial:.1f} g",
            f"Control de pérdida en tamizado seco: {self.error_masa_porc:.2f} % (Límite ASTM C136 num. 8.7 <= 0,3 %): "
            + ("CONFORME" if self.cumple_error_masa else "NO CONFORME - REPETIR ENSAYO"),
            "",
            "PARÁMETROS FÍSICOS CALCULADOS:",
            f"• Módulo de Finura (MF): {self.modulo_finura:.2f}",
        ]

        if self.tipo == "fino":
            lineas.append(
                f"  -> Criterio MF ASTM C33 (2,30 a 3,10): "
                + ("CONFORME" if self.cumple_mf else f"FUERA DE RANGO ({self.modulo_finura:.2f})")
            )
            lineas.append(
                f"• Máximo retenido entre tamices consecutivos: {self.max_ret_consecutivo:.1f} % ({self.tamiz_max_consecutivo})"
            )
            lineas.append(
                f"  -> Criterio ASTM C33 num. 6.2 (<= 45 %): "
                + ("CONFORME" if self.cumple_consecutivo else "NO CUMPLE (excede 45 %)")
            )
        else:
            desc, uso_huso = HUSOS_DESCRIPCION.get(self.huso, ("", ""))
            meta = HUSOS_METADATOS.get(self.huso, {})
            modo = "Automático por TMN" if self._huso_solicitado.lower() == "auto" else "Manual especificado"
            lineas.append(f"• Tamaño Máximo (TM): {self.tamano_maximo}")
            lineas.append(f"• Tamaño Máximo Nominal (TMN): {self.tamano_maximo_nominal}")
            lineas.append(f"• Huso evaluado ({modo}): Huso N.° {self.huso} ({desc}) [NTP 400.037 / ASTM C33]")
            lineas.append(f"  -> Uso típico en obra: {uso_huso}")
            lineas.append(f"  -> Criterio de selección: {self.huso_razon_seleccion}")
            if meta.get("nota"):
                lineas.append(f"  -> Nota normativa: {meta['nota']}")
            if self.pasa_lavado_200 > 0:
                lim_b = "CUMPLE (<= 1,0 %)" if self.pasa_n200_porc <= 1.0 else (
                    "ACEPTABLE SOLO SI LIBRE DE ARCILLA/PIZARRA (1,0–1,5 %)" if self.pasa_n200_porc <= 1.5
                    else "EXCEDE NOTA B (> 1,5 %)"
                )
                lineas.append(f"• Material pasa N° 200 (NTP 400.037:2025 Tabla 3 Nota B / ASTM C33): {self.pasa_n200_porc:.2f} % -> {lim_b}")

        if self.d10 and self.d60:
            lineas.append(f"• Diámetros característicos: D10 = {self.d10} mm | D30 = {self.d30} mm | D60 = {self.d60} mm")
            if self.cu:
                lineas.append(f"• Coeficientes de gradación: Cu = {self.cu} | Cc = {self.cc}")

        lineas.append("")
        lineas.append("EVALUACIÓN DEL HUSO GRANULOMÉTRICO:")
        if self.cumple_huso:
            nombre_huso_ok = "Huso Único (Tabla 1 NTP 400.037:2025)" if self.tipo == "fino" else f"Huso {self.huso}"
            lineas.append(f"[CONFORME] La muestra CUMPLE íntegramente las tolerancias del {nombre_huso_ok}.")
        else:
            lineas.append(f"[OBSERVADO] La muestra NO CUMPLE en {len(self.discrepancias_huso)} tamiz/tamices:")
            for d in self.discrepancias_huso:
                lineas.append(
                    f"   - {d['tamiz']} ({d['abertura_mm']} mm): obtenido {d['obtenido']:.1f} % "
                    f"(especificado {d['min_norma']:.0f} % a {d['max_norma']:.0f} %)"
                )
            if self.tipo == "grueso":
                alt = self.identificar_husos_compatibles()
                if alt:
                    lineas.append(f"  [SUGERENCIA AUTOMÁTICA] Esta granulometría SÍ encaja con el/los Huso(s): {', '.join(alt)}")
                else:
                    lineas.append(
                        "  [EXCEPCIÓN NTP 400.037] Se admite fuera de huso solo si existen estudios y diseños de mezcla "
                        "que aseguren la resistencia y trabajabilidad requeridas."
                    )

        return "\n".join(lineas)


# ==============================================================================
# CLASES COMPLEMENTARIAS DE ENSAYOS DE AGREGADOS (NTP / ASTM)
# ==============================================================================

class PesoUnitario:
    """Ensayo de peso unitario suelto, compactado y vacíos (NTP 400.017 / ASTM C29-17a)."""

    @classmethod
    def calibrar_volumen(
        cls,
        masa_molde_vacio_kg: float,
        masa_molde_agua_kg: float,
        temp_agua_c: float = 20.0,
    ) -> float:
        """Calcula el volumen real del recipiente según calibración por masa de agua (ASTM C29 §8)."""
        densidad = 1000.0 / (1.0 + (temp_agua_c - 4.0) * 0.00021 + ((temp_agua_c - 4.0) ** 2) * 0.000004)
        vol_m3 = (masa_molde_agua_kg - masa_molde_vacio_kg) / densidad
        return round(vol_m3, 6)

    def __init__(
        self,
        volumen_recipiente_m3: float,
        masa_molde_kg: float,
        masa_molde_suelto_kg: float,
        masa_molde_compactado_kg: float,
        peso_especifico_od: Optional[float] = None,
        absorcion_porc: Optional[float] = None,
        tipo_agregado: str = "fino",
        cantera: str = "Cantera en estudio",
        fecha: str = "2026-11-11",
    ):
        self.vol_m3 = float(volumen_recipiente_m3)
        self.w_molde = float(masa_molde_kg)
        self.w_suelto = float(masa_molde_suelto_kg)
        self.w_compact = float(masa_molde_compactado_kg)
        self.pe_od = float(peso_especifico_od) if peso_especifico_od else None
        self.absorcion_porc = float(absorcion_porc) if absorcion_porc is not None else None
        self.tipo = tipo_agregado
        self.cantera = cantera
        self.fecha = fecha

        # Cálculos directos (kg/m³)
        self.pus = round((self.w_suelto - self.w_molde) / self.vol_m3, 1)
        self.puc = round((self.w_compact - self.w_molde) / self.vol_m3, 1)

        # Redondeo reglamentario a los 10 kg/m³ más cercanos (ASTM C29-17a num. 11.1)
        self.pus_norma = round(self.pus / 10.0) * 10
        self.puc_norma = round(self.puc / 10.0) * 10

        # Peso unitario SSS opcional (ASTM C29-17a num. 10.1.1 ec. 3)
        if self.absorcion_porc is not None:
            factor = 1.0 + (self.absorcion_porc / 100.0)
            self.pus_sss = round(self.pus * factor, 1)
            self.puc_sss = round(self.puc * factor, 1)
        else:
            self.pus_sss = None
            self.puc_sss = None

        # Porcentaje de vacíos según ASTM C29-17a num. 10.2 ec. 4 (W_a = 998 kg/m³)
        if self.pe_od and self.pe_od > 0:
            dens_agua = 998.0  # kg/m3 según ASTM C29 num. 10.2
            self.vacios_suelto = round(
                ((self.pe_od * dens_agua - self.pus) / (self.pe_od * dens_agua)) * 100.0, 1
            )
            self.vacios_compact = round(
                ((self.pe_od * dens_agua - self.puc) / (self.pe_od * dens_agua)) * 100.0, 1
            )
            # Redondeo al 1 % más cercano (ASTM C29 num. 11.2)
            self.vacios_suelto_norma = round(self.vacios_suelto)
            self.vacios_compact_norma = round(self.vacios_compact)
        else:
            self.vacios_suelto = None
            self.vacios_compact = None
            self.vacios_suelto_norma = None
            self.vacios_compact_norma = None

        self.coherencia_ok = self.puc > self.pus

    def diagnostico_tecnico(self) -> str:
        lineas = [
            f"=== PESO UNITARIO Y VACÍOS ({self.tipo.upper()}) — ASTM C29 / NTP 400.017 ===",
            f"Cantera: {self.cantera} | Volumen calibrado del recipiente: {self.vol_m3*1000:.2f} L ({self.vol_m3:.6f} m³)",
            f"• Peso Unitario Suelto (PUS):     {self.pus:.1f} kg/m³  [Informar ASTM: {self.pus_norma} kg/m³]",
            f"• Peso Unitario Compactado (PUC): {self.puc:.1f} kg/m³  [Informar ASTM: {self.puc_norma} kg/m³]",
        ]
        if self.puc_sss is not None:
            lineas.append(f"• Peso Unitario Compactado SSS:   {self.puc_sss:.1f} kg/m³ (con Abs = {self.absorcion_porc:.2f}%)")
        if self.vacios_suelto is not None:
            lineas.append(f"• % Vacíos Suelto (con G_OD={self.pe_od:.3f}):     {self.vacios_suelto:.1f} %  [Informar ASTM: {self.vacios_suelto_norma} %]")
            lineas.append(f"• % Vacíos Compactado (con G_OD={self.pe_od:.3f}): {self.vacios_compact:.1f} %  [Informar ASTM: {self.vacios_compact_norma} %]")
        lineas.append(f"• Coherencia física (PUC > PUS): {'CONFORME' if self.coherencia_ok else 'OBSERVADA - Revisar tara o varillado'}")
        return "\n".join(lineas)


class PesoEspecificoAbsorcion:
    """Peso específico y absorción de agregados (NTP 400.021, 400.022 / ASTM C127, C128)."""

    def __init__(
        self,
        tipo: str,
        masa_seca_horno_a: float,
        masa_sss_b: Optional[float] = None,
        masa_sumergida_c: Optional[float] = None,
        masa_picnometro_agua_b: Optional[float] = None,
        masa_muestra_sss_s: Optional[float] = None,
        masa_picnometro_muestra_c: Optional[float] = None,
        cantera: str = "Cantera en estudio",
        fecha: str = "2026-11-11",
    ):
        self.tipo = tipo.lower().strip()
        self.cantera = cantera
        self.fecha = fecha

        if self.tipo == "grueso":
            # ASTM C127: A = seco horno, B = SSS aire, C = sumergido
            self.a = float(masa_seca_horno_a)
            self.b = float(masa_sss_b)
            self.c = float(masa_sumergida_c)

            den = self.b - self.c
            self.volumen_desalojado_cm3 = round(den, 2)
            self.pe_od = round(self.a / den, 3) if den > 0 else 0.0
            self.pe_sss = round(self.b / den, 3) if den > 0 else 0.0
            self.pe_aparente = round(self.a / (self.a - self.c), 3) if (self.a - self.c) > 0 else 0.0
            self.absorcion_porc = round(((self.b - self.a) / self.a) * 100.0, 2) if self.a > 0 else 0.0

        else:
            # ASTM C128 (Fino): A = seco horno, B = picnómetro+agua, S = muestra SSS, C = picnómetro+muestra+agua
            self.a = float(masa_seca_horno_a)
            self.b = float(masa_picnometro_agua_b)
            self.s = float(masa_muestra_sss_s)
            self.c = float(masa_picnometro_muestra_c)

            den = self.b + self.s - self.c
            self.volumen_desalojado_cm3 = round(den, 2)
            self.pe_od = round(self.a / den, 3) if den > 0 else 0.0
            self.pe_sss = round(self.s / den, 3) if den > 0 else 0.0
            self.pe_aparente = round(self.a / (self.b + self.a - self.c), 3) if (self.b + self.a - self.c) > 0 else 0.0
            self.absorcion_porc = round(((self.s - self.a) / self.a) * 100.0, 2) if self.a > 0 else 0.0

        self.coherencia_ok = (self.pe_aparente >= self.pe_sss >= self.pe_od) and (self.pe_od > 0)

    def comparar_d2s(self, replica: "PesoEspecificoAbsorcion") -> pd.DataFrame:
        """Verifica criterio d2s un solo operador (ASTM C127 Tabla 1 / ASTM C128 Tabla 1)."""
        limites = (
            {"pe_od": 0.025, "pe_sss": 0.020, "pe_aparente": 0.020, "absorcion_porc": None}
            if self.tipo == "grueso"
            else {"pe_od": 0.032, "pe_sss": 0.027, "pe_aparente": 0.027, "absorcion_porc": 0.31}
        )
        filas = []
        nombres = {"pe_od": "G_OD", "pe_sss": "G_SSS", "pe_aparente": "G_aparente", "absorcion_porc": "Absorción (%)"}
        for attr, lim in limites.items():
            v1 = getattr(self, attr)
            v2 = getattr(replica, attr)
            dif = round(abs(v1 - v2), 3)
            estado = "Sin d2s en norma" if lim is None else ("CUMPLE" if dif <= lim else f"EXCEDE ({dif} > {lim})")
            filas.append({
                "Parámetro": nombres[attr],
                "Ensayo 1": v1,
                "Ensayo 2": v2,
                "Diferencia |E1-E2|": dif,
                "Límite d2s": f"{lim}" if lim is not None else "—",
                "Control": estado,
            })
        return pd.DataFrame(filas)

    def diagnostico_tecnico(self) -> str:
        norma = "ASTM C127 / NTP 400.021" if self.tipo == "grueso" else "ASTM C128 / NTP 400.022"
        return (
            f"=== PESO ESPECÍFICO Y ABSORCIÓN ({self.tipo.upper()}) — {norma} ===\n"
            f"Cantera: {self.cantera} | Fecha: {self.fecha}\n"
            f"• Volumen de partículas SSS desalojado:        {self.volumen_desalojado_cm3:.2f} cm³\n"
            f"• Peso Específico de Masa Seco (G_OD):         {self.pe_od:.3f}  [Informar ASTM: {self.pe_od:.2f}]\n"
            f"• Peso Específico Sat. Sup. Seco (G_SSS):      {self.pe_sss:.3f}  [Informar ASTM: {self.pe_sss:.2f}]\n"
            f"• Peso Específico Aparente (G_a):              {self.pe_aparente:.3f}  [Informar ASTM: {self.pe_aparente:.2f}]\n"
            f"• Porcentaje de Absorción (Ab):                {self.absorcion_porc:.2f} % [Informar ASTM: {self.absorcion_porc:.1f} %]\n"
            f"• Coherencia termodinámica (G_a >= G_SSS >= G_OD): "
            + ("CONFORME" if self.coherencia_ok else "ANOMALÍA DETECTADA - REVISAR PESADAS")
        )


class ContenidoHumedad:
    """Contenido de humedad total evaporable de agregados (NTP 339.185 / ASTM C566-13)."""

    def __init__(
        self,
        masa_humeda_g: float,
        masa_seca_g: float,
        tipo_agregado: str = "fino",
        cantera: str = "Cantera en estudio",
        fecha: str = "2026-11-11",
    ):
        self.wh = float(masa_humeda_g)
        self.ws = float(masa_seca_g)
        self.tipo = tipo_agregado
        self.cantera = cantera
        self.fecha = fecha

        self.agua_evaporada_g = round(self.wh - self.ws, 2)
        self.humedad_porc = round(((self.wh - self.ws) / self.ws) * 100.0, 2) if self.ws > 0 else 0.0

    def diagnostico_tecnico(self) -> str:
        return (
            f"=== CONTENIDO DE HUMEDAD TOTAL ({self.tipo.upper()}) — ASTM C566 / NTP 339.185 ===\n"
            f"Cantera: {self.cantera} | Masa húmeda: {self.wh:.1f} g | Masa seca constante: {self.ws:.1f} g\n"
            f"• Agua evaporada: {self.agua_evaporada_g:.1f} g\n"
            f"• Contenido de Humedad Natural (w): {self.humedad_porc:.2f} %  [Informar ASTM: {self.humedad_porc:.1f} %]"
        )


class MaterialPasa200:
    """Material más fino que el tamiz N.° 200 por lavado (NTP 400.018 / ASTM C117-17)."""

    def __init__(
        self,
        masa_seca_inicial_g: float,
        masa_seca_lavada_g: float,
        tipo: str = "fino",
        uso_concreto: str = "general",
        cantera: str = "Cantera en estudio",
        fecha: str = "2026-11-11",
    ):
        """
        uso_concreto:
          - Si tipo == 'fino': 'abrasion' (<= 3,0 %) o 'general' (<= 5,0 %) [NTP 400.037:2025 Tabla 1]
          - Si tipo == 'grueso': 'general' (<= 1,0 %) o 'triturado_sin_arcilla' (<= 1,5 %) [NTP 400.037:2025 Tabla 3 Nota B / ASTM C33 Tabla 3 Nota B]
        """
        self.m1 = float(masa_seca_inicial_g)
        self.m2 = float(masa_seca_lavada_g)
        self.tipo = tipo.lower().strip()
        self.uso = uso_concreto.lower().strip()
        self.cantera = cantera
        self.fecha = fecha

        self.pasa_200_porc = round(((self.m1 - self.m2) / self.m1) * 100.0, 2) if self.m1 > 0 else 0.0

        if self.tipo == "fino":
            self.limite_norma = 3.0 if "abrasion" in self.uso else 5.0
        else:
            self.limite_norma = 1.5 if "triturado" in self.uso else 1.0

        self.cumple = self.pasa_200_porc <= self.limite_norma

    def diagnostico_tecnico(self) -> str:
        return (
            f"=== MATERIAL MÁS FINO QUE MALLA N.° 200 (75 µm) POR LAVADO ===\n"
            f"Material: {self.tipo.upper()} ({self.cantera}) | Uso: {self.uso}\n"
            f"Masa seca antes del lavado (B): {self.m1:.1f} g | Masa seca tras lavado (C): {self.m2:.1f} g\n"
            f"• Porcentaje que pasa malla N.° 200: {self.pasa_200_porc:.2f} %\n"
            f"• Límite normado NTP 400.037 / ASTM C33: <= {self.limite_norma:.1f} %\n"
            f"DICTAMEN: " + ("CONFORME" if self.cumple else "EXCEDE LÍMITE NORMADO")
        )


class AbrasionLosAngeles:
    """Resistencia al desgaste por abrasión en máquina de Los Ángeles (NTP 400.019 / ASTM C131-20)."""

    ESFERAS_POR_GRADACION = {
        "A": (12, "5000 ± 25 g"),
        "B": (11, "4580 ± 25 g"),
        "C": (8, "3330 ± 20 g"),
        "D": (6, "2500 ± 15 g"),
    }

    def __init__(
        self,
        gradacion: str = "B",
        masa_inicial_g: float = 5000.0,
        masa_retenida_tamiz12_g: float = 3850.0,
        cantera: str = "Cantera en estudio",
        fecha: str = "2026-11-11",
        revoluciones: int = 500,
        **kwargs,
    ):
        self.revoluciones = revoluciones
        self.gradacion = gradacion.upper().strip()
        self.mi = float(masa_inicial_g)
        self.mf = float(masa_retenida_tamiz12_g)
        self.cantera = cantera
        self.fecha = fecha

        self.n_esferas, self.masa_carga_esferas = self.ESFERAS_POR_GRADACION.get(
            self.gradacion, (11, "4580 ± 25 g")
        )
        self.desgaste_porc = round(((self.mi - self.mf) / self.mi) * 100.0, 2) if self.mi > 0 else 0.0

        # Criterio oficial NTP 400.037:2025 num. 11.1.1 (excepciones 11.1.3 y 11.4.1; Anexo B.2 para f'c >= 210 kg/cm²) / ASTM C33:
        # Máximo 50 % para concreto general. MTC EG-2013 fija <= 40 % para afirmados/bases viales.
        self.cumple_concreto_ntp = self.desgaste_porc <= 50.0
        self.cumple_concreto_general = self.cumple_concreto_ntp
        self.cumple_vial_mtc = self.desgaste_porc <= 40.0

    def diagnostico_tecnico(self) -> str:
        t_min = round(self.revoluciones / 33.0, 1)
        t_max = round(self.revoluciones / 30.0, 1)
        return (
            f"=== DESGASTE POR ABRASIÓN LOS ÁNGELES (NTP 400.019:2020 / ASTM C131-20) ===\n"
            f"Cantera: {self.cantera} | Gradación: {self.gradacion} ({self.n_esferas} esferas de 46–48 mm | {self.masa_carga_esferas})\n"
            f"Revoluciones: {self.revoluciones} (a 30–33 rpm, ≈ {t_min:.1f}–{t_max:.1f} min) | Masa inicial: {self.mi:.1f} g | Masa retenida N.° 12: {self.mf:.1f} g\n"
            f"• Porcentaje de Pérdida por Desgaste: {self.desgaste_porc:.2f} %  [Informar ASTM: {round(self.desgaste_porc)} %]\n"
            f"• Criterio NTP 400.037:2025 num. 11.1.1 (concreto general <= 50 %; Anexo B.2 para f'c >= 210 kg/cm²): "
            + ("CONFORME" if self.cumple_concreto_ntp else "NO CUMPLE (> 50 %)")
            + f"\n• Referencia vial MTC EG-2013 (Bases/carpetas asfálticas <= 40 %): "
            + ("CONFORME" if self.cumple_vial_mtc else "NO APTO PARA BASE VIAL (> 40 %)")
        )
