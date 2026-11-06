"""
detector.py
===========
Módulo de visión por computadora para análisis de glaciares.

Métodos de detección:
  1. YOLOv8 (segmentación) -> si existe models/best.pt y ultralytics instalado.
  2. Umbrales LAB + HSV con normalización CLAHE y detección de sombras (método estándar robusto).
  3. K-means no supervisado (k=4 en espacio LAB perceptual).

Salida (DetectionResult):
  - percentages : {clase: % de cobertura}, suma 100.0 %
  - masks       : {clase: máscara booleana}
  - annotated   : imagen RGB con contornos y leyenda
  - method      : descripción del método empleado
  - glacier_ok  : bool (indica si parece un glaciar o predomina vegetación)
  - warnings    : list con advertencias metodológicas y diagnósticas
  - confidence  : índice de confianza de clasificación (0.0 a 1.0)
  - auto_sky_pct: % superior de cielo detectado automáticamente
  - shadow_pct  : % de sombra detectada y desambiguada
  - comparison  : dict opcional con comparación entre umbrales y K-means
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

import config

METHOD_YOLO = "YOLOv8"
METHOD_COLOR = "Estimación por color (LAB + HSV normalizado)"
METHOD_KMEANS = "K-means no supervisado (k=4 en espacio LAB)"


class ImageError(ValueError):
    """Error de validación de la imagen (mensaje listo para mostrar al usuario)."""


@dataclass
class DetectionResult:
    percentages: dict
    masks: dict
    annotated: np.ndarray
    method: str
    glacier_ok: bool = True
    warnings: list = field(default_factory=list)
    confidence: float = 1.0
    auto_sky_pct: float = 0.0
    shadow_pct: float = 0.0
    comparison: dict | None = None
    spectral_profiles: dict = field(default_factory=dict)


# ----------------------------------------------------------------------------
# Carga y validación
# ----------------------------------------------------------------------------
def load_image(source) -> np.ndarray:
    """Convierte bytes / ruta / PIL / ndarray en RGB uint8 validado y reducido."""
    try:
        if isinstance(source, np.ndarray):
            img = Image.fromarray(source.astype(np.uint8)).convert("RGB")
        elif isinstance(source, (bytes, bytearray)):
            if len(source) > config.MAX_FILE_MB * 1024 * 1024:
                raise ImageError(f"La imagen supera {config.MAX_FILE_MB} MB.")
            img = Image.open(io.BytesIO(source))
            img.load()
        elif isinstance(source, Image.Image):
            img = source
        else:
            img = Image.open(source)
            img.load()
        img = ImageOps.exif_transpose(img).convert("RGB")
    except ImageError:
        raise
    except Exception as exc:
        raise ImageError(
            "No se pudo leer el archivo como imagen. Usa JPG, PNG o WEBP válidos."
        ) from exc

    rgb = np.array(img, dtype=np.uint8)
    h, w = rgb.shape[:2]
    if min(h, w) < config.MIN_IMAGE_SIDE:
        raise ImageError(
            f"La imagen es demasiado pequeña ({w}x{h}px). Mínimo {config.MIN_IMAGE_SIDE}px por lado."
        )
    big = max(h, w)
    if big > config.MAX_IMAGE_SIDE:
        s = config.MAX_IMAGE_SIDE / big
        rgb = cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return rgb


# ----------------------------------------------------------------------------
# Normalización y preprocesamiento de iluminación (CLAHE en LAB)
# ----------------------------------------------------------------------------
def normalize_illumination(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Aplica CLAHE al canal L en espacio LAB para equilibrar sombras duras
    y sobreexposición en la nieve, conservando los canales de color.
    Retorna (rgb_normalizado, lab_normalizado).
    """
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l_chan)

    lab_norm = cv2.merge([l_clahe, a_chan, b_chan])
    rgb_norm = cv2.cvtColor(lab_norm, cv2.COLOR_LAB2RGB)
    return rgb_norm, lab_norm


# ----------------------------------------------------------------------------
# Detección automática de cielo
# ----------------------------------------------------------------------------
def detect_sky_cutoff(rgb: np.ndarray, max_search_pct: float = 50.0) -> int:
    """
    Detecta automáticamente el límite inferior del cielo en la zona superior.
    Busca regiones homogéneas (baja varianza de gradiente / color azul o gris uniforme).
    Devuelve el índice de fila de corte (0 si no se detecta cielo claro).
    """
    h, w = rgb.shape[:2]
    max_row = int(h * (max_search_pct / 100.0))
    if max_row < 5:
        return 0

    hsv = cv2.cvtColor(rgb[:max_row, :], cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb[:max_row, :], cv2.COLOR_RGB2GRAY)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.abs(sobel_y)

    H = hsv[..., 0]
    S = hsv[..., 1]
    V = hsv[..., 2]

    # Criterio de cielo: azul suave (H 90..135, S>30) o bruma/gris homogéneo (S < 45, V > 140)
    is_blue_sky = (H >= 85) & (H <= 135) & (S >= 25) & (V >= 70)
    is_overcast = (S <= 45) & (V >= 150)
    is_sky_candidate = is_blue_sky | is_overcast

    # Evaluar fila por fila desde la parte superior
    cut_row = 0
    consecutive_non_sky = 0

    # Analizar por bloques de 4 filas para mayor estabilidad
    step = 4
    for r in range(0, max_row - step, step):
        block_sky = is_sky_candidate[r:r+step, :]
        block_grad = grad_mag[r:r+step, :]
        sky_ratio = float(block_sky.mean())
        grad_mean = float(block_grad.mean())

        # Un cielo típico tiene alta proporción de candidatos y bajo gradiente
        if sky_ratio > 0.65 and grad_mean < 12.0:
            cut_row = r + step
            consecutive_non_sky = 0
        else:
            consecutive_non_sky += 1
            # Si encontramos 3 bloques consecutivos con textura/terreno, detenemos el cielo
            if consecutive_non_sky >= 3:
                break

    return cut_row


# ----------------------------------------------------------------------------
# Detección de sombras (para no confundirlas con carbono negro)
# ----------------------------------------------------------------------------
def detect_shadow_mask(rgb: np.ndarray, lab_norm: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """
    Identifica sombras en la nieve/roca:
    Baja luminancia relativa en la imagen original, pero con tonalidad fría/azulada difusa
    (típica de iluminación indirecta del cielo en la sombra) y recuperación notable en LAB-CLAHE.
    """
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    V_raw = hsv[..., 2]
    S_raw = hsv[..., 1]
    L_clahe = lab_norm[..., 0]
    B_lab = lab_norm[..., 2]  # B < 128 tiende a azul frío

    # Sombras: oscuras en imagen cruda (V < 90), pero en CLAHE se recuperan (L_clahe >= 75)
    # y muestran tinte frío (B_lab <= 135) con saturación baja/moderada.
    # En contraste, el hollín denso permanece muy oscuro incluso tras CLAHE (L_clahe < 70)
    # y tiene perfil espectral neutro o cálido.
    shadow = (
        (V_raw <= 85) &
        (L_clahe >= 75) &
        (S_raw <= 70) &
        (B_lab <= 136) &
        valid
    )
    # Suavizado morfológico para eliminar ruido aislado
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    shadow = cv2.morphologyEx(shadow.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    return shadow


# ----------------------------------------------------------------------------
# Limpieza morfológica
# ----------------------------------------------------------------------------
def _clean(mask: np.ndarray) -> np.ndarray:
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (config.MORPH_KERNEL,) * 2)
    m = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    return m.astype(bool)


# ----------------------------------------------------------------------------
# Método 2: Estimación por color (LAB + HSV normalizado)
# ----------------------------------------------------------------------------
def _color_masks(rgb: np.ndarray, valid: np.ndarray, lab_norm: np.ndarray | None = None,
                sensitivity_carbon=1.0, sensitivity_dust=1.0, sensitivity_water=1.0):
    """
    Segmentación por combinación de espacios LAB + HSV tras normalización CLAHE.
    Separa sombras para no clasificarlas como carbono negro.
    
    Args:
        sensitivity_carbon: Factor de sensibilidad para carbono negro (0.5-2.0)
        sensitivity_dust: Factor de sensibilidad para polvo (0.5-2.0)
        sensitivity_water: Factor de sensibilidad para agua (0.5-2.0)
    """
    if lab_norm is None:
        _, lab_norm = normalize_illumination(rgb)

    # Suavizado previo para reducir ruido de sensores
    rgb_blur = cv2.GaussianBlur(rgb, (5, 5), 0)
    hsv = cv2.cvtColor(rgb_blur, cv2.COLOR_RGB2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    L_clahe = lab_norm[..., 0]
    A_lab = lab_norm[..., 1]
    B_lab = lab_norm[..., 2]

    # Detectar máscara de sombras orográficas/proyectadas
    shadow_mask = detect_shadow_mask(rgb, lab_norm, valid)

    # 1. Carbono negro (hollín): muy oscuro TANTO en V como en L_clahe, y no es sombra
    # Ajustar umbral según sensibilidad (mayor sensibilidad = umbral más alto)
    v_thresh_carbon = config.HSV_BLACK_V_MAX * sensitivity_carbon
    l_thresh_carbon = 72 * sensitivity_carbon
    black = (V <= v_thresh_carbon) & (L_clahe <= l_thresh_carbon) & (~shadow_mask)

    # 2. Agua de deshielo: azul saturado característico
    c = config.HSV_MELT
    # Ajustar umbrales de saturación según sensibilidad
    s_thresh_water = max(c["s_min"] / sensitivity_water, 10)
    v_thresh_water = max(c["v_min"] / sensitivity_water, 30)
    melt = (H >= c["h_min"]) & (H <= c["h_max"]) & (S >= s_thresh_water) & (V >= v_thresh_water)
    # Refuerzo con LAB: B bajo indica azul fuerte
    b_thresh_water = 110 * (1.0 / sensitivity_water)
    melt |= (H >= 85) & (H <= 135) & (B_lab <= b_thresh_water) & (V >= 50)

    # 3. Polvo mineral / sedimento: marrón, ocre o gris con tonalidad térrea
    c = config.HSV_DUST
    # Ajustar umbrales según sensibilidad
    s_thresh_dust = max(c["s_min"] / sensitivity_dust, 5)
    v_thresh_dust = max(c["v_min"] / sensitivity_dust, 40)
    dust = (H >= c["h_min"]) & (H <= c["h_max"]) & (S >= s_thresh_dust) & (V >= v_thresh_dust)
    c = config.HSV_DUST_GRAY
    v_min_dust_gray = max(c["v_min"] / sensitivity_dust, 60)
    v_max_dust_gray = min(c["v_max"] * sensitivity_dust, 220)
    dust |= (S <= c["s_max"]) & (V >= v_min_dust_gray) & (V <= v_max_dust_gray) & (~shadow_mask)
    # Refuerzo LAB para sedimentos ocres: B_lab > 138 indica tonos amarillos/terrosos
    dust |= (B_lab >= 140) & (A_lab >= 126) & (V >= 50) & (V <= 190) & (~melt)

    # Limpieza morfológica
    black = _clean(black)
    melt = _clean(melt)
    dust = _clean(dust)

    # Prioridad de asignación: las sombras no absorbidas por carbón van a hielo limpio
    label = np.full(H.shape, 3, dtype=np.uint8)  # 3 = clean_ice
    label[dust] = 1
    label[melt] = 2
    label[black] = 0

    masks = {cls: (label == i) & valid for i, cls in enumerate(config.CLASSES)}

    # Detección de vegetación para control de calidad
    g = config.HSV_GREEN
    green = (H >= g["h_min"]) & (H <= g["h_max"]) & (S >= g["s_min"]) & (V >= g["v_min"])
    green_frac = float(green[valid].mean()) if valid.any() else 0.0

    shadow_frac = float(shadow_mask[valid].mean()) if valid.any() else 0.0
    return masks, green_frac, shadow_frac


# ----------------------------------------------------------------------------
# Método 3: K-means no supervisado (k=4 en espacio LAB)
# ----------------------------------------------------------------------------
def _kmeans_masks(rgb: np.ndarray, valid: np.ndarray, lab_norm: np.ndarray | None = None):
    """
    Segmentación por K-means (k=4) en espacio LAB con distancias perceptualmente uniformes.
    Asigna los 4 centroides a: clean_ice, black_carbon, dust, meltwater_pool.
    """
    if lab_norm is None:
        _, lab_norm = normalize_illumination(rgb)

    h, w = rgb.shape[:2]
    valid_coords = np.where(valid)
    if len(valid_coords[0]) < 100:
        # Fallback si hay poquísimos píxeles válidos
        return _color_masks(rgb, valid, lab_norm)[:2] + (0.0,)

    pixels_lab = lab_norm[valid_coords].astype(np.float32)

    # Criterio de parada para cv2.kmeans: 15 iteraciones o epsilon 0.5
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 0.5)
    flags = cv2.KMEANS_PP_CENTERS
    _, labels, centers = cv2.kmeans(pixels_lab, 4, None, criteria, 5, flags)

    labels = labels.flatten()

    # Mapeo de centroides [L, A, B] a clases:
    # L: 0..255 (luminancia), A: 0..255 (verde-rojo), B: 0..255 (azul-amarillo)
    # - Hielo limpio: mayor L
    # - Carbono negro: menor L
    # - De los 2 restantes:
    #     - Agua: menor B (más azul)
    #     - Polvo: mayor B (más amarillo/tierra)
    sorted_by_L = np.argsort(centers[:, 0])
    idx_black = int(sorted_by_L[0])
    idx_ice = int(sorted_by_L[-1])

    remaining = [i for i in range(4) if i not in (idx_black, idx_ice)]
    # Comparar canal B (centroide[:, 2]): menor B es azul (agua), mayor B es ocre (polvo)
    if centers[remaining[0], 2] < centers[remaining[1], 2]:
        idx_melt = remaining[0]
        idx_dust = remaining[1]
    else:
        idx_melt = remaining[1]
        idx_dust = remaining[0]

    cluster_to_class = {
        idx_black: "black_carbon",
        idx_dust: "dust",
        idx_melt: "meltwater_pool",
        idx_ice: "clean_ice",
    }

    full_labels = np.full((h, w), -1, dtype=np.int32)
    full_labels[valid_coords] = labels

    masks = {}
    for c_idx, c_name in cluster_to_class.items():
        m = (full_labels == c_idx) & valid
        masks[c_name] = _clean(m)

    # Exclusividad estricta garantizada
    taken = np.zeros((h, w), bool)
    for c in ("black_carbon", "meltwater_pool", "dust"):
        masks[c] = masks[c] & valid & ~taken
        taken |= masks[c]
    masks["clean_ice"] = valid & ~taken

    # Calcular fracción de verde
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    g = config.HSV_GREEN
    green = (hsv[..., 0] >= g["h_min"]) & (hsv[..., 0] <= g["h_max"]) & (hsv[..., 1] >= g["s_min"]) & (hsv[..., 2] >= g["v_min"])
    green_frac = float(green[valid].mean()) if valid.any() else 0.0

    return masks, green_frac, 0.0


# ----------------------------------------------------------------------------
# Índice de confianza (0.0 a 1.0)
# ----------------------------------------------------------------------------
def compute_confidence(rgb: np.ndarray, masks: dict, valid: np.ndarray) -> float:
    """
    Calcula un índice de calidad y certidumbre diagnóstica (0.0 - 1.0) evaluando:
    1. Rango dinámico y contraste de luminancia en la zona glaciar.
    2. Nitidez de bordes y coherencia morfológica.
    3. Ausencia de artefactos de sobreexposición (glare) o subexposición extrema.
    """
    if not valid.any():
        return 0.0

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    valid_gray = gray[valid]

    # 1. Rango dinámico (penaliza imágenes casi planas o quemadas)
    std_dev = float(np.std(valid_gray))
    score_contrast = np.clip(std_dev / 45.0, 0.2, 1.0)

    # 2. Exceso de saturación / pixeles quemados (valores > 252 o < 8)
    burned_pixels = float(((valid_gray > 252) | (valid_gray < 8)).mean())
    score_dynamic_range = max(0.0, 1.0 - burned_pixels * 2.5)

    # 3. Fragmentación de máscara (relación perímetro/área media)
    total_valid = float(valid.sum())
    coverage_ice = float(masks["clean_ice"].sum()) / total_valid

    # Un glaciar suele tener al menos una masa coherente de hielo o nieve
    score_ice_presence = 0.5 + 0.5 * min(coverage_ice / 0.35, 1.0)

    confidence = 0.40 * score_contrast + 0.35 * score_dynamic_range + 0.25 * score_ice_presence
    return float(np.clip(confidence, 0.15, 0.98))


def compute_spectral_profiles(rgb: np.ndarray, masks: dict, valid: np.ndarray) -> dict[str, dict]:
    """
    Calcula perfiles radiométricos (media y desviación de L en LAB, y recuento de píxeles)
    para cada clase clasificada dentro del área analizada.
    """
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l_chan = lab[..., 0]
    profiles = {}
    for c in config.CLASSES:
        m = masks.get(c)
        if m is not None and m.any():
            vals = l_chan[m]
            profiles[c] = {
                "mean_l": round(float(np.mean(vals)), 1),
                "std_l": round(float(np.std(vals)), 1),
                "pixel_count": int(len(vals)),
            }
        else:
            profiles[c] = {
                "mean_l": 0.0,
                "std_l": 0.0,
                "pixel_count": 0,
            }
    return profiles


# ----------------------------------------------------------------------------
# Método 1: YOLOv8 (opcional)
# ----------------------------------------------------------------------------
def _yolo_masks(rgb: np.ndarray, valid: np.ndarray, model_path: Path):
    """Ejecuta YOLOv8. Devuelve (masks, cajas) o lanza excepción si falla."""
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    res = model.predict(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), verbose=False)[0]
    names = {int(k): str(v).lower() for k, v in res.names.items()}
    h, w = rgb.shape[:2]
    masks = {c: np.zeros((h, w), bool) for c in config.CONTAMINANTS}
    boxes = []

    if res.boxes is not None:
        polys = res.masks.xy if res.masks is not None else None
        for i, box in enumerate(res.boxes):
            cls = names.get(int(box.cls[0]))
            if cls not in masks:
                continue
            canvas = np.zeros((h, w), np.uint8)
            if polys is not None and len(polys[i]) >= 3:
                cv2.fillPoly(canvas, [polys[i].astype(np.int32)], 1)
            else:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                canvas[max(y1, 0):y2, max(x1, 0):x2] = 1
                boxes.append((x1, y1, x2, y2, cls))
            masks[cls] |= canvas.astype(bool)

    taken = np.zeros((h, w), bool)
    out = {}
    for cls in ("black_carbon", "meltwater_pool", "dust"):
        out[cls] = masks[cls] & valid & ~taken
        taken |= out[cls]
    out["clean_ice"] = valid & ~taken
    return {c: out[c] for c in config.CLASSES}, boxes


# ----------------------------------------------------------------------------
# Anotación
# ----------------------------------------------------------------------------
def _annotate(rgb, masks, pct, valid, boxes=(), confidence: float = 1.0):
    out = rgb.copy()
    for cls in config.CONTAMINANTS:
        m = masks[cls]
        if not m.any():
            continue
        col = np.array(config.COLORS_RGB[cls], dtype=np.float32)
        out[m] = (0.55 * out[m].astype(np.float32) + 0.45 * col).astype(np.uint8)
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = [c for c in cnts if cv2.contourArea(c) > 40]
        cv2.drawContours(out, cnts, -1, config.COLORS_RGB[cls], 2)
    for x1, y1, x2, y2, cls in boxes:
        cv2.rectangle(out, (x1, y1), (x2, y2), config.COLORS_RGB[cls], 2)

    if not valid.all():
        y = int(np.argmax(valid.any(axis=1)))
        out[:y] = (out[:y] * 0.35).astype(np.uint8)
        cv2.line(out, (0, y), (out.shape[1], y), (255, 255, 255), 2)
        cv2.putText(out, "ZONA EXCLUIDA (CIELO)", (12, max(22, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    # Leyenda
    w = out.shape[1]
    fs = max(0.45, w / 1100 * 0.6)
    th = max(1, int(fs * 2))
    row = int(34 * fs / 0.6)
    pad = 8
    box_w = int(340 * fs / 0.6)
    # Fila adicional para índice de confianza
    box_h = row * (len(config.CLASSES) + 1) + pad * 2
    y0 = int(out.shape[0] * 0)
    ov = out.copy()
    cv2.rectangle(ov, (6, 6 + y0), (6 + box_w, 6 + y0 + box_h), (20, 20, 20), -1)
    out = cv2.addWeighted(ov, 0.65, out, 0.35, 0)
    for i, cls in enumerate(config.CLASSES):
        y = 6 + y0 + pad + row * i + row // 2
        cv2.rectangle(out, (14, y - row // 3), (14 + row // 2, y + row // 3),
                      config.COLORS_RGB[cls], -1)
        cv2.putText(out, f"{config.LABELS_ES[cls]}: {pct[cls]:.1f}%",
                    (14 + row // 2 + 8, y + row // 6), cv2.FONT_HERSHEY_SIMPLEX,
                    fs, (255, 255, 255), th, cv2.LINE_AA)

    # Línea de confianza
    y_conf = 6 + y0 + pad + row * len(config.CLASSES) + row // 2
    conf_col = (50, 220, 100) if confidence >= 0.65 else (50, 160, 240) if confidence >= 0.50 else (60, 60, 240)
    cv2.putText(out, f"Confianza estimada: {confidence * 100:.0f}%",
                (14, y_conf + row // 6), cv2.FONT_HERSHEY_SIMPLEX,
                fs * 0.9, conf_col, th, cv2.LINE_AA)
    return out


# ----------------------------------------------------------------------------
# API principal (retrocompatible)
# ----------------------------------------------------------------------------
def detect(
    rgb: np.ndarray,
    ignore_top_pct: float = 0.0,
    use_yolo: bool = False,
    method_name: str = "color",
    auto_sky: bool = True,
    compare_kmeans: bool = False,
    sensitivity_carbon: float = 1.0,
    sensitivity_dust: float = 1.0,
    sensitivity_water: float = 1.0,
) -> DetectionResult:
    """
    Analiza una imagen RGB y devuelve cobertura por clase, máscara y métricas.

    Parámetros:
    -----------
    rgb : np.ndarray
        Imagen RGB (H×W×3, uint8).
    ignore_top_pct : float
        porcientaje manual superior a excluir como cielo (0-60).
    use_yolo : bool
        Si True y existe el modelo YOLOv8, se prioriza.
    method_name : str
        "color" (LAB+HSV con CLAHE) o "kmeans" (K-means en espacio LAB).
    auto_sky : bool
        Si True, detecta automáticamente la franja de cielo homogéneo.
    compare_kmeans : bool
        Si True, calcula también la alternativa y la adjunta en result.comparison.
    """
    h, w = rgb.shape[:2]

    # 1. Detección de cielo: auto-detección combinada con el slider manual
    auto_cut = 0
    if auto_sky:
        auto_cut = detect_sky_cutoff(rgb)

    manual_cut = int(h * ignore_top_pct / 100.0)
    final_cut = max(auto_cut, manual_cut)

    if final_cut >= h - 1:
        raise ImageError("La zona de cielo cubre toda la imagen. Reduce el porcientaje.")

    valid = np.ones((h, w), bool)
    valid[:final_cut] = False

    # 2. Normalización de iluminación (CLAHE sobre canal L en LAB)
    rgb_norm, lab_norm = normalize_illumination(rgb)

    warnings, boxes, method = [], [], METHOD_COLOR
    masks = None
    shadow_frac = 0.0

    # 3. Intentar YOLOv8 si corresponde
    if use_yolo and config.MODEL_PATH.exists():
        try:
            masks, boxes = _yolo_masks(rgb, valid, config.MODEL_PATH)
            method = METHOD_YOLO
        except Exception as exc:
            warnings.append(f"No se pudo usar YOLOv8 ({type(exc).__name__}). Se usó estimación por color.")
            masks = None

    # 4. Métodos clásicos (Color LAB+HSV o K-means)
    comparison_data = None
    if masks is None:
        if method_name.lower() == "kmeans":
            masks, green_frac, shadow_frac = _kmeans_masks(rgb, valid, lab_norm)
            method = METHOD_KMEANS
        else:
            masks, green_frac, shadow_frac = _color_masks(
                rgb, valid, lab_norm,
                sensitivity_carbon=sensitivity_carbon,
                sensitivity_dust=sensitivity_dust,
                sensitivity_water=sensitivity_water,
            )
            method = METHOD_COLOR

        # Cálculo de comparación opcional si se solicita
        if compare_kmeans:
            alt_masks, _, _ = (
                _color_masks(rgb, valid, lab_norm,
                             sensitivity_carbon=sensitivity_carbon,
                             sensitivity_dust=sensitivity_dust,
                             sensitivity_water=sensitivity_water)
                if method_name.lower() == "kmeans"
                else _kmeans_masks(rgb, valid, lab_norm)
            )
            total_v = float(valid.sum())
            alt_pct = {c: float(100.0 * alt_masks[c].sum() / total_v) for c in config.CLASSES}
            alt_pct["clean_ice"] = 100.0 - sum(alt_pct[c] for c in config.CONTAMINANTS)
            alt_name = METHOD_COLOR if method_name.lower() == "kmeans" else METHOD_KMEANS
            comparison_data = {"method": alt_name, "percentages": alt_pct}
    else:
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        g = config.HSV_GREEN
        gm = ((hsv[..., 0] >= g["h_min"]) & (hsv[..., 0] <= g["h_max"])
              & (hsv[..., 1] >= g["s_min"]) & (hsv[..., 2] >= g["v_min"]))
        green_frac = float(gm[valid].mean())

    total = float(valid.sum())
    pct = {c: float(100.0 * masks[c].sum() / total) for c in config.CLASSES}
    # Asegurar que la suma sea exactamente 100.0 %
    pct["clean_ice"] = max(0.0, 100.0 - sum(pct[c] for c in config.CONTAMINANTS))

    # 5. Índice de confianza
    confidence = compute_confidence(rgb, masks, valid)

    # 6. Avisos y diagnósticos
    glacier_ok = green_frac <= config.GREEN_MAX_FRACTION
    if not glacier_ok:
        warnings.append("La imagen presenta alta proporción de vegetación: es probable que no corresponda a un cuerpo glaciar.")

    if confidence < 0.60:
        warnings.append(
            f"Índice de confianza bajo ({confidence:.2f}): contraste o iluminación irregular. "
            "Se recomienda verificar la máscara de segmentación."
        )

    if shadow_frac > 0.08:
        warnings.append(
            f"Sombras orográficas detectadas ({shadow_frac * 100:.1f} % del área). "
            "El algoritmo CLAHE las diferenció para evitar sobreestimar carbono negro."
        )

    if auto_cut > manual_cut and auto_cut > 0:
        warnings.append(
            f"Cielo detectado automáticamente ({auto_cut * 100.0 / h:.1f} % superior excluido). "
            "Puede ajustarse manualmente con la barra deslizante."
        )

    if method == METHOD_COLOR or method == METHOD_KMEANS:
        warnings.append(
            f"{method}: clasificación espectral superficial. "
            "Mediciones in situ de balance de masa requieren calibración multiespectral."
        )

    annotated = _annotate(rgb, masks, pct, valid, boxes, confidence)

    auto_sky_pct = round(final_cut * 100.0 / h, 1)
    shadow_pct = round(shadow_frac * 100.0, 1)
    profiles = compute_spectral_profiles(rgb, masks, valid)

    return DetectionResult(
        percentages=pct,
        masks=masks,
        annotated=annotated,
        method=method,
        glacier_ok=glacier_ok,
        warnings=warnings,
        confidence=confidence,
        auto_sky_pct=auto_sky_pct,
        shadow_pct=shadow_pct,
        comparison=comparison_data,
        spectral_profiles=profiles,
    )
