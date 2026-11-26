"""Módulo de ensayos de cemento hidráulico y yeso.

Implementa:
- Consistencia normal del cemento (NTP 334.074 / ASTM C187-23)
- Tiempo de fraguado con aguja de Vicat (NTP 334.006 / ASTM C191-21)
- Criterios normativos verificados: NTP 334.009:2025 Tabla 3 nota D (45–375 min inicial) y NTP 334.090:2025 Tabla 2 nota B (45–420 min inicial)
- Tiempo de fraguado del yeso: cuchillo (EN 13279-2) y Vicat (ASTM C472 / NTP 239.651)
"""

from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


class FraguadoVicatCemento:
    """Ensayo de tiempo de fraguado del cemento hidráulico con aguja de Vicat."""

    def __init__(
        self,
        tiempos_min: Union[Dict[float, float], List[float], None] = None,
        penetraciones_mm: Optional[List[float]] = None,
        masa_cemento_g: float = 650.0,
        agua_consistencia_porc: float = 27.5,
        tipo_cemento: str = "Cemento Portland Puzolánico Tipo IP",
        categoria_normativa: Optional[str] = None,
        marca_lote: str = "Yura / Rumi",
        temp_ambiente_c: float = 23.0,
        humedad_relativa_porc: float = 65.0,
        fecha: str = "2026-11-11",
        muestra_id: str = "TC-B-CE-01",
        lecturas_vicat: Optional[Dict[float, float]] = None,
    ):
        """Inicializa el ensayo de fraguado Vicat.

        Acepta diccionario `{tiempo_min: penetracion_mm}` o listas paralelas `tiempos_min` y `penetraciones_mm`.
        """
        datos_dict = lecturas_vicat if lecturas_vicat is not None else (
            tiempos_min if isinstance(tiempos_min, dict) else None
        )

        if datos_dict is not None:
            self.tiempos = [float(t) for t in datos_dict.keys()]
            self.penetraciones = [float(p) for p in datos_dict.values()]
        elif tiempos_min is not None and penetraciones_mm is not None:
            if len(tiempos_min) != len(penetraciones_mm):
                raise ValueError("Las listas de tiempos y penetraciones deben tener la misma longitud.")
            self.tiempos = [float(t) for t in tiempos_min]
            self.penetraciones = [float(p) for p in penetraciones_mm]
        else:
            raise ValueError("Debe proporcionar `lecturas_vicat={t: p}` o `tiempos_min` y `penetraciones_mm`.")

        self.masa_cemento = float(masa_cemento_g)
        self.agua_porc = float(agua_consistencia_porc)
        self.vol_agua_ml = round((self.masa_cemento * self.agua_porc) / 100.0, 1)
        self.tipo_cemento = tipo_cemento
        self.marca_lote = marca_lote
        self.temp = float(temp_ambiente_c)
        self.hr = float(humedad_relativa_porc)
        self.fecha = fecha
        self.muestra_id = muestra_id

        # Determinar categoría normativa para fraguado inicial:
        # NTP 334.090 (Adicionados IP, IS, IL, IPM): máx 7 h = 420 min
        # NTP 334.009 (Portland I a V): máx 375 min
        if categoria_normativa:
            self.categoria_normativa = categoria_normativa.lower().strip()
        else:
            txt = tipo_cemento.upper()
            if any(tok in txt for tok in ["IP", "IPM", "IS", "IL", "ADICIONADO", "PUZOL"]):
                self.categoria_normativa = "adicionado"
            else:
                self.categoria_normativa = "portland"

        self.max_inicial_norma = 420.0 if self.categoria_normativa == "adicionado" else 375.0
        self.min_inicial_norma = 45.0

        self._procesar()

    def _procesar(self):
        """Calcula el fraguado inicial (25 mm por interpolación ASTM C191) y registra el final."""
        df_lecturas = pd.DataFrame({
            "Tiempo (min)": self.tiempos,
            "Penetracion (mm)": self.penetraciones
        }).sort_values("Tiempo (min)").reset_index(drop=True)

        self.df = df_lecturas

        t_arr = df_lecturas["Tiempo (min)"].values
        p_arr = df_lecturas["Penetracion (mm)"].values

        # 1. Fraguado inicial: tiempo a 25.0 mm (ASTM C191-21 num. 11.1)
        self.fraguado_inicial_exacto_min = None
        for i in range(len(p_arr) - 1):
            p1, p2 = p_arr[i], p_arr[i + 1]
            t1, t2 = t_arr[i], t_arr[i + 1]
            if (p1 >= 25.0 and p2 <= 25.0) or (p1 <= 25.0 and p2 >= 25.0):
                if p1 == p2:
                    self.fraguado_inicial_exacto_min = float(t1)
                else:
                    # Fórmula oficial ASTM C191-21 num. 11.1: ((H - E)/(C - D))*(C - 25) + E
                    self.fraguado_inicial_exacto_min = float(t1 + ((p1 - 25.0) / (p1 - p2)) * (t2 - t1))
                break

        if self.fraguado_inicial_exacto_min is None:
            self.fraguado_inicial_exacto_min = float(t_arr[-1] if p_arr[-1] < 25.0 else t_arr[0])

        # Redondear al minuto entero (ASTM C191-21 num. 11.1)
        self.fraguado_inicial_min = float(round(self.fraguado_inicial_exacto_min))

        # 2. Fraguado final: primera lectura <= 0.5 mm (sin huella circular completa), redondeada a 5 min (num. 11.2)
        final_idx = np.where(p_arr <= 0.5)[0]
        raw_final = float(t_arr[final_idx[0]]) if len(final_idx) > 0 else float(t_arr[-1])
        self.fraguado_final_exacto_min = raw_final
        self.fraguado_final_min = float(5 * round(raw_final / 5.0))

        # 3. Criterios normativos de aceptación (sobre FRAGUADO INICIAL exclusivamente)
        # Fuente: NTP 334.009:2025 Tabla 3 nota D (Portland: 45–375 min) / NTP 334.090:2025 Tabla 2 nota B (Adicionado: 45–420 min)
        # Ninguna norma vigente fija límite de aceptación para el fraguado final; se informa solo como dato.
        self.cumple_inicial = self.min_inicial_norma <= self.fraguado_inicial_min <= self.max_inicial_norma
        self.cumple_final = True  # Sin requisito normado para fraguado final
        self.cumple_norma = self.cumple_inicial

        # Alias para compatibilidad
        self.tiempos_min = self.tiempos
        self.penetraciones_mm = self.penetraciones
        self.tiempo_inicial_min = self.fraguado_inicial_min
        self.tiempo_final_min = self.fraguado_final_min
        self.agua_normal_porc = self.agua_porc
        self.agua_normal_ml = self.vol_agua_ml

    def diagnostico_tecnico(self) -> str:
        norma_esp = (
            "NTP 334.090:2025 Tabla 2 nota B (Cementos Adicionados)"
            if self.categoria_normativa == "adicionado"
            else "NTP 334.009:2025 Tabla 3 nota D (Cemento Portland I–V)"
        )
        agua_redondeada = round(self.agua_porc * 2.0) / 2.0  # Aprox a 0,5 % según ASTM C187 num. 8.1

        lineas = [
            f"=== EVALUACIÓN NORMATIVA — TIEMPO DE FRAGUADO VICAT (ASTM C191 / NTP 334.006) ===",
            f"Cemento: {self.tipo_cemento} ({self.marca_lote}) | Muestra: {self.muestra_id}",
            f"Especificación aplicable: {norma_esp}",
            f"Masa cemento: {self.masa_cemento:.1f} g | Agua consistencia normal: {self.agua_porc:.1f} % ({self.vol_agua_ml:.1f} mL) [Informar C187: {agua_redondeada:.1f} %]",
            f"Condiciones ambientales: Temp = {self.temp:.1f} °C (Norma: 23 ± 2 °C) | HR = {self.hr:.0f} %",
            "",
            "RESULTADOS DEL ENSAYO:",
            f"• Fraguado Inicial (25 mm): {self.fraguado_inicial_min:.0f} min ({self.fraguado_inicial_min/60:.2f} h) [interpolado: {self.fraguado_inicial_exacto_min:.1f} min]",
            f"  -> Criterio único de aceptación ({self.min_inicial_norma:.0f} min <= t_i <= {self.max_inicial_norma:.0f} min): "
            + ("CONFORME" if self.cumple_inicial else "NO CUMPLE (fuera de tolerancia inicial)"),
            f"• Fraguado Final (sin huella circular): {self.fraguado_final_min:.0f} min ({self.fraguado_final_min/60:.2f} h)  [Sin límite normado; solo se informa]",
            "",
            "DICTAMEN FINAL: " + ("APROBADO — CUMPLE ESPECIFICACIONES DE FRAGUADO" if self.cumple_norma else "OBSERVADO"),
        ]
        return "\n".join(lineas)
