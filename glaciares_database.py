"""
glaciares_database.py
=====================
Base de datos de glaciares conocidos para selección interactiva en el mapa.
"""

# Base de datos de glaciares andinos y globales conocidos
GLACIARES_CONOCIDOS = {
    # Perú
    "Pastoruri (Perú)": {
        "lat": -9.92,
        "lon": -77.27,
        "area_km2": 1.57,  # 2020
        "rate_km2": 0.08,
        "pais": "Perú",
        "cordillera": "Blanca",
        "tipo": "Glaciar de montaña",
        "fuente": "INAIGEM 2020"
    },
    "Artesonraju (Perú)": {
        "lat": -8.95,
        "lon": -77.63,
        "area_km2": 2.3,
        "rate_km2": 0.12,
        "pais": "Perú",
        "cordillera": "Blanca",
        "tipo": "Glaciar de montaña",
        "fuente": "INAIGEM 2018"
    },
    "Quelccaya (Perú)": {
        "lat": -13.93,
        "lon": -70.83,
        "area_km2": 42.0,
        "rate_km2": 0.35,
        "pais": "Perú",
        "cordillera": "Vilcanota",
        "tipo": "Casquete glaciar",
        "fuente": "INAIGEM / Thompson et al. (Science 2013)"
    },
    "Coropuna (Perú)": {
        "lat": -15.52,
        "lon": -72.65,
        "area_km2": 44.0,
        "rate_km2": 0.40,
        "pais": "Perú",
        "cordillera": "Ampato",
        "tipo": "Volcán glaciado",
        "fuente": "INAIGEM 2016"
    },
    
    # Bolivia
    "Chacaltaya (Bolivia)": {
        "lat": -16.35,
        "lon": -68.13,
        "area_km2": 0.0,  # Extinto 2009
        "rate_km2": 0.0,
        "pais": "Bolivia",
        "cordillera": "Real",
        "tipo": "Glaciar extinto",
        "fuente": "Rabatel et al. 2006"
    },
    "Zongo (Bolivia)": {
        "lat": -16.27,
        "lon": -68.17,
        "area_km2": 2.4,
        "rate_km2": 0.10,
        "pais": "Bolivia",
        "cordillera": "Real",
        "tipo": "Glaciar de montaña",
        "fuente": "IRD 2019"
    },
    
    # Ecuador
    "Antisana (Ecuador)": {
        "lat": -0.48,
        "lon": -78.14,
        "area_km2": 10.1,
        "rate_km2": 0.25,
        "pais": "Ecuador",
        "cordillera": "Andes Ecuatoriales",
        "tipo": "Volcán glaciado",
        "fuente": "INAMHI 2018"
    },
    "Cotopaxi (Ecuador)": {
        "lat": -0.68,
        "lon": -78.44,
        "area_km2": 14.6,
        "rate_km2": 0.30,
        "pais": "Ecuador",
        "cordillera": "Andes Ecuatoriales",
        "tipo": "Volcán glaciado",
        "fuente": "INAMHI 2017"
    },
    
    # Colombia
    "Santa Isabel (Colombia)": {
        "lat": 4.82,
        "lon": -75.37,
        "area_km2": 1.8,
        "rate_km2": 0.09,
        "pais": "Colombia",
        "cordillera": "Central",
        "tipo": "Glaciar de montaña",
        "fuente": "IDEAM 2020"
    },
    "Nevado del Ruiz (Colombia)": {
        "lat": 4.89,
        "lon": -75.32,
        "area_km2": 8.9,
        "rate_km2": 0.18,
        "pais": "Colombia",
        "cordillera": "Central",
        "tipo": "Volcán glaciado",
        "fuente": "IDEAM 2019"
    },
    
    # Argentina
    "Upsala (Argentina)": {
        "lat": -49.88,
        "lon": -73.30,
        "area_km2": 595.0,
        "rate_km2": 3.5,
        "pais": "Argentina",
        "cordillera": "Patagonia",
        "tipo": "Glaciar de descarga",
        "fuente": "IANIGLA 2020"
    },
    "Perito Moreno (Argentina)": {
        "lat": -50.47,
        "lon": -73.03,
        "area_km2": 254.0,
        "rate_km2": 0.1,  # Estable
        "pais": "Argentina",
        "cordillera": "Patagonia",
        "tipo": "Glaciar de descarga",
        "fuente": "IANIGLA 2020"
    },
    
    # Chile
    "San Rafael (Chile)": {
        "lat": -46.66,
        "lon": -73.85,
        "area_km2": 762.0,
        "rate_km2": 5.2,
        "pais": "Chile",
        "cordillera": "Patagonia Norte",
        "tipo": "Glaciar de descarga",
        "fuente": "DGA 2019"
    },
    "Echaurren (Chile)": {
        "lat": -33.58,
        "lon": -70.13,
        "area_km2": 0.4,
        "rate_km2": 0.02,
        "pais": "Chile",
        "cordillera": "Andes Centrales",
        "tipo": "Glaciar de montaña",
        "fuente": "DGA 2020"
    },
}

def get_glaciar_info(nombre):
    """Obtiene información de un glaciar por nombre."""
    return GLACIARES_CONOCIDOS.get(nombre)

def get_glaciares_por_pais(pais):
    """Obtiene todos los glaciares de un país."""
    return {k: v for k, v in GLACIARES_CONOCIDOS.items() if v["pais"] == pais}

def get_glaciares_activos():
    """Obtiene solo glaciares con área > 0 (no extintos)."""
    return {k: v for k, v in GLACIARES_CONOCIDOS.items() if v["area_km2"] > 0}

def get_paises():
    """Obtiene lista de países con glaciares."""
    return sorted(set(v["pais"] for v in GLACIARES_CONOCIDOS.values()))
