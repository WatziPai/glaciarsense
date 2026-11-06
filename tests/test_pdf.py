"""
tests/test_pdf.py
=================
Prueba unitaria para la generación de reportes PDF técnicos.
"""
from PIL import Image
import numpy as np

import detector
import gis_engine
from utils import pdf_report


def test_pdf_generation_bytes():
    """Verifica que el generador de PDF cree un documento válido en memoria."""
    # Simulación de datos
    img_arr = np.full((200, 200, 3), 200, dtype=np.uint8)
    det = detector.detect(img_arr, auto_sky=False)
    alb = gis_engine.albedo_summary(det.percentages)
    scens = gis_engine.compute_scenarios(5e6, 0.1e6, alb["alpha_eff"], alb["alpha_clean"], 0.6)
    mc = gis_engine.simulate_monte_carlo(5e6, 0.1e6, det.percentages, 0.6, n_runs=100)

    pdf_bytes = pdf_report.generate_pdf_report(
        glacier_name="Pastoruri (Perú)",
        lat=-9.90,
        lon=-77.18,
        area_km2=1.4,
        rate_km2=0.06,
        det_result=det,
        albedo_data=alb,
        scenarios=scens,
        mc_data=mc,
        annotated_rgb=Image.fromarray(det.annotated),
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")

