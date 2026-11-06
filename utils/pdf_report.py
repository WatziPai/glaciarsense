"""
utils/pdf_report.py
===================
Generador de informes técnicos en formato PDF para GlaciarSense.
Construye un documento de 1 o 2 páginas con diseño profesional,
gráficos/imágenes anotadas, tablas métricas, simulación de vida y limitaciones.
"""
from __future__ import annotations

import io
import tempfile
from datetime import datetime
from pathlib import Path
from PIL import Image

from fpdf import FPDF
import config


def _clean_text(text: str) -> str:
    """Reemplaza caracteres tipográficos incompatibles con Latin-1 (en-dash, comillas curvas, etc.)."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "*",
        "…": "...",
        "≤": "<=",
        "≥": ">=",
        "≈": "~",
        "≠": "!=",
        "°": " deg",
        "²": "2",
        "³": "3",
        "µ": "u",
        "α": "alfa",
        "Δ": "Delta",
        "∑": "Sum",
        "🧊": "",
        "🏔": "",
        "⚠️": "[!]",
        "ℹ": "[i]",
        "⚫": "[*]",
        "🟤": "[*]",
        "💧": "[*]",
        "❄": "[*]",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Filtrar cualquier caracter que no pueda codificarse en latin-1
    return text.encode("latin-1", "replace").decode("latin-1")


class GlaciarReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(24, 76, 120)
        self.cell(0, 8, _clean_text("GlaciarSense - Informe Técnico de Análisis Glaciar"), new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, _clean_text("Diagnóstico de reflectancia superficial por imagen y proyección de retroceso"), new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_draw_color(200, 200, 200)
        self.line(10, 22, 200, 22)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        page_str = f"Página {self.page_no()} / {{nb}}"
        self.cell(0, 10, _clean_text(f"GlaciarSense | {page_str}"), align="C")


def generate_pdf_report(
    glacier_name: str,
    lat: float,
    lon: float,
    area_km2: float,
    rate_km2: float,
    det_result,
    albedo_data: dict,
    scenarios: list,
    mc_data: dict | None = None,
    annotated_rgb: Image.Image | None = None,
    notes: str = "",
) -> bytes:
    """
    Genera el informe técnico en memoria y devuelve los bytes del archivo PDF.
    """
    pdf = GlaciarReportPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 1. Nota técnica de alcance metodológico
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(210, 220, 230)
    pdf.set_text_color(50, 70, 90)
    pdf.set_font("Helvetica", "B", 8)
    disclaimer = (
        "RESUMEN TÉCNICO: Este informe documenta la estimación de albedo efectivo a partir de la reflectancia "
        "espectral observada en imagen, cuantificando la aceleración de absorción térmica por impurezas (carbono negro y polvo) "
        "y proyectando trayectorias de retroceso acopladas a escenarios climáticos del IPCC."
    )
    pdf.multi_cell(0, 4.5, _clean_text(disclaimer), border=1, fill=True, align="L")
    pdf.ln(3)

    # 2. Metadatos generales del análisis
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 6, _clean_text("1. Datos Generales de la Observación"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=8.5)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    col_w = 47
    pdf.set_fill_color(245, 247, 250)
    pdf.cell(col_w, 5, _clean_text(f"Glaciar: {glacier_name}"), border=1, fill=True)
    pdf.cell(col_w, 5, _clean_text(f"Fecha emisión: {now_str}"), border=1, fill=True)
    pdf.cell(col_w, 5, _clean_text(f"Ubicación: {lat:.3f}, {lon:.3f}"), border=1, fill=True)
    pdf.cell(col_w, 5, _clean_text(f"Área base: {area_km2:.2f} km2"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    conf_pct = det_result.confidence * 100.0 if hasattr(det_result, "confidence") else 100.0
    pdf.cell(col_w * 2, 5, _clean_text(f"Método de clasificación: {det_result.method}"), border=1)
    pdf.cell(col_w * 2, 5, _clean_text(f"Confianza diagnóstica estimada: {conf_pct:.1f}%"), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 3. Imagen anotada
    if annotated_rgb is not None:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                temp_path = tmp.name
                if not isinstance(annotated_rgb, Image.Image):
                    im = Image.fromarray(annotated_rgb)
                else:
                    im = annotated_rgb
                # Reducir imagen a tamaño óptimo para el PDF
                im_thumb = im.copy()
                im_thumb.thumbnail((800, 600))
                im_thumb.save(temp_path, "JPEG", quality=85)

            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, _clean_text("2. Registro Visual Clasificado"), new_x="LMARGIN", new_y="NEXT")
            # Centrar la imagen en la página A4 (ancho disponible ~190mm)
            img_w = 140
            x_pos = (210 - img_w) / 2
            pdf.image(temp_path, x=x_pos, w=img_w)
            pdf.ln(2)

            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass

    # 4. Tabla de coberturas
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _clean_text("3. Cobertura Superficial y Albedos Estimados"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(220, 230, 242)
    pdf.cell(60, 5, _clean_text("Cobertura"), border=1, fill=True)
    pdf.cell(40, 5, _clean_text("Porcentaje (%)"), border=1, fill=True, align="R")
    pdf.cell(45, 5, _clean_text("Albedo de Referencia"), border=1, fill=True, align="R")
    pdf.cell(45, 5, _clean_text("Tipo de Superficie"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=8)
    pcts = det_result.percentages
    class_details = [
        ("clean_ice", "Hielo limpio", config.ALBEDOS["clean_ice"], "Reflectante (deshielo basal)"),
        ("black_carbon", "Carbono negro (hollín)", config.ALBEDOS["black_carbon"], "Absorbente crítico"),
        ("dust", "Polvo mineral", config.ALBEDOS["dust"], "Absorbente intermedio"),
        ("meltwater_pool", "Agua de deshielo", config.ALBEDOS["meltwater_pool"], "Absorbente hídrico"),
    ]
    for key, name, alb_val, desc in class_details:
        pdf.cell(60, 4.5, _clean_text(name), border=1)
        pdf.cell(40, 4.5, f"{pcts.get(key, 0.0):.2f} %", border=1, align="R")
        pdf.cell(45, 4.5, f"{alb_val:.2f}", border=1, align="R")
        pdf.cell(45, 4.5, _clean_text(desc), border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)

    # 5. Métricas de albedo y aceleración
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(47, 5, _clean_text(f"Albedo efectivo: {albedo_data['alpha_eff']:.3f}"), border=1, fill=True)
    pdf.cell(47, 5, _clean_text(f"Pérdida albedo: -{albedo_data['loss_abs']:.3f}"), border=1, fill=True)
    pdf.cell(47, 5, _clean_text(f"Pérdida relativa: {albedo_data['loss_pct']:.1f}%"), border=1, fill=True)
    # Aceleración Delta M
    clean_alb = albedo_data["alpha_clean"]
    dm = max((1.0 - albedo_data["alpha_eff"]) / (1.0 - clean_alb) - 1.0, 0.0) if clean_alb < 1.0 else 0.0
    pdf.cell(47, 5, _clean_text(f"Aceleración energética Delta M: +{dm * 100:.1f}%"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    # PÁGINA 2: Proyecciones e Incertidumbre
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 6, _clean_text("4. Proyecciones y Escenarios de Tiempo de Vida Restante"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_fill_color(220, 230, 242)
    pdf.cell(50, 5, _clean_text("Escenario / Trayectoria"), border=1, fill=True)
    pdf.cell(30, 5, _clean_text("Factor Contaminante"), border=1, fill=True, align="R")
    pdf.cell(35, 5, _clean_text("Tasa Ajustada (km2/año)"), border=1, fill=True, align="R")
    pdf.cell(35, 5, _clean_text("Años Restantes"), border=1, fill=True, align="R")
    pdf.cell(40, 5, _clean_text("Año Estimado Extinción"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=7.5)
    for sc in scenarios:
        y_str = f"{sc.years:.0f} años" if sc.years < 9999 else "Sin pérdida"
        y_end = str(sc.year_end) if sc.year_end else "-"
        pdf.cell(50, 4.5, _clean_text(sc.name[:28]), border=1)
        pdf.cell(30, 4.5, f"+{sc.factor * 100:.1f} %", border=1, align="R")
        pdf.cell(35, 4.5, f"{sc.rate_adj / 1e6:.3f}", border=1, align="R")
        pdf.cell(35, 4.5, _clean_text(y_str), border=1, align="R")
        pdf.cell(40, 4.5, _clean_text(y_end), border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # 6. Simulación Monte Carlo de Incertidumbre
    if mc_data is not None and mc_data.get("median", 0) > 0:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, _clean_text("5. Análisis de Incertidumbre Monte Carlo (1,000 corridas estocásticas)"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=8)
        mc_desc = (
            f"Se ejecutaron 1,000 simulaciones variando aleatoriamente la sensibilidad de contaminantes (k +/-25%), "
            f"la tasa de retroceso histórica (+/-20%) y los albedos de referencia (+/-10%).\n"
            f"  - Mediana estimada: {mc_data['median']:.1f} años\n"
            f"  - Rango de confianza (Percentiles 10-90): {mc_data['p10']:.1f} - {mc_data['p90']:.1f} años\n"
            f"  - Desviación estándar del modelo: +/-{mc_data['std']:.1f} años"
        )
        pdf.multi_cell(0, 4.5, _clean_text(mc_desc), border=1, fill=False)
        pdf.ln(3)

    # 7. Limitaciones científicas fundamentales
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _clean_text("6. Limitaciones Científicas y Metodológicas"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=7.5)
    limitaciones = [
        "1. Imagen bidimensional sin escala física: la proporción de contaminantes detectada en la foto corresponde al encuadre visual y no necesariamente representa la totalidad del casquete o cuenca glaciar.",
        "2. Ausencia de calibración radiométrica multiespectral: una cámara estándar RGB aproxima colores visuales pero carece de bandas infrarrojas de onda corta (SWIR) necesarias para diferenciar agua líquida profunda de hielo azul o regolito mineral fino con exactitud espectral.",
        "3. Dinámica de hielo no modelada: el modelo utiliza reducción geométrica de área. No modela flujo por deformación de Glen, balance de masa por gradiente altitudinal ni efecto de topografía rocosa subglaciar.",
        "4. Forzamiento climático simplificado: los escenarios SSP se aproximan como multiplicadores escalares de la tasa histórica, sin resolver balances de energía acoplados a modelos de circulación general (GCM).",
    ]
    for lim in limitaciones:
        pdf.multi_cell(0, 3.8, _clean_text(lim))
        pdf.ln(0.8)

    pdf.ln(2)
    # 8. Cita y fuentes
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(100, 100, 100)
    sources = (
        "Fuentes de referencia para datos verificables: WGMS (World Glacier Monitoring Service, DOI:10.5904/wgms-fog-2023-09); "
        "INAIGEM (Inventario Nacional de Glaciares del Perú); IPCC AR6 SROCC (2019/2021); Warren & Wiscombe (1980)."
    )
    pdf.multi_cell(0, 3.5, _clean_text(sources))

    return bytes(pdf.output())
