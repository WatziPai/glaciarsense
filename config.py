"""
config.py
=========
Todas las constantes editables y parámetros del proyecto GlaciarSense.

Distingue claramente entre:
  - Dato referencial (fuente científica citada con licencia o informe)
  - Estimación (cálculo basado en fórmulas empíricas)
  - Simulación (escenario didáctico con supuestos explícitos)
"""
from pathlib import Path

# ----------------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "best.pt"      # pesos YOLOv8 (opcional)
SAMPLES_DIR = BASE_DIR / "sample_images"
DATA_DIR = BASE_DIR / "data"                      # datos GIS y registros WGMS/RGI

# ----------------------------------------------------------------------------
# Imágenes
# ----------------------------------------------------------------------------
MAX_IMAGE_SIDE = 1280      # px: se reduce si es más grande (velocidad)
MIN_IMAGE_SIDE = 32        # px: menos que esto no es analizable
MAX_FILE_MB = 15

# ----------------------------------------------------------------------------
# Clases
# ----------------------------------------------------------------------------
CLASSES = ("black_carbon", "dust", "meltwater_pool", "clean_ice")
CONTAMINANTS = ("black_carbon", "dust", "meltwater_pool")

# Etiquetas legibles para la interfaz
LABELS_ES = {
    "black_carbon": "Carbono negro (hollin)",
    "dust": "Polvo mineral",
    "meltwater_pool": "Agua de deshielo",
    "clean_ice": "Hielo limpio",
}

COLORS_RGB = {
    "black_carbon": (214, 40, 57),
    "dust": (244, 162, 97),
    "meltwater_pool": (42, 157, 244),
    "clean_ice": (190, 225, 245),
}


def color_hex(cls: str) -> str:
    r, g, b = COLORS_RGB[cls]
    return f"#{r:02x}{g:02x}{b:02x}"


# ----------------------------------------------------------------------------
# Albedos de referencia
# Valores promedio de literatura glaciológica (Warren & Wiscombe 1980; Cuffey & Paterson 2010).
# Tipo: Dato referencial ilustrativo (promedios de campo).
# ----------------------------------------------------------------------------
ALBEDOS = {
    "clean_ice": 0.45,       # Rango real: 0.35 - 0.70 (hielo desnudo a nieve fresca)
    "dust": 0.25,            # Rango real: 0.20 - 0.35 (polvo mineral y regolito fino)
    "black_carbon": 0.10,    # Rango real: 0.05 - 0.15 (depósitos densos de hollín)
    "meltwater_pool": 0.15,  # Rango real: 0.10 - 0.25 (charcas supraglaciares)
}

# ----------------------------------------------------------------------------
# Modelo de aceleración del deshielo
# ----------------------------------------------------------------------------
K_DEFAULT = 0.6            # sensibilidad del deshielo a la pérdida de albedo
FACTOR_MAX = 1.5           # tope del Factor_Contaminante (+150 % aceleración máxima)

# Escenarios clásicos (compatibilidad)
SCENARIO_K_MULT = (0.5, 1.0, 1.5)       # optimista, central, pesimista
SCENARIO_RATE_MULT = (0.8, 1.0, 1.2)    # optimista, central, pesimista
SCENARIO_NAMES = ("Optimista", "Central", "Pesimista")

# Escenarios Climáticos IPCC AR6 (Trayectorias Socioeconómicas Compartidas)
# NOTA EDUCATIVA: Son simplificaciones didácticas que aproximan el calentamiento
# y su forzamiento sobre las tasas históricas de pérdida de área.
SSP_SCENARIOS = {
    "SSP1-2.6": {
        "name": "SSP1-2.6 (Bajas emisiones)",
        "rate_mult": 0.85,
        "k_mult": 0.75,
        "desc": "Transición sostenible con descarbonización acelerada. Calentamiento contenido ~1.8 °C hacia 2100.",
        "fuente": "IPCC AR6 WGI / WGII",
        "tipo": "Escenario de proyección",
    },
    "SSP2-4.5": {
        "name": "SSP2-4.5 (Emisiones intermedias)",
        "rate_mult": 1.15,
        "k_mult": 1.00,
        "desc": "Trayectoria tendencial con compromisos climáticos actuales. Calentamiento ~2.7 °C hacia 2100.",
        "fuente": "IPCC AR6 WGI / WGII",
        "tipo": "Escenario de proyección",
    },
    "SSP5-8.5": {
        "name": "SSP5-8.5 (Altas emisiones)",
        "rate_mult": 1.55,
        "k_mult": 1.35,
        "desc": "Desarrollo basado en combustibles fósiles sin mitigación. Calentamiento >4.4 °C hacia 2100.",
        "fuente": "IPCC AR6 WGI / WGII",
        "tipo": "Escenario de proyección",
    },
}

# Parámetros para Simulación Monte Carlo de Incertidumbre
MC_RUNS = 1000
MC_K_UNCERTAINTY = 0.25       # Coeficiente de variación (CV = 25%) para k
MC_RATE_UNCERTAINTY = 0.20    # CV = 20% para la tasa histórica
MC_ALBEDO_UNCERTAINTY = 0.10  # CV = 10% para cada albedo de referencia

HORIZONS = (5, 10, 20)                  # años de proyección en el mapa
HORIZON_COLORS = {0: "#00e5ff", 5: "#ffd60a", 10: "#ff8c00", 20: "#e63946"}

# ----------------------------------------------------------------------------
# Segmentación por color (HSV de OpenCV: H 0-179, S 0-255, V 0-255)
# ----------------------------------------------------------------------------
HSV_BLACK_V_MAX = 60                       # muy oscuro -> carbono negro
HSV_MELT = dict(h_min=90, h_max=130, s_min=60, v_min=60)      # azul saturado
HSV_DUST = dict(h_min=5, h_max=35, s_min=40, v_min=60)        # marrón/ocre
HSV_DUST_GRAY = dict(s_max=40, v_min=60, v_max=125)           # gris sucio
HSV_GREEN = dict(h_min=36, h_max=85, s_min=60, v_min=40)      # vegetación
MORPH_KERNEL = 5                           # limpieza de ruido (px)
GREEN_MAX_FRACTION = 0.50                  # si hay más verde, no parece glaciar

# ----------------------------------------------------------------------------
# GIS
# ----------------------------------------------------------------------------
EPSG_WGS84 = 4326
GENERIC_RATE_PCT_PER_YEAR = 1.0            # % del área actual perdido por año
MIN_GLACIER_AREA_M2 = 100.0                # 0.0001 km² umbral de extinción técnica

# Valores APROXIMADOS e ILUSTRATIVOS para la demo (editables en la app).
# Fuentes reales de referencia:
#   - INAIGEM / ANA (Perú) - Inventario Nacional de Glaciares y Lagunas.
#   - WGMS (World Glacier Monitoring Service, Fluctuations of Glaciers).
GLACIER_PRESETS = {
    "Quelccaya (Perú)": dict(
        lat=-13.93, lon=-70.83, area_km2=42.0, rate_km2=0.35,
        fuente="INAIGEM / Thompson et al. (Science 2013) + Vector GeoJSON",
        tipo="Dato de inventario con contorno digitalizado"
    ),
    "Pastoruri (Perú)": dict(
        lat=-9.90, lon=-77.18, area_km2=1.4, rate_km2=0.06,
        fuente="INAIGEM - Inventario Cordillera Blanca + Vector GeoJSON",
        tipo="Dato de inventario con contorno digitalizado"
    ),
    "Coropuna (Perú)": dict(
        lat=-15.52, lon=-72.65, area_km2=40.0, rate_km2=0.50,
        fuente="INAIGEM - Cordillera Ampato",
        tipo="Dato referencial (elipse paramétrica)"
    ),
    "Personalizado": dict(
        lat=-13.93, lon=-70.83, area_km2=10.0, rate_km2=0.10,
        fuente="Valores definidos por el usuario",
        tipo="Estimación personalizada"
    ),
}
DEFAULT_PRESET = "Quelccaya (Perú)"
