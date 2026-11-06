# GlaciarSense - Diagnostico, Albedo y Proyeccion de Glaciares

Sistema de analisis computacional y geoespacial desarrollado en Streamlit para cuantificar el impacto de impurezas y contaminantes superficiales (carbono negro, polvo mineral, agua de deshielo) sobre la degradacion del albedo, la aceleracion termica y las trayectorias de retroceso de cuerpos glaciares.

---

## 1. Caracteristicas y Metodologia

| Componente | Metodologia | Detalle Tecnico |
|---|---|---|
| **Vision Computacional** (`detector.py`) | **Normalizacion CLAHE (LAB)** | Ecualizacion adaptativa de histograma sobre luminancia (L) para mitigar sombras orograficas duras y reflejos sin alterar el croma. |
| **Vision Computacional** (`detector.py`) | **Exclusion de Cielo** | Analisis de gradiente vertical y varianza espectral para recortar cielo homogeneo superior (mantiene ajuste manual complementario). |
| **Vision Computacional** (`detector.py`) | **Desambiguacion de Sombras** | Filtrado en espacio LAB (canal B frio) y contraste relativo para evitar falsos positivos de carbono negro en zonas de penumbra. |
| **Vision Computacional** (`detector.py`) | **Clustering K-means (k=4 LAB)** | Algoritmo no supervisado alternativo basado en distancias euclidianas perceptuales y comparacion directa con segmentacion por umbrales. |
| **Vision Computacional** (`detector.py`) | **Indice de Confianza (0 a 1)** | Evaluacion integral de contraste, rango dinamico no saturado y coherencia morfologica superficial. |
| **Modelo Fisico** (`gis_engine.py`) | **Escenarios Climaticos SSP** | Integracion de multiplicadores forzantes de los escenarios SSP1-2.6, SSP2-4.5 y SSP5-8.5 (IPCC AR6). |
| **Modelo Fisico** (`gis_engine.py`) | **Retroceso No Lineal (Exponencial)** | Modelo asintotico $A(t) = A_0 \exp(-\lambda t)$ comparado con la reduccion lineal continua. |
| **Incertidumbre** (`gis_engine.py`) | **Simulacion Monte Carlo (1,000 corridas)** | Propagacion estocastica de incertidumbre en sensibilidad $k$ (+/-25%), tasa historica (+/-20%) y albedos (+/-10%), con calculo de Mediana, P10 y P90. |
| **Motor GIS** (`gis_engine.py`) | **Contorno Vectorial GeoJSON** | Carga de contorno poligonal oficial en `data/` (ej. `pastoruri.geojson` de INAIGEM) o elipse parametrica proyectada en coordenadas UTM metricas. |
| **Comparacion** (`app.py`) | **Comparativa Multi-Imagen (2 a 5 fotos)** | Procesamiento en lote para contrastar la evolucion de coberturas y la degradacion del albedo efectivo. |
| **Exportacion** (`utils/pdf_report.py`) | **Reporte Tecnico PDF y CSV** | Generacion de informes tecnicos estructurados con fotografia clasificada, tablas parametricas y analisis de incertidumbre. |
| **Datos Abiertos** (`scripts/descargar_datos.py`) | **Modulo Panorama Global** | Registro oficial abierto consolidado del WGMS (World Glacier Monitoring Service) e inventario RGI a nivel andino y global. |
| **Conocimiento Glaciar** (`app.py`) | **Modulo Educativo Avanzado** | Exploracion de 6 temas criticos: topografia basal, puntos de no retorno, agua subglacial, bioalbedo, avalanchas y saberes comunitarios con bibliografia cientifica completa. |

---

## 2. Instalacion y Ejecucion

**Requisitos:** Python 3.10, 3.11 o 3.12 (Windows, macOS o Linux).

### Paso 1 - Entorno Virtual
```bash
python -m venv venv
```
- **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
- **Windows (CMD):** `.\venv\Scripts\activate.bat`
- **Linux / macOS:** `source venv/bin/activate`

### Paso 2 - Dependencias
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 3 - Ejecutar la Aplicacion
En Windows puedes simplemente hacer doble clic en `iniciar_app.bat` o ejecutar:
```bash
.\venv\Scripts\python.exe -m streamlit run app.py
```
Si tienes el entorno virtual previamente activado (`.\venv\Scripts\activate`):
```bash
streamlit run app.py
```

---

## 3. Pruebas Unitarias (`pytest`)

El proyecto cuenta con una bateria automatizada de 21 pruebas unitarias que validan la precision numerica y fisica:

```bash
python -m pytest tests -v
```

Puntos clave verificados en las pruebas:
- `tests/test_detector.py`: Valida que el error en imagenes calibradas con cobertura conocida sea inferior a +/-5 puntos porcentuales, suma 100%, exclusion automatica de cielo y desambiguacion de sombras.
- `tests/test_gis_engine.py`: Valida formulas fisicas de albedo y aceleracion Delta M, convergencia de 1,000 corridas Monte Carlo, escenarios SSP y carga de GeoJSON.
- `tests/test_pdf.py`: Valida la construccion del documento PDF en memoria y sus cabeceras.

---

## 4. Estructura del Repositorio

```
glaciar_app/
|-- app.py                      # Interfaz interactiva Streamlit (5 pestanias)
|-- detector.py                 # Procesamiento de imagen, CLAHE, K-means y perfiles L*
|-- gis_engine.py               # Modelado matematico, proyeccion UTM, SSP, Monte Carlo y tornado
|-- config.py                   # Parametros de calibracion y constantes fisicas
|-- iniciar_app.bat             # Lanzador automatico para Windows (doble clic)
|-- iniciar_app.ps1             # Lanzador para PowerShell
|-- pytest.ini                  # Configuracion de ejecucion para pytest
|-- requirements.txt            # Dependencias del proyecto
|-- README.md                   # Documentacion tecnica del sistema
|-- data/
|   |-- pastoruri.geojson       # Contorno vectorial del inventario nacional (INAIGEM)
|   |-- quelccaya.geojson       # Contorno vectorial del casquete Quelccaya
|   |-- wgms_global_regions.csv # Inventario de reduccion por macrorregion (WGMS / IPCC)
|   |-- wgms_andean_glaciers.csv# Series temporales observadas en glaciares andinos
|   `-- REFERENCIAS_CONOCIMIENTO_GLACIAR.md # Bibliografia cientifica del modulo educativo
|-- scripts/
|   `-- descargar_datos.py      # Utilidad de verificacion de datos abiertos oficiales
|-- tests/
|   |-- test_detector.py        # Pruebas de vision computacional y sinteticos calibrados
|   |-- test_gis_engine.py      # Pruebas de formulacion fisica y casos limite
|   `-- test_pdf.py             # Pruebas de exportacion documental
`-- utils/
    |-- sample_images.py        # Generador de muestras sinteticas con ruido textural
    `-- pdf_report.py           # Generador de informes tecnicos en PDF (fpdf2)
```

---

## 5. Fundamentacion Matematica

1. **Albedo Efectivo**:
   $$\alpha_{ef} = \sum_{i} f_i \cdot \alpha_i$$
   donde $f_i$ representa la fraccion de cobertura de cada material y $\alpha_i$ su reflectancia de referencia.

2. **Aceleracion de Absorcion Solar ($\Delta M$)**:
   $$\Delta M = \max\left(\frac{1 - \alpha_{ef}}{1 - \alpha_{limpio}} - 1,\; 0\right)$$

3. **Tasa Ajustada de Fusion**:
   $$Factor = \text{clip}(k \cdot \Delta M,\; 0,\; 1.5)$$
   $$R_{ajustada} = R_{historica} \times (1 + Factor)$$

4. **Tiempo de Vida Restante**:
   - Modelo lineal: $T = \frac{A_0}{R_{ajustada}}$
   - Modelo exponencial: $A(t) = A_0 \exp\left(-\frac{R_{ajustada}}{A_0} \cdot t\right)$

---

## 6. Modulo de Conocimiento Glaciar

La pestaña **"Conocimiento Glaciar"** es un recurso educativo avanzado que explora procesos complejos que trascienden el análisis superficial de imágenes:

### Temas Cubiertos

1. **🏔️ Cavidades Ocultas y Topografía Basal**
   - Sobreexcavaciones glaciales (*overdeepenings*) y riesgo de colapso abrupto
   - Geometría del lecho rocoso y su influencia en la estabilidad
   - Técnicas de caracterización: radar de penetración (GPR), batimetría
   - Riesgo de formación de lagos proglaciares y eventos GLOF

2. **♻️ Puntos de No Retorno Irreversibles (Inercia Glaciar)**
   - Tiempo de respuesta glaciar: décadas de desfase entre clima y geometría
   - Línea de Equilibrio Altitudinal (ELA) y balance de masa negativo
   - Retroalimentación albedo-temperatura como ciclo autosostenido
   - Proyecciones IPCC AR6: pérdida comprometida incluso bajo SSP1-2.6

3. **💧 Dinámica del Agua Subglacial y Sedimentos**
   - Canales subglaciales de Röthlisberger vs. películas de agua de Weertman
   - Aceleración del deslizamiento basal por lubricación hídrica
   - Erosión del lecho: tasas de 1-10 mm/año y transporte de sedimentos
   - Impacto en infraestructura: colmatación de embalses hidroeléctricos

4. **🦠 Bioalbedo y Ecosistemas Microbianos**
   - Algas de nieve (*Chlamydomonas nivalis*, *Sanguina nivaloides*)
   - Reducción de albedo de 0.85 a 0.40-0.60 por pigmentos carotenoides
   - Cianobacterias, bacterias heterótrofas y formación de crioconita
   - Retroalimentación bioalbedo-clima: aceleración del 10-30% en tasas de fusión
   - Detección remota con índices espectrales (NDVI, NDWI)

5. **❄️ Contribución de Avalanchas a Gran Altitud**
   - Recarga episódica desde paredes rocosas empinadas (>45°)
   - Aporte del 30-50% del balance de masa en glaciares de circo
   - Variabilidad espacial del espesor no capturada por modelos continuos
   - Monitoreo con InSAR y modelos de propagación (RAMMS, SAMOS-AT)

6. **🌾 Desconexión con Conocimiento Comunitario Local**
   - Indicadores biofísicos tradicionales: fenología, fauna, *puquiales*
   - Toponimia quechua/aymara y memoria territorial
   - Prácticas de gestión ancestral: *amunas*, *qochas*, rituales de pago a Apus
   - Monitoreo participativo y co-diseño de adaptación
   - Marco normativo: Convenio 169 OIT, Ley de Recursos Hídricos

### Recursos Bibliográficos

Cada tema incluye:
- **Referencias científicas revisadas por pares** (The Cryosphere, Nature Climate Change, Earth-Science Reviews)
- **Casos de estudio andinos** (glaciares Chacaltaya, Pastoruri, Quelccaya)
- **Recursos técnicos** (WGMS, GLIMS, INAIGEM, RGI)
- **Proyectos de adaptación colaborativa** (PACC Perú, PRAA)

La bibliografía completa está disponible en `data/REFERENCIAS_CONOCIMIENTO_GLACIAR.md`.

---

## 7. Consideraciones Metodologicas

- **Perspectiva y Cobertura**: Una fotografia individual captura el campo visual frontal; no sustituye la integracion espacial de sensores multiespectrales orbitales (Sentinel-2, Landsat).
- **Concentracion de Particulas**: La estimacion clasifica area expuesta, requiriendo calibracion espectrorradiometrica in situ para cuantificar concentraciones masicas en profundidad ($\mu\text{g/g}$).
- **Dinamica del Hielo**: La contraccion superficial proyecta el balance de area pero no resuelve las ecuaciones tridimensionales de flujo por deformacion viscosa (ley de Glen) ni la topografia del lecho subglaciar.
