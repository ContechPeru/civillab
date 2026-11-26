"""Módulo de ensayos de madera estructural según NTP 251.010 y RNE E.010.

Implementa:
- Contenido de humedad en madera por método de secado en horno (ASTM D4442 / NTP 251.010)
- Evaluación de límites normativos según RNE E.010 Madera
"""

from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


class HumedadMadera:
    """Determinación del contenido de humedad de la madera por método del horno."""

    def __init__(
        self,
        probetas: List[Dict[str, Union[str, float]]],
        especie: str = "Eucalipto (Eucalyptus globulus) / Pino",
        procedencia: str = "Valle Sagrado / Cusco",
        uso_previsto: str = "Estructural aserrada",
        fecha: str = "2026-10-29",
    ):
        """
        probetas: lista de dicts con:
        - 'codigo': str
        - 'masa_humeda_g': float (masa inicial)
        - 'masa_seca_g': float (masa constante a 103 ± 2 °C)
        uso_previsto: 'Estructural aserrada' (máx 22 %) o 'Laminada encolada' (8-12 %)
        """
        self.probetas = probetas
        self.especie = especie
        self.procedencia = procedencia
        self.uso_previsto = uso_previsto
        self.fecha = fecha

        self._procesar()

    def _procesar(self):
        filas = []
        for p in self.probetas:
            mh = float(p.get("masa_humeda_g", 0.0))
            ms = float(p.get("masa_seca_g", 0.0))

            ch_porc = ((mh - ms) / ms * 100.0) if ms > 0 else 0.0

            filas.append({
                "codigo": p.get("codigo", "PROB-01"),
                "masa_humeda_g": mh,
                "masa_seca_g": ms,
                "agua_evaporada_g": round(mh - ms, 2),
                "contenido_humedad_porc": round(ch_porc, 2),
            })

        self.df = pd.DataFrame(filas)
        valores = self.df["contenido_humedad_porc"].values
        self.ch_promedio = round(float(np.mean(valores)), 2)
        self.ch_max = round(float(np.max(valores)), 2)

        # Criterio RNE E.010 (Capítulo 2, num. 2.1.2)
        if "laminada" in self.uso_previsto.lower():
            self.cumple_norma = 8.0 <= self.ch_promedio <= 12.0
            self.exigencia = "8 % a 12 % (Madera laminada encolada)"
        else:
            self.cumple_norma = self.ch_promedio <= 22.0
            self.exigencia = "Máximo 22 % (Madera estructural aserrada)"

    def diagnostico_tecnico(self) -> str:
        return (
            f"=== EVALUACIÓN DE HUMEDAD EN MADERA (NTP 251.010 / RNE E.010) ===\n"
            f"Especie: {self.especie} | Procedencia: {self.procedencia}\n"
            f"Uso previsto: {self.uso_previsto} | Probetas ensayadas: {len(self.df)}\n"
            f"• Contenido de humedad promedio: {self.ch_promedio:.2f} %\n"
            f"• Contenido de humedad máximo:   {self.ch_max:.2f} %\n"
            f"• Requisito RNE E.010: {self.exigencia}\n"
            f"\nDICTAMEN NORMATIVO: "
            + ("APROBADO — APTA PARA USO ESTRUCTURAL" if self.cumple_norma else "OBSERVADA — REQUIERE SECADO ADICIONAL")
        )
