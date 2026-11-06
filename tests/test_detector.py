"""
tests/test_detector.py
======================
Pruebas unitarias para detector.py:
  - Clasificación en imágenes sintéticas con cobertura conocida (error <= 5 puntos porcentuales)
  - Suma de porcentajes igual a 100.0%
  - Detección automática de cielo
  - Desambiguación de sombras
  - K-means y comparación
  - Rango del índice de confianza (0.0 a 1.0)
"""
import numpy as np
import pytest

import config
import detector
from utils import sample_images


def create_ground_truth_image(
    h: int = 400,
    w: int = 400,
    pct_ice: float = 50.0,
    pct_carbon: float = 20.0,
    pct_dust: float = 20.0,
    pct_water: float = 10.0,
) -> np.ndarray:
    """
    Crea una imagen sintética calibrada con partición exacta de píxeles
    y los colores radiométricos estándar de cada clase.
    """
    assert abs(pct_ice + pct_carbon + pct_dust + pct_water - 100.0) < 1e-3

    img = np.zeros((h, w, 3), dtype=np.uint8)
    total_pixels = h * w

    n_ice = int(total_pixels * (pct_ice / 100.0))
    n_carbon = int(total_pixels * (pct_carbon / 100.0))
    n_dust = int(total_pixels * (pct_dust / 100.0))
    n_water = total_pixels - (n_ice + n_carbon + n_dust)

    # Colores representativos de cada clase
    col_ice = [228, 236, 246]
    col_carbon = [25, 25, 28]
    col_dust = [155, 115, 75]
    col_water = [30, 115, 205]

    flat = img.reshape(-1, 3)
    idx = 0
    flat[idx : idx + n_ice] = col_ice
    idx += n_ice
    flat[idx : idx + n_carbon] = col_carbon
    idx += n_carbon
    flat[idx : idx + n_dust] = col_dust
    idx += n_dust
    flat[idx : idx + n_water] = col_water

    return img.reshape(h, w, 3)


def test_detector_known_coverage_accuracy():
    """
    Verifica que en una imagen sintética calibrada de cobertura conocida,
    el error de detección no supere los 5 puntos porcentuales (+/- 5%).
    """
    target = {
        "clean_ice": 50.0,
        "black_carbon": 20.0,
        "dust": 20.0,
        "meltwater_pool": 10.0,
    }
    img = create_ground_truth_image(
        h=300,
        w=300,
        pct_ice=target["clean_ice"],
        pct_carbon=target["black_carbon"],
        pct_dust=target["dust"],
        pct_water=target["meltwater_pool"],
    )

    result = detector.detect(img, ignore_top_pct=0.0, auto_sky=False)
    preds = result.percentages

    for cls_name, true_pct in target.items():
        pred_pct = preds[cls_name]
        err = abs(pred_pct - true_pct)
        assert err <= 5.0, (
            f"Error en clase '{cls_name}' excede 5 puntos porcentuales: "
            f"Esperado {true_pct:.1f}%, Obtenido {pred_pct:.1f}% (Error: {err:.2f}%)"
        )


def test_detector_percentages_sum_100():
    """Verifica que los porcentajes devueltos sumen siempre exactamente 100.0%."""
    samples = sample_images.get_samples()
    for name, img in samples.items():
        res = detector.detect(img)
        total = sum(res.percentages.values())
        assert abs(total - 100.0) < 1e-4, f"En {name}, suma={total}"


def test_detector_confidence_bounds():
    """Verifica que el índice de confianza esté acotado entre 0.0 y 1.0."""
    samples = sample_images.get_samples()
    for name, img in samples.items():
        res = detector.detect(img)
        assert 0.0 <= res.confidence <= 1.0, f"Confianza fuera de rango en {name}: {res.confidence}"


def test_detector_kmeans_method():
    """Verifica que el método K-means en LAB funcione y retorne las 4 clases."""
    img = sample_images.get_samples()["2. Polvo moderado"]
    res = detector.detect(img, method_name="kmeans", compare_kmeans=True)
    assert res.method == detector.METHOD_KMEANS
    assert len(res.percentages) == 4
    for c in config.CLASSES:
        assert c in res.percentages
        assert res.percentages[c] >= 0.0
    assert res.comparison is not None
    assert "percentages" in res.comparison


def test_detector_auto_sky():
    """Verifica la detección automática de franja superior de cielo."""
    # Imagen con cielo azul arriba (primeras 60 filas) y hielo abajo
    h, w = 200, 200
    img = np.full((h, w, 3), [220, 230, 245], dtype=np.uint8)  # hielo
    img[:50, :] = [100, 150, 225]  # cielo azul

    res = detector.detect(img, auto_sky=True)
    assert res.auto_sky_pct >= 15.0, f"No detectó el cielo superior: {res.auto_sky_pct}%"


def test_detector_shadow_distinction():
    """Verifica que las sombras no se computen indiscriminadamente como carbono negro."""
    h, w = 200, 200
    # Nieve sombreada (L intermedio en LAB tras CLAHE y tono frío azulado)
    img_shadow = np.full((h, w, 3), [75, 78, 88], dtype=np.uint8)
    res = detector.detect(img_shadow, auto_sky=False)
    # No debe asignar el 100% a carbono negro gracias a la desambiguación CLAHE
    assert res.percentages["black_carbon"] < 80.0


def test_detector_spectral_profiles():
    """Verifica el cálculo de perfiles radiométricos espectrales."""
    img = sample_images.get_samples()["1. Glaciar limpio"]
    res = detector.detect(img)
    assert res.spectral_profiles is not None
    assert "clean_ice" in res.spectral_profiles
    assert res.spectral_profiles["clean_ice"]["pixel_count"] > 0
    assert res.spectral_profiles["clean_ice"]["mean_l"] > 0

