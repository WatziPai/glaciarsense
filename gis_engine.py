"""
gis_engine.py
=============
Motor GIS y de modelado físico-matemático (didáctico) para retroceso de glaciares.

Cadena de cálculo:
    cobertura (%) -> albedo efectivo (α_eff) -> aceleración energética (ΔM)
    -> Factor_Contaminante -> Tasa_Ajustada -> Tiempo_Restante (rango e incertidumbre)
    -> Perímetros proyectados a 5, 10 y 20 años (GeoJSON real o elipse en UTM).

Fórmulas:
    α_eff               = Σ (fracción_i × α_i)
    ΔM                  = max((1 − α_eff) / (1 − α_limpio) − 1, 0)
    Factor_Contaminante = clip(k × ΔM, 0, FACTOR_MAX)
    Tasa_Ajustada       = Tasa_Historica × (1 + Factor_Contaminante)
    Tiempo_Restante     = Área_Actual / Tasa_Ajustada (modelo lineal)
    Área(t) [exp]       = Área_0 × exp(-t × Tasa_Ajustada / Área_0)
"""
from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.affinity import rotate, scale, translate
from shapely.geometry import Point, Polygon
from shapely.ops import transform as shp_transform

import config


# ----------------------------------------------------------------------------
# Utilidades y diagnósticos
# ----------------------------------------------------------------------------
def arcgis_disponible() -> bool:
    """True si `arcgis` está instalado en el entorno."""
    return importlib.util.find_spec("arcgis") is not None


def validate_inputs(lat: float, lon: float, area_m2: float, rate_m2: float):
    """Lanza ValueError descriptivo si los parámetros están fuera de rango físico."""
    if not (-90.0 <= lat <= 90.0):
        raise ValueError("La latitud debe estar comprendida entre -90 y 90 grados.")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError("La longitud debe estar comprendida entre -180 y 180 grados.")
    if area_m2 < 0:
        raise ValueError("El área del glaciar no puede ser negativa.")
    if rate_m2 < 0:
        raise ValueError("La tasa histórica de retroceso no puede ser negativa.")


def default_rate_m2(area_m2: float) -> float:
    """Tasa genérica ilustrativa: 1 % del área actual por año."""
    return area_m2 * config.GENERIC_RATE_PCT_PER_YEAR / 100.0


def utm_epsg(lat: float, lon: float) -> int:
    """Código EPSG de la zona UTM métrica correspondiente a (lat, lon)."""
    zone = min(max(int((lon + 180) // 6) + 1, 1), 60)
    return (32600 if lat >= 0 else 32700) + zone


# ----------------------------------------------------------------------------
# Albedo y aceleración por contaminantes
# ----------------------------------------------------------------------------
def albedo_summary(pct: dict, albedos: dict | None = None) -> dict:
    """
    Calcula el albedo efectivo como media ponderada de las coberturas superficiales
    y la pérdida de reflectancia solar frente a hielo limpio de referencia.
    """
    albedos = albedos or config.ALBEDOS
    total = sum(pct.get(c, 0.0) for c in albedos)
    if total <= 0:
        raise ValueError("Los porcientajes de cobertura válidos suman 0.")
    alpha_eff = sum(pct.get(c, 0.0) / total * a for c, a in albedos.items())
    clean = albedos["clean_ice"]
    return dict(
        alpha_eff=float(alpha_eff),
        alpha_clean=float(clean),
        loss_abs=float(clean - alpha_eff),
        loss_pct=float((clean - alpha_eff) / clean * 100.0),
    )


def melt_acceleration(alpha_eff: float, alpha_clean: float) -> float:
    """
    ΔM: Aumento fraccional de la energía solar absorbida frente a hielo limpio.
    ΔM = ((1 - α_eff) / (1 - α_limpio)) - 1  (con límite inferior en 0.0).
    """
    if alpha_clean >= 1.0:
        return 0.0
    val = (1.0 - alpha_eff) / (1.0 - alpha_clean) - 1.0
    return float(max(val, 0.0))


def contaminant_factor(delta_m: float, k: float) -> float:
    """
    Factor_Contaminante = clip(k * ΔM, 0, FACTOR_MAX).
    Modela el forzamiento adicional sobre la tasa de retroceso.
    """
    return float(np.clip(k * delta_m, 0.0, config.FACTOR_MAX))


# ----------------------------------------------------------------------------
# Escenarios clásicos y climáticos SSP (IPCC AR6)
# ----------------------------------------------------------------------------
@dataclass
class Scenario:
    name: str
    k: float
    rate_hist: float       # m²/año
    factor: float          # Factor_Contaminante
    rate_adj: float        # m²/año
    years: float           # años restantes (inf si no hay pérdida o 0 si ya desapareció)
    year_end: int | None   # año calendario estimado de extinción
    tipo: str = "Escenario de proyección"
    descripcion: str = ""


def compute_scenarios(
    area_m2: float,
    rate_hist_m2: float,
    alpha_eff: float,
    alpha_clean: float,
    k: float,
    include_ssp: bool = False,
) -> list[Scenario]:
    """
    Calcula escenarios clásicos (Optimista, Central, Pesimista) y opcionalmente
    los escenarios climáticos SSP del IPCC AR6 como multiplicadores didácticos.
    """
    validate_inputs(0, 0, area_m2, rate_hist_m2)

    # Caso límite: glaciar extinto o área despreciable
    if area_m2 <= config.MIN_GLACIER_AREA_M2:
        return [
            Scenario("Actual (Extinto)", k, rate_hist_m2, 0.0, 0.0, 0.0, date.today().year,
                     "Dato límite", "Glaciar con área inferior al umbral técnico de permanencia.")
        ]

    dm = melt_acceleration(alpha_eff, alpha_clean)
    out: list[Scenario] = []

    # 1. Escenarios de sensibilidad de contaminantes (Optimista, Central, Pesimista)
    for name, km, rm in zip(config.SCENARIO_NAMES, config.SCENARIO_K_MULT, config.SCENARIO_RATE_MULT):
        k_s = k * km
        rate_s = rate_hist_m2 * rm
        factor = contaminant_factor(dm, k_s)
        rate_adj = rate_s * (1.0 + factor)

        if rate_adj <= 0:
            years = math.inf
            year_end = None
        else:
            years = area_m2 / rate_adj
            year_end = date.today().year + int(math.ceil(years)) if math.isfinite(years) else None

        desc = f"Sensibilidad k={k_s:.2f}, tasa base={rate_s / 1e6:.3f} km²/año"
        out.append(Scenario(name, k_s, rate_s, factor, rate_adj, years, year_end, "Escenario de proyección", desc))

    # 2. Escenarios SSP (si se solicitan)
    if include_ssp:
        for ssp_key, data in config.SSP_SCENARIOS.items():
            k_s = k * data["k_mult"]
            rate_s = rate_hist_m2 * data["rate_mult"]
            factor = contaminant_factor(dm, k_s)
            rate_adj = rate_s * (1.0 + factor)

            if rate_adj <= 0:
                years = math.inf
                year_end = None
            else:
                years = area_m2 / rate_adj
                year_end = date.today().year + int(math.ceil(years)) if math.isfinite(years) else None

            out.append(Scenario(
                name=data["name"],
                k=k_s,
                rate_hist=rate_s,
                factor=factor,
                rate_adj=rate_adj,
                years=years,
                year_end=year_end,
                tipo=data["tipo"],
                descripcion=data["desc"],
            ))

    return out


# ----------------------------------------------------------------------------
# Curvas temporales de retroceso (Lineal vs. Decaimiento Exponencial No Lineal)
# ----------------------------------------------------------------------------
def area_curve(
    area_m2: float,
    rate_adj_m2: float,
    years: np.ndarray,
    model: str = "linear",
) -> np.ndarray:
    """
    Calcula el área restante en cada paso de tiempo según el modelo elegido:
      - 'linear': A(t) = max(A0 - rate_adj * t, 0)
      - 'exponential': A(t) = A0 * exp(- (rate_adj / A0) * t)
    """
    years_arr = np.asarray(years, dtype=float)
    if area_m2 <= 0:
        return np.zeros_like(years_arr)

    if model == "exponential":
        decay_constant = rate_adj_m2 / area_m2 if area_m2 > 0 else 0.0
        return area_m2 * np.exp(-decay_constant * years_arr)
    else:
        return np.maximum(area_m2 - rate_adj_m2 * years_arr, 0.0)


# ----------------------------------------------------------------------------
# Simulación Monte Carlo de Incertidumbre
# ----------------------------------------------------------------------------
def simulate_monte_carlo(
    area_m2: float,
    rate_hist_m2: float,
    pct: dict,
    k: float,
    n_runs: int = config.MC_RUNS,
    seed: int = 42,
) -> dict:
    """
    Ejecuta una simulación Monte Carlo de 1000 iteraciones variando:
      - Parámetro de sensibilidad k (~ ±25% CV)
      - Tasa histórica de retroceso (~ ±20% CV)
      - Albedos de referencia de cada cobertura (~ ±10% CV)

    Devuelve:
      - median: mediana de años restantes
      - p10: percentil 10 (caso acelerado/pesimista de incertidumbre)
      - p90: percentil 90 (caso conservador)
      - samples: array 1D con las muestras simuladas
      - stats: media, desviación estándar, tasa ajustada media
    """
    if area_m2 <= config.MIN_GLACIER_AREA_M2 or rate_hist_m2 <= 0:
        return {
            "median": 0.0 if area_m2 <= config.MIN_GLACIER_AREA_M2 else math.inf,
            "p10": 0.0,
            "p90": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "samples": np.zeros(n_runs),
            "rate_adj_mean": 0.0,
        }

    rng = np.random.default_rng(seed)

    # 1. Muestreo de k (distribución normal truncada > 0.05)
    k_samples = rng.normal(loc=k, scale=k * config.MC_K_UNCERTAINTY, size=n_runs)
    k_samples = np.clip(k_samples, 0.05, 3.0)

    # 2. Muestreo de Tasa histórica (truncada > 0)
    rate_samples = rng.normal(loc=rate_hist_m2, scale=rate_hist_m2 * config.MC_RATE_UNCERTAINTY, size=n_runs)
    rate_samples = np.clip(rate_samples, rate_hist_m2 * 0.1, rate_hist_m2 * 3.0)

    # 3. Muestreo de Albedos
    years_samples = np.empty(n_runs, dtype=float)
    rate_adj_samples = np.empty(n_runs, dtype=float)

    total_pct = sum(pct.get(c, 0.0) for c in config.CLASSES)
    if total_pct <= 0:
        total_pct = 100.0

    for i in range(n_runs):
        alb_sim = {}
        for c in config.CLASSES:
            nominal = config.ALBEDOS[c]
            sim_val = rng.normal(nominal, nominal * config.MC_ALBEDO_UNCERTAINTY)
            alb_sim[c] = float(np.clip(sim_val, 0.02, 0.95))

        alpha_eff = sum(pct.get(c, 0.0) / total_pct * alb_sim[c] for c in config.CLASSES)
        clean = alb_sim["clean_ice"]
        dm = max((1.0 - alpha_eff) / (1.0 - clean) - 1.0, 0.0) if clean < 1.0 else 0.0

        factor = np.clip(k_samples[i] * dm, 0.0, config.FACTOR_MAX)
        r_adj = rate_samples[i] * (1.0 + factor)

        rate_adj_samples[i] = r_adj
        years_samples[i] = area_m2 / r_adj if r_adj > 0 else 9999.0

    median = float(np.median(years_samples))
    p10 = float(np.percentile(years_samples, 10))
    p90 = float(np.percentile(years_samples, 90))
    mean = float(np.mean(years_samples))
    std = float(np.std(years_samples))

    return {
        "median": median,
        "p10": p10,
        "p90": p90,
        "mean": mean,
        "std": std,
        "samples": years_samples,
        "rate_adj_mean": float(np.mean(rate_adj_samples)),
    }


def compute_sensitivity_tornado(
    area_m2: float,
    rate_hist_m2: float,
    pct: dict,
    k: float,
    alpha_clean: float = 0.45,
) -> list[dict]:
    """
    Calcula el análisis de sensibilidad univariado (Diagrama de Tornado)
    para determinar cuál parámetro físico introduce mayor variación en el tiempo de vida.
    """
    if area_m2 <= config.MIN_GLACIER_AREA_M2 or rate_hist_m2 <= 0:
        return []

    alb_base = albedo_summary(pct)["alpha_eff"]
    dm_base = melt_acceleration(alb_base, alpha_clean)
    f_base = contaminant_factor(dm_base, k)
    r_adj_base = rate_hist_m2 * (1.0 + f_base)
    t_base = area_m2 / r_adj_base if r_adj_base > 0 else 0.0

    variaciones = [
        ("Tasa histórica de retroceso (±20%)", "rate", 0.20),
        ("Sensibilidad k al forzamiento (±25%)", "k", 0.25),
        ("Albedo de referencia del hielo (±10%)", "clean_alb", 0.10),
        ("Cobertura de carbono negro (±25%)", "carbon", 0.25),
    ]

    tornado_data = []
    for label, param_type, delta in variaciones:
        if param_type == "rate":
            r_low = rate_hist_m2 * (1.0 - delta)
            r_high = rate_hist_m2 * (1.0 + delta)
            t_low = area_m2 / (r_high * (1.0 + f_base))  # Mayor tasa -> menor tiempo
            t_high = area_m2 / (r_low * (1.0 + f_base))
        elif param_type == "k":
            k_low = max(0.01, k * (1.0 - delta))
            k_high = k * (1.0 + delta)
            f_low = contaminant_factor(dm_base, k_low)
            f_high = contaminant_factor(dm_base, k_high)
            t_low = area_m2 / (rate_hist_m2 * (1.0 + f_high))
            t_high = area_m2 / (rate_hist_m2 * (1.0 + f_low))
        elif param_type == "clean_alb":
            ca_low = max(0.15, alpha_clean * (1.0 - delta))
            ca_high = min(0.85, alpha_clean * (1.0 + delta))
            dm_low = melt_acceleration(alb_base, ca_low)
            dm_high = melt_acceleration(alb_base, ca_high)
            t_low = area_m2 / (rate_hist_m2 * (1.0 + contaminant_factor(dm_high, k)))
            t_high = area_m2 / (rate_hist_m2 * (1.0 + contaminant_factor(dm_low, k)))
        elif param_type == "carbon":
            pct_low = dict(pct)
            pct_high = dict(pct)
            pct_low["black_carbon"] = max(0.0, pct.get("black_carbon", 0.0) * (1.0 - delta))
            pct_high["black_carbon"] = pct.get("black_carbon", 0.0) * (1.0 + delta)
            alb_low = albedo_summary(pct_low)["alpha_eff"]
            alb_high = albedo_summary(pct_high)["alpha_eff"]
            dm_for_low = melt_acceleration(alb_low, alpha_clean)
            dm_for_high = melt_acceleration(alb_high, alpha_clean)
            t_low = area_m2 / (rate_hist_m2 * (1.0 + contaminant_factor(dm_for_high, k)))
            t_high = area_m2 / (rate_hist_m2 * (1.0 + contaminant_factor(dm_for_low, k)))

        amplitud = abs(t_high - t_low)
        tornado_data.append({
            "parámetro": label,
            "base_years": t_base,
            "min_years": min(t_low, t_high),
            "max_years": max(t_low, t_high),
            "amplitud": amplitud,
        })

    tornado_data.sort(key=lambda x: x["amplitud"], reverse=True)
    return tornado_data


def estimate_frontal_retreat(area_m2: float, gdf_proj: gpd.GeoDataFrame) -> dict[int, float]:
    """
    Estima el retroceso medio lineal del frente glaciar (en metros)
    a partir de la contracción métrica en UTM de los horizontes temporales.
    """
    if area_m2 <= 0:
        return {}

    r0_m = math.sqrt(area_m2 / math.pi)
    retreat_m = {}

    for _, row in gdf_proj.iterrows():
        h = int(row.get("anios", 0))
        if h == 0:
            continue
        area_h = float(row.get("area_m2", 0.0))
        if area_h <= config.MIN_GLACIER_AREA_M2:
            retreat_m[h] = round(r0_m, 1)
        else:
            rh_m = math.sqrt(area_h / math.pi)
            retreat_m[h] = round(max(0.0, r0_m - rh_m), 1)

    return retreat_m


# ----------------------------------------------------------------------------
# Geometrías y Carga de GeoJSON real vs. Elipse simulada
# ----------------------------------------------------------------------------
def _ellipse_utm(x0: float, y0: float, area_m2: float, aspect: float = 1.6, angle: float = 25.0) -> Polygon:
    """Genera una elipse de área EXACTA centrada en (x0, y0) en coordenadas métricas UTM."""
    if area_m2 <= 0:
        return Polygon()
    a = math.sqrt(area_m2 * aspect / math.pi)
    b = area_m2 / (math.pi * a)
    e = scale(Point(0, 0).buffer(1.0, 64), a, b, origin=(0, 0))
    e = scale(e, math.sqrt(area_m2 / e.area), math.sqrt(area_m2 / e.area), origin=(0, 0))
    return translate(rotate(e, angle, origin=(0, 0)), x0, y0)


def _shrink_to_area(poly: Polygon, target_m2: float) -> Polygon | None:
    """Aplica buffer negativo mediante bisección numérica hasta alcanzar target_m2."""
    if target_m2 <= config.MIN_GLACIER_AREA_M2:
        return None
    if poly.is_empty or target_m2 >= poly.area:
        return poly

    lo, hi = 0.0, math.sqrt(poly.area)
    for _ in range(60):
        mid = (lo + hi) / 2.0
        g = poly.buffer(-mid)
        area = 0.0 if g.is_empty else g.area
        if area > target_m2:
            lo = mid
        else:
            hi = mid

    g = poly.buffer(-(lo + hi) / 2.0)
    if g.is_empty:
        return None
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda p: p.area)
    return g


def find_glacier_geojson(glacier_name: str | None) -> Path | None:
    """Busca un archivo GeoJSON o Shapefile real en data/ para el glaciar solicitado."""
    if not glacier_name:
        return None

    # Normalizar nombre para búsqueda de archivo
    clean_name = glacier_name.lower().split(" ")[0].replace("(", "").replace(")", "").strip()
    data_dir = config.DATA_DIR
    if not data_dir.exists():
        return None

    candidates = [
        data_dir / f"{clean_name}.geojson",
        data_dir / f"{clean_name}.json",
        data_dir / f"{clean_name}.shp",
    ]
    for c in candidates:
        if c.exists():
            return c

    # Si hay algún .geojson en data/ que contenga el nombre
    for f in data_dir.glob("*.geojson"):
        if clean_name in f.stem.lower():
            return f

    return None


def get_base_geometry(
    lat: float,
    lon: float,
    area_m2: float,
    glacier_name: str | None = None,
    utm_crs: int = 32718,
) -> tuple[Polygon, bool, str]:
    """
    Obtiene la geometría base para proyección métrica:
      - Si existe GeoJSON real en data/, lo carga, reproyecta a UTM y ajusta.
      - Si no existe, genera una elipse sintética y marca el origen como simulado.

    Retorna: (geometría_UTM, es_contorno_real, descripcion_fuente)
    """
    geojson_path = find_glacier_geojson(glacier_name)
    if geojson_path is not None:
        try:
            gdf_real = gpd.read_file(geojson_path)
            if not gdf_real.empty and gdf_real.geometry.iloc[0] is not None:
                geom = gdf_real.geometry.iloc[0]
                # Reproyectar a UTM
                if gdf_real.crs is not None and gdf_real.crs.to_epsg() != utm_crs:
                    gdf_utm = gdf_real.to_crs(epsg=utm_crs)
                    geom_utm = gdf_utm.geometry.iloc[0]
                else:
                    to_utm = Transformer.from_crs(config.EPSG_WGS84, utm_crs, always_xy=True)
                    geom_utm = shp_transform(to_utm.transform, geom)

                if geom_utm.geom_type == "MultiPolygon":
                    geom_utm = max(geom_utm.geoms, key=lambda p: p.area)

                # Escalar para que coincida exactamente con el área solicitada si difiere
                if geom_utm.area > 0 and abs(geom_utm.area - area_m2) / area_m2 > 0.05:
                    scale_factor = math.sqrt(area_m2 / geom_utm.area)
                    geom_utm = scale(geom_utm, xfact=scale_factor, yfact=scale_factor, origin="centroid")

                source_note = f"Contorno real GeoJSON: {geojson_path.name} (INAIGEM / Datos abiertos)"
                return geom_utm, True, source_note
        except Exception:
            # Fallback seguro a elipse si el archivo estuviese corrupto
            pass

    # Si no hay archivo real: Elipse simulada
    to_utm = Transformer.from_crs(config.EPSG_WGS84, utm_crs, always_xy=True)
    x0, y0 = to_utm.transform(lon, lat)
    ellipse = _ellipse_utm(x0, y0, area_m2)
    source_note = "Elipse paramétrica (área proyectada en UTM)"
    return ellipse, False, source_note


def build_projection(
    lat: float,
    lon: float,
    area_m2: float,
    rate_adj_m2: float,
    horizons: tuple = config.HORIZONS,
    glacier_name: str | None = None,
    decay_model: str = "linear",
) -> gpd.GeoDataFrame:
    """
    Genera GeoDataFrame en WGS84 (EPSG:4326) con perímetros a 0, 5, 10 y 20 años.
    Usa contorno real GeoJSON si existe en data/, o elipse simulada si no.
    """
    validate_inputs(lat, lon, area_m2, rate_adj_m2)

    # Caso límite: glaciar ya desaparecido
    if area_m2 <= config.MIN_GLACIER_AREA_M2:
        rows = [
            dict(
                etiqueta="Actual (Extinto)",
                anios=0,
                area_m2=0.0,
                area_km2=0.0,
                estado="desaparecido",
                color="#666666",
                geometry=Polygon(),
            )
        ]
        gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=config.EPSG_WGS84)
        gdf.attrs["is_real_contour"] = False
        gdf.attrs["source"] = "Glaciar extinto o área nula"
        return gdf

    epsg = utm_epsg(lat, lon)
    base_geom, is_real, source_info = get_base_geometry(lat, lon, area_m2, glacier_name, epsg)

    rows = []
    for h in (0, *horizons):
        if decay_model == "exponential":
            target = float(area_curve(area_m2, rate_adj_m2, np.array([h]), model="exponential")[0])
        else:
            target = max(area_m2 - rate_adj_m2 * h, 0.0)

        geom = base_geom if h == 0 else _shrink_to_area(base_geom, target)
        if geom is None or target <= config.MIN_GLACIER_AREA_M2:
            rows.append(
                dict(
                    etiqueta=f"+{h} años",
                    anios=h,
                    area_m2=0.0,
                    area_km2=0.0,
                    estado="desaparecido",
                    color=config.HORIZON_COLORS.get(h, "#999"),
                    geometry=Polygon(),
                )
            )
        else:
            rows.append(
                dict(
                    etiqueta="Actual" if h == 0 else f"+{h} años",
                    anios=h,
                    area_m2=float(geom.area),
                    area_km2=float(geom.area) / 1e6,
                    estado="activo",
                    color=config.HORIZON_COLORS.get(h, "#999"),
                    geometry=geom,
                )
            )

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=epsg)
    gdf_wgs84 = gdf.to_crs(config.EPSG_WGS84)
    gdf_wgs84.attrs["is_real_contour"] = is_real
    gdf_wgs84.attrs["source"] = source_info
    return gdf_wgs84
