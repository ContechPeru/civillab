"""CivilLab UNSAAC — Suite de protocolos y ensayos de laboratorio de ingeniería civil.

Módulos de cálculo normativo según NTP, ASTM y RNE.
Universidad Nacional de San Antonio Abad del Cusco (UNSAAC).
"""

from .aggregates import (
    Granulometria,
    PesoUnitario,
    PesoEspecificoAbsorcion,
    ContenidoHumedad,
    MaterialPasa200,
    AbrasionLosAngeles,
)
from .cement import FraguadoVicatCemento
from .concrete import ConcretoFresco, CompresionBriquetas
from .masonry import (
    LadrilloCalidad,
    CompresionPrismasMortero,
    EnsayoVaciosLadrillo,
    CompresionLadrilloUnidad,
)
from .wood import HumedadMadera
from .mix_design import DisenoMezclaACI211, resistencia_promedio_requerida_e060
from .export import (
    exportar_ficha_granulometria_excel,
    exportar_ficha_compresion_concreto_excel,
    exportar_ficha_ladrillos_e070_excel,
)
from .plotting import (
    graficar_granulometria,
    graficar_comparacion_husos,
    graficar_fraguado_vicat,
    graficar_rotura_compresion,
    graficar_calidad_ladrillo,
    graficar_humedad_madera,
)
from .standards import (
    HUSO_AGREGADO_FINO,
    HUSOS_AGREGADO_GRUESO,
    HUSOS_DESCRIPCION,
    HUSOS_METADATOS,
    HUSOS_POR_TMN,
    TAMICES_INFO,
    TAMICES_MODULO_FINURA_MM,
    catalogo_husos_df,
)

__version__ = "1.0.0"
__author__ = "Jorge Luis Dueñas Ttito"

__all__ = [
    # Diseño de mezclas
    "DisenoMezclaACI211",
    "resistencia_promedio_requerida_e060",
    # Agregados
    "Granulometria",
    "PesoUnitario",
    "PesoEspecificoAbsorcion",
    "ContenidoHumedad",
    "MaterialPasa200",
    "AbrasionLosAngeles",
    # Cemento
    "FraguadoVicatCemento",
    # Concreto
    "ConcretoFresco",
    "CompresionBriquetas",
    # Albañilería
    "LadrilloCalidad",
    "CompresionPrismasMortero",
    "EnsayoVaciosLadrillo",
    "CompresionLadrilloUnidad",
    # Madera
    "HumedadMadera",
    # Gráficos
    "graficar_granulometria",
    "graficar_comparacion_husos",
    "graficar_fraguado_vicat",
    "graficar_rotura_compresion",
    "graficar_calidad_ladrillo",
    "graficar_humedad_madera",
    # Reportes Excel
    "exportar_ficha_granulometria_excel",
    "exportar_ficha_compresion_concreto_excel",
    "exportar_ficha_ladrillos_e070_excel",
    # Constantes y Catálogo de Husos
    "HUSO_AGREGADO_FINO",
    "HUSOS_AGREGADO_GRUESO",
    "HUSOS_DESCRIPCION",
    "HUSOS_METADATOS",
    "HUSOS_POR_TMN",
    "TAMICES_INFO",
    "TAMICES_MODULO_FINURA_MM",
    "catalogo_husos_df",
]
