"""
advanced_analysis.py
====================
Módulo de análisis avanzado para detección de características glaciares complejas.

Funcionalidades:
- Detección de bioalbedo (algas y crioconita)
- Análisis de rugosidad superficial (indicador de ablación)
- Detección de grietas y cavidades superficiales
- Análisis de distribución espacial de contaminantes
- Estimación de espesor relativo por sombreado
- Índices espectrales (NDVI, NDWI, NDSI)
"""
from __future__ import annotations

import numpy as np
import cv2
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

import config


@dataclass
class AdvancedAnalysisResult:
    """Resultado del análisis avanzado."""
    bioalbedo_detected: bool
    bioalbedo_percentage: float
    bioalbedo_map: np.ndarray
    
    crevasses_detected: bool
    crevasse_count: int
    crevasse_map: np.ndarray
    
    roughness_index: float  # 0-1: 0=suave, 1=muy rugoso
    roughness_map: np.ndarray
    
    ndvi: float  # Normalized Difference Vegetation Index
    ndwi: float  # Normalized Difference Water Index
    ndsi: float  # Normalized Difference Snow Index
    
    spatial_distribution: Dict[str, float]  # Concentración por cuadrante
    contamination_clusters: int
    
    estimated_thickness_map: np.ndarray  # Mapa relativo de espesor
    
    warnings: list
    confidence: float


def detect_bioalbedo(img_rgb: np.ndarray, 
                     clean_ice_mask: np.ndarray,
                     dust_mask: np.ndarray) -> Tuple[bool, float, np.ndarray]:
    """
    Detecta presencia de bioalbedo (algas de nieve y crioconita).
    
    Método:
    - Busca píxeles con tonalidad verdosa/rojiza en hielo
    - Analiza agregados oscuros pequeños (crioconita: 1-5mm)
    - Usa análisis de textura para diferenciar de polvo inerte
    
    Returns:
        (detectado, porcientaje, mapa_binario)
    """
    h, w = img_rgb.shape[:2]
    bioalbedo_mask = np.zeros((h, w), dtype=bool)
    
    # Convertir a LAB y HSV
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    
    L, A, B = cv2.split(lab)
    H, S, V = cv2.split(hsv)
    
    # 1. Detección de algas (tonos verdes/rojos en hielo)
    # Algas tienen pigmentos que reflejan en verde (clorofila) o rojo (carotenoides)
    algae_green = (H >= 35) & (H <= 85) & (S > 30) & (V > 60) & clean_ice_mask
    algae_red = (H >= 0) & (H <= 15) & (S > 40) & (V > 70) & clean_ice_mask
    
    # 2. Detección de crioconita (agregados oscuros pequeños en hielo)
    # Crioconita: partículas muy oscuras (V < 80) pero con textura granular
    dark_ice = (V < 80) & (L < 120) & clean_ice_mask
    
    # Filtrar por tamaño (crioconita: 1-5mm, asumiendo ~2-10 píxeles)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dark_ice_morphed = cv2.morphologyEx(dark_ice.astype(np.uint8), 
                                         cv2.MORPH_OPEN, kernel_small)
    
    # 3. Análisis de textura para distinguir de polvo
    # Bioalbedo tiene textura más granular/punteada que polvo uniforme
    texture = cv2.Laplacian(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY), cv2.CV_64F)
    texture_var = cv2.GaussianBlur(np.abs(texture), (5, 5), 0)
    high_texture = texture_var > np.percentile(texture_var[clean_ice_mask], 70)
    
    # Combinar criterios
    bioalbedo_mask = (algae_green | algae_red | 
                      (dark_ice_morphed.astype(bool) & high_texture))
    
    # Calcular porcentaje
    total_glacier = clean_ice_mask.sum() + dust_mask.sum()
    if total_glacier > 0:
        percentage = 100.0 * bioalbedo_mask.sum() / total_glacier
    else:
        percentage = 0.0
    
    detected = percentage > 0.5  # Umbral: >0.5% de cobertura
    
    return detected, percentage, bioalbedo_mask


def detect_crevasses(img_rgb: np.ndarray, 
                     ice_mask: np.ndarray) -> Tuple[bool, int, np.ndarray]:
    """
    Detecta grietas (crevasses) en la superficie glaciar.
    
    Método:
    - Detección de bordes con Canny
    - Transformada de Hough para líneas
    - Filtrado por orientación y longitud
    
    Returns:
        (detectado, cantidad, mapa_binario)
    """
    h, w = img_rgb.shape[:2]
    crevasse_map = np.zeros((h, w), dtype=np.uint8)
    
    # Convertir a escala de grises
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    
    # Aplicar CLAHE para mejorar contraste
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Detección de bordes en zona glaciar
    edges = cv2.Canny(enhanced, 30, 100)
    edges = edges & ice_mask.astype(np.uint8) * 255
    
    # Transformada de Hough probabilística
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                            minLineLength=30, maxLineGap=10)
    
    crevasse_count = 0
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            
            # Filtrar grietas (longitud > 30 píxeles, no horizontales perfectas)
            angle = np.abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)
            if length > 30 and not (angle > 85 and angle < 95):
                cv2.line(crevasse_map, (x1, y1), (x2, y2), 255, 2)
                crevasse_count += 1
    
    detected = crevasse_count > 3
    crevasse_map = crevasse_map.astype(bool)
    
    return detected, crevasse_count, crevasse_map


def calculate_roughness(img_rgb: np.ndarray, 
                        ice_mask: np.ndarray) -> Tuple[float, np.ndarray]:
    """
    Calcula índice de rugosidad superficial.
    
    Rugosidad alta indica:
    - Ablación activa (fusión desigual)
    - Presencia de crioconita y penitentes
    - Superficie envejecida
    
    Returns:
        (índice_global [0-1], mapa_espacial)
    """
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    
    # 1. Varianza local de intensidad
    kernel_size = 15
    mean = cv2.blur(gray.astype(float), (kernel_size, kernel_size))
    sqr_mean = cv2.blur((gray.astype(float))**2, (kernel_size, kernel_size))
    variance = sqr_mean - mean**2
    variance = np.clip(variance, 0, None)
    
    # 2. Gradiente de Sobel
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
    gradient_mag = np.sqrt(sobelx**2 + sobely**2)
    
    # 3. Laplaciano (segunda derivada)
    laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_64F, ksize=5))
    
    # Combinar métricas
    roughness_map = (variance / 255.0) * 0.4 + \
                    (gradient_mag / gradient_mag.max()) * 0.3 + \
                    (laplacian / laplacian.max()) * 0.3
    
    # Normalizar a [0, 1]
    roughness_map = np.clip(roughness_map, 0, 1)
    
    # Índice global (solo en zona glaciar)
    if ice_mask.sum() > 0:
        roughness_index = float(roughness_map[ice_mask].mean())
    else:
        roughness_index = 0.0
    
    return roughness_index, roughness_map


def calculate_spectral_indices(img_rgb: np.ndarray,
                                ice_mask: np.ndarray) -> Dict[str, float]:
    """
    Calcula índices espectrales aproximados desde RGB.
    
    NOTA: RGB tiene limitaciones vs. multispectral real, pero permite
    estimaciones útiles para análisis exploratorio.
    
    Returns:
        dict con NDVI, NDWI, NDSI
    """
    # Normalizar a [0, 1]
    R = img_rgb[:, :, 0].astype(float) / 255.0
    G = img_rgb[:, :, 1].astype(float) / 255.0
    B = img_rgb[:, :, 2].astype(float) / 255.0
    
    # NDVI aproximado: (G - R) / (G + R)
    # En imágenes RGB, verde alto y rojo bajo indica vegetación
    ndvi = np.where((G + R) > 0, (G - R) / (G + R), 0)
    
    # NDWI aproximado: (G - NIR) / (G + NIR)
    # Sin NIR real, usamos B como proxy (agua refleja más en azul)
    ndwi = np.where((G + B) > 0, (G - B) / (G + B), 0)
    
    # NDSI aproximado: (G - SWIR) / (G + SWIR)
    # Sin SWIR, usamos R como proxy (nieve refleja en verde)
    ndsi = np.where((G + R) > 0, (G - R) / (G + R), 0)
    
    # Promedios en zona glaciar
    if ice_mask.sum() > 0:
        ndvi_mean = float(ndvi[ice_mask].mean())
        ndwi_mean = float(ndwi[ice_mask].mean())
        ndsi_mean = float(ndsi[ice_mask].mean())
    else:
        ndvi_mean = ndwi_mean = ndsi_mean = 0.0
    
    return {
        'ndvi': ndvi_mean,
        'ndwi': ndwi_mean,
        'ndsi': ndsi_mean
    }


def analyze_spatial_distribution(masks: Dict[str, np.ndarray],
                                 img_shape: Tuple[int, int]) -> Dict[str, float]:
    """
    Analiza distribución espacial de contaminantes.
    
    Divide la imagen en cuadrantes y calcula concentración.
    Útil para identificar zonas de mayor deposición.
    
    Returns:
        dict con concentración por zona
    """
    h, w = img_shape
    mid_h, mid_w = h // 2, w // 2
    
    quadrants = {
        'superior_izq': (0, mid_h, 0, mid_w),
        'superior_der': (0, mid_h, mid_w, w),
        'inferior_izq': (mid_h, h, 0, mid_w),
        'inferior_der': (mid_h, h, mid_w, w)
    }
    
    distribution = {}
    
    # Combinar máscaras de contaminantes
    contaminant_mask = np.zeros((h, w), dtype=bool)
    for cls in config.CONTAMINANTS:
        if cls in masks:
            contaminant_mask |= masks[cls]
    
    for name, (y1, y2, x1, x2) in quadrants.items():
        quadrant_area = (y2 - y1) * (x2 - x1)
        if quadrant_area > 0:
            contamination = contaminant_mask[y1:y2, x1:x2].sum()
            distribution[name] = 100.0 * contamination / quadrant_area
        else:
            distribution[name] = 0.0
    
    return distribution


def estimate_thickness_map(img_rgb: np.ndarray,
                           ice_mask: np.ndarray) -> np.ndarray:
    """
    Estima mapa RELATIVO de espesor basado en sombreado y reflectancia.
    
    Asunciones:
    - Hielo más grueso tiende a ser más brillante (menos impurezas)
    - Zonas sombreadas pueden indicar depresiones
    
    NOTA: Es una estimación cualitativa, NO cuantitativa.
    
    Returns:
        mapa normalizado [0-1] donde 1 = más grueso relativo
    """
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    L = lab[:, :, 0].astype(float)
    
    # Normalizar luminancia
    L_norm = L / 255.0
    
    # Aplicar suavizado para reducir ruido
    L_smooth = cv2.GaussianBlur(L_norm, (21, 21), 0)
    
    # Máscara de hielo
    thickness_map = np.zeros_like(L_smooth)
    thickness_map[ice_mask] = L_smooth[ice_mask]
    
    # Normalizar al rango del glaciar
    if ice_mask.sum() > 0:
        ice_values = thickness_map[ice_mask]
        vmin, vmax = ice_values.min(), ice_values.max()
        if vmax > vmin:
            thickness_map[ice_mask] = (ice_values - vmin) / (vmax - vmin)
    
    return thickness_map


def perform_advanced_analysis(img_rgb: np.ndarray,
                              masks: Dict[str, np.ndarray],
                              percentages: Dict[str, float]) -> AdvancedAnalysisResult:
    """
    Ejecuta análisis avanzado completo de la imagen glaciar.
    
    Args:
        img_rgb: Imagen RGB original
        masks: Diccionario de máscaras de detección básica
        percentages: porcientajes de cobertura básica
        
    Returns:
        AdvancedAnalysisResult con todos los análisis
    """
    warnings = []
    h, w = img_rgb.shape[:2]
    
    # Crear máscara combinada de hielo
    ice_mask = masks.get('clean_ice', np.zeros((h, w), dtype=bool))
    dust_mask = masks.get('dust', np.zeros((h, w), dtype=bool))
    full_glacier_mask = ice_mask | dust_mask
    
    # 1. Bioalbedo
    bio_detected, bio_pct, bio_map = detect_bioalbedo(img_rgb, ice_mask, dust_mask)
    if bio_detected:
        warnings.append(
            f"⚠️ Bioalbedo detectado ({bio_pct:.1f}%): Posible presencia de algas "
            "o crioconita. Aceleración de fusión +10-30% adicional."
        )
    
    # 2. Grietas
    crev_detected, crev_count, crev_map = detect_crevasses(img_rgb, full_glacier_mask)
    if crev_detected:
        warnings.append(
            f"⚠️ {crev_count} grietas detectadas: Indica tensión glaciar activa "
            "y posible fragmentación."
        )
    
    # 3. Rugosidad
    roughness_idx, roughness_map = calculate_roughness(img_rgb, full_glacier_mask)
    if roughness_idx > 0.6:
        warnings.append(
            f"⚠️ Superficie muy rugosa (índice: {roughness_idx:.2f}): "
            "Indica ablación avanzada y envejecimiento."
        )
    
    # 4. Índices espectrales
    spectral = calculate_spectral_indices(img_rgb, full_glacier_mask)
    
    # 5. Distribución espacial
    spatial_dist = analyze_spatial_distribution(masks, (h, w))
    
    # Detectar clusters de contaminación
    contaminant_mask = np.zeros((h, w), dtype=np.uint8)
    for cls in config.CONTAMINANTS:
        if cls in masks:
            contaminant_mask[masks[cls]] = 255
    
    num_labels, labels = cv2.connectedComponents(contaminant_mask)
    contamination_clusters = num_labels - 1  # Restar fondo
    
    # 6. Espesor relativo
    thickness_map = estimate_thickness_map(img_rgb, ice_mask)
    
    # Calcular confianza del análisis (más realista)
    confidence = 0.50  # Base conservadora
    
    # Factor 1: Cobertura glaciar en imagen
    glacier_coverage = full_glacier_mask.sum() / (h * w)
    if glacier_coverage > 0.4:  # >40% es glaciar
        confidence += 0.20
    elif glacier_coverage > 0.2:  # >20% es glaciar
        confidence += 0.10
    elif glacier_coverage > 0.1:  # >10% es glaciar
        confidence += 0.05
    
    # Factor 2: Calidad de imagen (no muy ruidosa)
    if roughness_idx < 0.7:
        confidence += 0.10
    elif roughness_idx < 0.85:
        confidence += 0.05
    
    # Factor 3: Coherencia de detecciones
    detections_count = sum([bio_detected, crev_detected, contamination_clusters > 0])
    if detections_count >= 2:
        confidence += 0.05
    
    # Factor 4: Índices espectrales coherentes
    if spectral['ndsi'] > 0.3:  # NDSI alto indica nieve/hielo
        confidence += 0.05
    
    # Penalización por incertidumbre RGB (no es multiespectral real)
    confidence *= 0.90  # -10% por limitaciones RGB
    
    # Limitar a máximo 85% (nunca 100% con RGB)
    confidence = min(confidence, 0.85)
    
    return AdvancedAnalysisResult(
        bioalbedo_detected=bio_detected,
        bioalbedo_percentage=bio_pct,
        bioalbedo_map=bio_map,
        crevasses_detected=crev_detected,
        crevasse_count=crev_count,
        crevasse_map=crev_map,
        roughness_index=roughness_idx,
        roughness_map=roughness_map,
        ndvi=spectral['ndvi'],
        ndwi=spectral['ndwi'],
        ndsi=spectral['ndsi'],
        spatial_distribution=spatial_dist,
        contamination_clusters=contamination_clusters,
        estimated_thickness_map=thickness_map,
        warnings=warnings,
        confidence=confidence
    )
