"""Constantes y especificaciones normativas para agregados y concreto.

Fuentes verificadas contra normas en raw:
- NTP 400.012:2021 / ASTM C136/C136M-19 (Análisis granulométrico)
- NTP 400.037:2025 Tabla 1 y Tabla 3 / ASTM C33/C33M-24 Tabla 3 (Especificaciones de agregados)
- ASTM E11-24 (Tamices de ensayo)
"""

from typing import Dict
import pandas as pd

# Catálogo maestro de aberturas de tamices según ASTM E11 (mm)
TAMICES_INFO = {
    '4"': 100.0,
    '3 1/2"': 90.0,
    '3"': 75.0,
    '2 1/2"': 63.0,
    '2"': 50.0,
    '1 1/2"': 37.5,
    '1"': 25.0,
    '3/4"': 19.0,
    '1/2"': 12.5,
    '3/8"': 9.5,
    '1/4"': 6.3,
    'N° 4': 4.75,
    'N.° 4': 4.75,
    '#4': 4.75,
    'N° 8': 2.36,
    'N.° 8': 2.36,
    '#8': 2.36,
    'N° 12': 1.70,
    'N.° 12': 1.70,
    '#12': 1.70,
    'N° 16': 1.18,
    'N.° 16': 1.18,
    '#16': 1.18,
    'N° 30': 0.600,
    'N.° 30': 0.600,
    '#30': 0.600,
    'N° 50': 0.300,
    'N.° 50': 0.300,
    '#50': 0.300,
    'N° 100': 0.150,
    'N.° 100': 0.150,
    '#100': 0.150,
    'N° 200': 0.075,
    'N.° 200': 0.075,
    '#200': 0.075,
}

# Tamices normalizados que participan en el cálculo del Módulo de Finura (MF)
# Serie Tyler / ASTM C136 num. 9.2 (relación 2:1 desde N° 100 hasta 6"):
TAMICES_MODULO_FINURA_MM = [
    0.150,  # N° 100
    0.300,  # N° 50
    0.600,  # N° 30
    1.18,   # N° 16
    2.36,   # N° 8
    4.75,   # N° 4
    9.5,    # 3/8"
    19.0,   # 3/4"
    37.5,   # 1 1/2"
    75.0,   # 3"
    150.0,  # 6"
]

# ==============================================================================
# HUSOS GRANULOMÉTRICOS NORMADOS SEGÚN NTP 400.037 / ASTM C33/C33M-24
# Formato: {abertura_mm: (min_porc_pasa, max_porc_pasa)}
# ==============================================================================

# Tabla 1 NTP 400.037:2025 / Num. 6.1 ASTM C33-24: Agregado Fino (Huso único)
HUSO_AGREGADO_FINO = {
    9.5: (100.0, 100.0),     # 3/8"
    4.75: (95.0, 100.0),     # N° 4
    2.36: (80.0, 100.0),     # N° 8
    1.18: (50.0, 85.0),      # N° 16
    0.600: (25.0, 60.0),     # N° 30
    0.300: (5.0, 30.0),      # N° 50
    0.150: (0.0, 10.0),      # N° 100
}

# Tabla 3 NTP 400.037:2025 / Tabla 3 ASTM C33/C33M-24: Los 15 Husos de Agregado Grueso
HUSOS_AGREGADO_GRUESO: Dict[str, Dict[float, tuple]] = {
    # --- Husos de tamaño grande (concreto masivo / presas / cimentaciones enormes) ---
    '1': {  # 90 a 37,5 mm (3 1/2" a 1 1/2")
        100.0: (100.0, 100.0),  # 4"
        90.0: (90.0, 100.0),    # 3 1/2"
        63.0: (25.0, 60.0),     # 2 1/2"
        37.5: (0.0, 15.0),      # 1 1/2"
        19.0: (0.0, 5.0),       # 3/4"
    },
    '2': {  # 63 a 37,5 mm (2 1/2" a 1 1/2")
        75.0: (100.0, 100.0),   # 3"
        63.0: (90.0, 100.0),    # 2 1/2"
        50.0: (35.0, 70.0),     # 2"
        37.5: (0.0, 15.0),      # 1 1/2"
        19.0: (0.0, 5.0),       # 3/4"
    },
    '3': {  # 50 a 25,0 mm (2" a 1")
        63.0: (100.0, 100.0),   # 2 1/2"
        50.0: (90.0, 100.0),    # 2"
        37.5: (35.0, 70.0),     # 1 1/2"
        25.0: (0.0, 15.0),      # 1"
        12.5: (0.0, 5.0),       # 1/2"
    },
    '357': {  # 50 a 4,75 mm (2" a N° 4)
        63.0: (100.0, 100.0),   # 2 1/2"
        50.0: (95.0, 100.0),    # 2"
        25.0: (35.0, 70.0),     # 1"
        12.5: (10.0, 30.0),     # 1/2"
        4.75: (0.0, 5.0),       # N° 4
    },
    '4': {  # 37,5 a 19,0 mm (1 1/2" a 3/4")
        50.0: (100.0, 100.0),   # 2"
        37.5: (90.0, 100.0),    # 1 1/2"
        25.0: (20.0, 55.0),     # 1"
        19.0: (0.0, 15.0),      # 3/4"
        9.5: (0.0, 5.0),        # 3/8"
    },
    '467': {  # 37,5 a 4,75 mm (1 1/2" a N° 4)
        50.0: (100.0, 100.0),   # 2"
        37.5: (95.0, 100.0),    # 1 1/2"
        19.0: (35.0, 70.0),     # 3/4"
        9.5: (10.0, 30.0),      # 3/8"
        4.75: (0.0, 5.0),       # N° 4
    },
    # --- Husos de uso común en obras de edificación y concreto armado ---
    '5': {  # 25,0 a 12,5 mm (1" a 1/2")
        37.5: (100.0, 100.0),   # 1 1/2"
        25.0: (90.0, 100.0),    # 1"
        19.0: (20.0, 55.0),     # 3/4"
        12.5: (0.0, 10.0),      # 1/2"
        9.5: (0.0, 5.0),        # 3/8"
    },
    '56': {  # 25,0 a 9,5 mm (1" a 3/8")
        37.5: (100.0, 100.0),   # 1 1/2"
        25.0: (90.0, 100.0),    # 1"
        19.0: (40.0, 85.0),     # 3/4"
        12.5: (10.0, 40.0),     # 1/2"
        9.5: (0.0, 15.0),       # 3/8"
        4.75: (0.0, 5.0),       # N° 4
    },
    '57': {  # 25,0 a 4,75 mm (1" a N° 4)
        37.5: (100.0, 100.0),   # 1 1/2"
        25.0: (95.0, 100.0),    # 1"
        12.5: (25.0, 60.0),     # 1/2"
        4.75: (0.0, 10.0),      # N° 4
        2.36: (0.0, 5.0),       # N° 8
    },
    '6': {  # 19,0 a 9,5 mm (3/4" a 3/8")
        25.0: (100.0, 100.0),   # 1"
        19.0: (90.0, 100.0),    # 3/4"
        12.5: (20.0, 55.0),     # 1/2"
        9.5: (0.0, 15.0),       # 3/8"
        4.75: (0.0, 5.0),       # N° 4
    },
    '67': {  # 19,0 a 4,75 mm (3/4" a N° 4) — Estándar edificación
        25.0: (100.0, 100.0),   # 1"
        19.0: (90.0, 100.0),    # 3/4"
        9.5: (20.0, 55.0),      # 3/8"
        4.75: (0.0, 10.0),      # N° 4
        2.36: (0.0, 5.0),       # N° 8
    },
    '7': {  # 12,5 a 4,75 mm (1/2" a N° 4)
        19.0: (100.0, 100.0),   # 3/4"
        12.5: (90.0, 100.0),    # 1/2"
        9.5: (40.0, 70.0),      # 3/8"
        4.75: (0.0, 15.0),      # N° 4
        2.36: (0.0, 5.0),       # N° 8
    },
    '8': {  # 9,5 a 2,36 mm (3/8" a N° 8)
        12.5: (100.0, 100.0),   # 1/2"
        9.5: (85.0, 100.0),     # 3/8"
        4.75: (10.0, 30.0),     # N° 4
        2.36: (0.0, 10.0),      # N° 8
        1.18: (0.0, 5.0),       # N° 16
    },
    '89': {  # 9,5 a 1,18 mm (3/8" a N° 16)
        12.5: (100.0, 100.0),   # 1/2"
        9.5: (90.0, 100.0),     # 3/8"
        4.75: (20.0, 55.0),     # N° 4
        2.36: (5.0, 30.0),      # N° 8
        1.18: (0.0, 10.0),      # N° 16
        0.300: (0.0, 5.0),      # N° 50
    },
    '9': {  # 4,75 a 1,18 mm (N° 4 a N° 16)
        9.5: (100.0, 100.0),    # 3/8"
        4.75: (85.0, 100.0),    # N° 4
        2.36: (10.0, 40.0),     # N° 8
        1.18: (0.0, 10.0),      # N° 16
        0.300: (0.0, 5.0),      # N° 50
    },
}

HUSOS_DESCRIPCION = {
    '1':   ('90 a 37,5 mm (3 1/2" a 1 1/2")', 'Concreto masivo (presas, grandes cimentaciones)'),
    '2':   ('63 a 37,5 mm (2 1/2" a 1 1/2")', 'Concreto masivo / obras hidráulicas'),
    '3':   ('50 a 25,0 mm (2" a 1")', 'Cimentaciones masivas y obras viales gruesas'),
    '357': ('50 a 4,75 mm (2" a N° 4)', 'Concreto ciclópeo o cimentaciones de gran volumen'),
    '4':   ('37,5 a 19,0 mm (1 1/2" a 3/4")', 'Presas y elementos con poco acero'),
    '467': ('37,5 a 4,75 mm (1 1/2" a N° 4)', 'Zapatas amplias, muros de contención y pavimentos rígidos'),
    '5':   ('25,0 a 12,5 mm (1" a 1/2")', 'Grava clasificada para dosificación combinada'),
    '56':  ('25,0 a 9,5 mm (1" a 3/8")', 'Fracción gruesa intermedia'),
    '57':  ('25,0 a 4,75 mm (1" a N° 4)', 'Uso común en zapatas, vigas anchas y losas macizas'),
    '6':   ('19,0 a 9,5 mm (3/4" a 3/8")', 'Fracción para combinar con gravilla'),
    '67':  ('19,0 a 4,75 mm (3/4" a N° 4)', 'Estándar en edificación (columnas, vigas, aligerados)'),
    '7':   ('12,5 a 4,75 mm (1/2" a N° 4)', 'Placas delgadas, elementos esbeltos y prefabricados'),
    '8':   ('9,5 a 2,36 mm (3/8" a N° 8)', 'Concreto bombeable o relleno de albañilería armada (grout)'),
    '89':  ('9,5 a 1,18 mm (3/8" a N° 16)', 'Microconcreto y concretos de alta fluidez'),
    '9':   ('4,75 a 1,18 mm (N° 4 a N° 16)', 'Concretos muy finos o mezcla con Huso 8 (forma el 89)'),
}

# Mapeo TMN -> husos recomendados (primero los de gradación continua terminados en 7/9)
HUSOS_POR_TMN = {
    '3 1/2"': ['1'],
    '2 1/2"': ['2'],
    '2"':     ['357', '3'],
    '1 1/2"': ['467', '4'],
    '1"':     ['57', '56', '5'],
    '3/4"':   ['67', '6'],
    '1/2"':   ['7'],
    '3/8"':   ['8', '89'],
    'N° 4':   ['9'],
}

HUSOS_METADATOS = {
    '1':   {'tmn': '3 1/2"', 'tmn_mm': 90.0, 'tipo': 'Tamaño grande (masivo)', 'nota': 'Nota B: N° 200 <= 1,0 % (1,5 % sin arcilla/pizarra)'},
    '2':   {'tmn': '2 1/2"', 'tmn_mm': 63.0, 'tipo': 'Tamaño grande (masivo)', 'nota': 'Nota B: N° 200 <= 1,0 % (1,5 % sin arcilla/pizarra)'},
    '3':   {'tmn': '2"',     'tmn_mm': 50.0, 'tipo': 'Fracción gruesa cerrada', 'nota': 'Nota B: N° 200 <= 1,0 % (1,5 % sin arcilla/pizarra)'},
    '357': {'tmn': '2"',     'tmn_mm': 50.0, 'tipo': 'Gradación amplia (hasta N° 4)', 'nota': 'Nota 11: entregar en al menos 2 tamaños separados'},
    '4':   {'tmn': '1 1/2"', 'tmn_mm': 37.5, 'tipo': 'Fracción gruesa cerrada', 'nota': 'Se puede combinar con gravilla si falta finos'},
    '467': {'tmn': '1 1/2"', 'tmn_mm': 37.5, 'tipo': 'Gradación continua (hasta N° 4)', 'nota': 'Nota 11: entregar en al menos 2 tamaños separados'},
    '5':   {'tmn': '1"',     'tmn_mm': 25.0, 'tipo': 'Fracción única (1" a 1/2")', 'nota': 'Menor continuidad granulométrica que el Huso 57'},
    '56':  {'tmn': '1"',     'tmn_mm': 25.0, 'tipo': 'Gradación intermedia (1" a 3/8")', 'nota': 'Alternativa al 57 sin fracción entre 3/8" y N° 4'},
    '57':  {'tmn': '1"',     'tmn_mm': 25.0, 'tipo': 'Gradación continua (hasta N° 4)', 'nota': 'Preferido para TMN 1" en concreto estructural'},
    '6':   {'tmn': '3/4"',   'tmn_mm': 19.0, 'tipo': 'Fracción única (3/4" a 3/8")', 'nota': 'Alternativa si falta fracción 3/8" a N° 4'},
    '67':  {'tmn': '3/4"',   'tmn_mm': 19.0, 'tipo': 'Gradación continua (hasta N° 4)', 'nota': 'Estándar más usado en edificación armada'},
    '7':   {'tmn': '1/2"',   'tmn_mm': 12.5, 'tipo': 'Gradación continua (hasta N° 4)', 'nota': 'Ideal para placas densas o poco espaciamiento'},
    '8':   {'tmn': '3/8"',   'tmn_mm': 9.5,  'tipo': 'Gravilla / grueso fino', 'nota': 'Base para bombeo, prefabricados y grout'},
    '89':  {'tmn': '3/8"',   'tmn_mm': 9.5,  'tipo': 'Gravilla ampliada (3/8" a N° 16)', 'nota': 'Nota A: puede formarse combinando Huso 8 + Huso 9'},
    '9':   {'tmn': 'N° 4',   'tmn_mm': 4.75, 'tipo': 'Agregado muy fino (Nota A)', 'nota': 'Nota A: agregado fino según ASTM; combinable con Huso 8'},
}


def catalogo_husos_df() -> pd.DataFrame:
    """Devuelve un cuadro resumen legible de todos los husos normados ASTM C33 / NTP 400.037."""
    filas = []
    for codigo, (rango, uso) in HUSOS_DESCRIPCION.items():
        meta = HUSOS_METADATOS.get(codigo, {})
        filas.append({
            "Huso N.°": codigo,
            "TMN Asociado": f"{meta.get('tmn', '—')} ({meta.get('tmn_mm', '—')} mm)",
            "Tamaño Nominal": rango,
            "Tipo de Banda": meta.get("tipo", "—"),
            "Uso Recomendado en Obra": uso,
            "Nota Normativa (ASTM C33 / NTP 400.037)": meta.get("nota", "—"),
        })
    return pd.DataFrame(filas)
