"""
utils/sample_images.py
======================
Genera imágenes SINTÉTICAS de glaciares para probar la app sin descargar nada.
No son fotos reales: son texturas con manchas de polvo, hollín y agua.
"""
from pathlib import Path

import cv2
import numpy as np

# nombre -> (semilla, cobertura polvo, cobertura carbono, cobertura agua)
PRESETS = {
    "1. Glaciar limpio": (11, 0.02, 0.00, 0.03),
    "2. Polvo moderado": (22, 0.25, 0.05, 0.08),
    "3. Muy contaminado": (33, 0.35, 0.25, 0.15),
}

_ICE = np.array([228, 236, 246], dtype=np.float32)
_DUST = np.array([150, 115, 80], dtype=np.float32)
_CARBON = np.array([28, 28, 32], dtype=np.float32)
_WATER = np.array([30, 120, 200], dtype=np.float32)


def _field(rng, h, w, cell):
    """Campo de ruido suave (manchas orgánicas) normalizado a 0..1."""
    small = rng.random((h // cell + 2, w // cell + 2)).astype(np.float32)
    big = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    big = (big - big.min()) / (big.max() - big.min() + 1e-9)
    return big


def _mask_from_field(f, coverage):
    if coverage <= 0:
        return np.zeros_like(f)
    thr = np.quantile(f, 1.0 - coverage)
    m = (f >= thr).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 1.2)


def make_glacier(seed, dust, carbon, water, h=480, w=720):
    """Devuelve una imagen RGB uint8 de h x w."""
    rng = np.random.default_rng(seed)
    base = np.tile(_ICE, (h, w, 1))
    base += (_field(rng, h, w, 6)[..., None] - 0.5) * 18        # textura del hielo

    f_dust = 0.6 * _field(rng, h, w, 40) + 0.4 * _field(rng, h, w, 14)
    f_water = 0.7 * _field(rng, h, w, 55) + 0.3 * _field(rng, h, w, 20)
    f_carbon = 0.6 * _field(rng, h, w, 30) + 0.4 * _field(rng, h, w, 10)

    for field, cov, color in ((f_dust, dust, _DUST),
                              (f_water, water, _WATER),
                              (f_carbon, carbon, _CARBON)):
        m = _mask_from_field(field, cov)[..., None]
        tint = color + (rng.random((h, w, 1)).astype(np.float32) - 0.5) * 10
        base = base * (1 - m) + tint * m
    return np.clip(base, 0, 255).astype(np.uint8)


def get_samples():
    """Dict {nombre: imagen RGB}."""
    return {name: make_glacier(*params) for name, params in PRESETS.items()}


def save_samples(folder):
    """Guarda las imágenes de prueba como PNG y devuelve las rutas."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, img in get_samples().items():
        fname = name.split(". ")[1].lower().replace(" ", "_") + ".png"
        p = folder / fname
        cv2.imwrite(str(p), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        paths.append(p)
    return paths


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import SAMPLES_DIR
    for p in save_samples(SAMPLES_DIR):
        print("Guardada:", p)
