"""
tests/test_gis_engine.py
========================
Pruebas unitarias para gis_engine.py:
  - Fórmulas físicas de albedo efectivo y aceleración energética
  - Ajuste de tasa y cálculo de tiempo restante
  - Escenarios climáticos SSP (IPCC AR6)
  - Modelo de decaimiento exponencial vs. lineal
  - Simulación estocástica Monte Carlo (1,000 corridas, cuantiles)
  - Detección de GeoJSON real vs. Elipse simulada
  - Casos límite (área cero, tasa cero, glaciar extinto, validación)
"""
import math
import numpy as np
import pytest

import config
import gis_engine


def test_albedo_summary_formula():
    """Verifica que el albedo efectivo corresponda a la suma ponderada."""
    pct = {
        "clean_ice": 40.0,
        "black_carbon": 20.0,
        "dust": 20.0,
        "meltwater_pool": 20.0,
    }
    # 0.40*0.45 + 0.20*0.10 + 0.20*0.25 + 0.20*0.15 = 0.18 + 0.02 + 0.05 + 0.03 = 0.28
    res = gis_engine.albedo_summary(pct)
    expected_alpha = 0.28
    assert abs(res["alpha_eff"] - expected_alpha) < 1e-4
    assert abs(res["loss_abs"] - (0.45 - expected_alpha)) < 1e-4
    assert res["loss_pct"] > 0


def test_melt_acceleration_delta_m():
    """Verifica la fórmula de aceleración de energía absorbida ΔM."""
    clean = 0.45
    # Si albedo_eff == clean, Delta M debe ser 0.0
    dm_zero = gis_engine.melt_acceleration(clean, clean)
    assert abs(dm_zero - 0.0) < 1e-6

    # Si albedo_eff cae a 0.20
    # Delta M = (1 - 0.20) / (1 - 0.45) - 1 = 0.80 / 0.55 - 1 = 1.4545 - 1 = 0.4545
    dm_val = gis_engine.melt_acceleration(0.20, clean)
    assert abs(dm_val - (0.80 / 0.55 - 1.0)) < 1e-4


def test_contaminant_factor_clipping():
    """Verifica el tope máximo de clip en FACTOR_MAX (1.5)."""
    # Factor pequeño
    f1 = gis_engine.contaminant_factor(0.1, 0.5)
    assert abs(f1 - 0.05) < 1e-6

    # Factor extremo debe saturar en 1.5
    f_max = gis_engine.contaminant_factor(5.0, 2.0)
    assert abs(f_max - config.FACTOR_MAX) < 1e-6


def test_compute_scenarios_and_ssp():
    """Verifica el cálculo de escenarios clásicos y climáticos SSP."""
    area_m2 = 10e6        # 10 km2
    rate_hist_m2 = 0.2e6  # 0.2 km2/año
    alpha_eff = 0.30
    clean = 0.45
    k = 0.6

    scenarios = gis_engine.compute_scenarios(
        area_m2, rate_hist_m2, alpha_eff, clean, k, include_ssp=True
    )
    # Deben calcularse 3 clásicos + 3 SSP = 6 escenarios
    assert len(scenarios) == 6

    names = [s.name for s in scenarios]
    assert "Optimista" in names
    assert "Central" in names
    assert "Pesimista" in names
    assert "SSP1-2.6 (Bajas emisiones)" in names
    assert "SSP5-8.5 (Altas emisiones)" in names

    # En un escenario más pesimista, la tasa ajustada debe ser mayor y los años menores
    opt = next(s for s in scenarios if s.name == "Optimista")
    pes = next(s for s in scenarios if s.name == "Pesimista")
    assert opt.rate_adj < pes.rate_adj
    assert opt.years > pes.years


def test_monte_carlo_distribution():
    """Verifica que la simulación Monte Carlo ejecute 1000 iteraciones con cuantiles coherentes."""
    area_m2 = 5e6
    rate_hist_m2 = 0.1e6
    pct = {"clean_ice": 60.0, "black_carbon": 10.0, "dust": 20.0, "meltwater_pool": 10.0}
    k = 0.6

    mc = gis_engine.simulate_monte_carlo(area_m2, rate_hist_m2, pct, k, n_runs=1000)
    assert len(mc["samples"]) == 1000
    assert mc["p10"] > 0
    assert mc["p10"] <= mc["median"] <= mc["p90"]
    assert mc["std"] > 0


def test_exponential_vs_linear_decay():
    """Verifica las propiedades matemáticas de la curva de decaimiento exponencial vs lineal."""
    area_m2 = 10e6
    rate_adj = 1.0e6
    years = np.array([0, 5, 10, 15, 20])

    curve_lin = gis_engine.area_curve(area_m2, rate_adj, years, model="linear")
    curve_exp = gis_engine.area_curve(area_m2, rate_adj, years, model="exponential")

    # En t=0, ambas deben igualar el área inicial
    assert abs(curve_lin[0] - area_m2) < 1e-4
    assert abs(curve_exp[0] - area_m2) < 1e-4

    # El modelo lineal llega a 0 en t=10 años
    assert curve_lin[2] == 0.0

    # El modelo exponencial es asintótico y positivo
    assert curve_exp[2] > 0.0
    assert curve_exp[4] > 0.0


def test_geojson_detection_pastoruri():
    """Verifica que el motor detecte y cargue el contorno real GeoJSON en data/."""
    gdf = gis_engine.build_projection(
        lat=-9.90, lon=-77.18, area_m2=1.4e6, rate_adj_m2=0.06e6,
        glacier_name="Pastoruri (Perú)"
    )
    assert gdf.attrs["is_real_contour"] is True
    assert "GeoJSON" in gdf.attrs["source"]
    assert not gdf.empty


def test_geojson_detection_quelccaya():
    """Verifica que Quelccaya cargue su contorno real GeoJSON en data/."""
    gdf = gis_engine.build_projection(
        lat=-13.93, lon=-70.83, area_m2=42e6, rate_adj_m2=0.35e6,
        glacier_name="Quelccaya (Perú)"
    )
    assert gdf.attrs["is_real_contour"] is True
    assert "GeoJSON" in gdf.attrs["source"]


def test_ellipse_fallback_coropuna():
    """Verifica que si no hay GeoJSON (como Coropuna), el motor use elipse paramétrica."""
    gdf = gis_engine.build_projection(
        lat=-15.52, lon=-72.65, area_m2=40e6, rate_adj_m2=0.50e6,
        glacier_name="Coropuna (Perú)"
    )
    assert gdf.attrs["is_real_contour"] is False
    assert "Elipse" in gdf.attrs["source"]


def test_edge_cases_zero_area_and_rate():
    """Valida casos límite: área cero o glaciar ya extinto."""
    # 1. Área 0
    scens_zero = gis_engine.compute_scenarios(0.0, 0.1e6, 0.35, 0.45, 0.6)
    assert scens_zero[0].years == 0.0

    # 2. Tasa 0 (sin pérdida)
    scens_norate = gis_engine.compute_scenarios(5e6, 0.0, 0.35, 0.45, 0.6)
    assert math.isinf(scens_norate[1].years)

    # 3. Proyección de glaciar extinto
    gdf_extinto = gis_engine.build_projection(0, 0, 0.0, 0.1e6)
    assert gdf_extinto.iloc[0]["estado"] == "desaparecido"


def test_input_validation_errors():
    """Verifica que se lancen excepciones con parámetros fuera de rango físico."""
    with pytest.raises(ValueError):
        gis_engine.validate_inputs(120.0, 0.0, 1e6, 1e5)  # Latitud > 90

    with pytest.raises(ValueError):
        gis_engine.validate_inputs(0.0, 200.0, 1e6, 1e5)  # Longitud > 180

    with pytest.raises(ValueError):
        gis_engine.validate_inputs(0.0, 0.0, -100.0, 1e5)  # Área negativa


def test_sensitivity_tornado():
    """Verifica el cálculo del análisis de sensibilidad tipo tornado."""
    pct = {"clean_ice": 60.0, "black_carbon": 10.0, "dust": 20.0, "meltwater_pool": 10.0}
    tornado = gis_engine.compute_sensitivity_tornado(5e6, 0.1e6, pct, 0.6)
    assert len(tornado) == 4
    for item in tornado:
        assert item["min_years"] <= item["max_years"]
        assert item["amplitud"] >= 0.0
    # Verifica que esté ordenado por amplitud descendente
    assert tornado[0]["amplitud"] >= tornado[-1]["amplitud"]


def test_estimate_frontal_retreat():
    """Verifica la estimación del retroceso lineal del frente glaciar."""
    gdf = gis_engine.build_projection(-9.90, -77.18, 1.4e6, 0.06e6, glacier_name="Pastoruri (Perú)")
    retreat = gis_engine.estimate_frontal_retreat(1.4e6, gdf)
    assert 5 in retreat and 10 in retreat and 20 in retreat
    # El retroceso a 20 años debe ser mayor o igual al retroceso a 5 años
    assert retreat[20] >= retreat[5]

