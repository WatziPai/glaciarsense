# Changelog - GlaciarSense

Todas las actualizaciones notables del proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere al [Versionado Semántico](https://semver.org/lang/es/).

---

## [2.2.0] - 2026-10-30

### Añadido

#### Nueva Pestaña: "Conocimiento Glaciar" 🎓
- **Módulo educativo avanzado** con 6 temas científicos fundamentales:
  1. **Cavidades Ocultas y Topografía Basal** - Sobreexcavaciones, riesgo GLOF y limitaciones de modelos 2D
  2. **Puntos de No Retorno Irreversibles** - Inercia térmica, ELA y retroalimentación climática
  3. **Dinámica del Agua Subglacial** - Canales de Röthlisberger, lubricación basal y erosión
  4. **Bioalbedo y Ecosistemas Microbianos** - Algas de nieve, crioconita y aceleración de fusión
  5. **Contribución de Avalanchas** - Recarga episódica y variabilidad espacial del espesor
  6. **Conocimiento Comunitario Local** - Saberes tradicionales, monitoreo participativo y co-diseño

#### Documentación Científica
- **Archivo `REFERENCIAS_CONOCIMIENTO_GLACIAR.md`**: Bibliografía completa con +40 referencias científicas revisadas por pares
  - Revistas: The Cryosphere, Nature Climate Change, Earth-Science Reviews
  - Casos de estudio andinos: Chacaltaya, Pastoruri, Quelccaya, Artesonraju
  - Recursos técnicos: WGMS, GLIMS, INAIGEM, RGI, IANIGLA
  - Proyectos de adaptación: PACC Perú, PRAA

#### Herramientas de Visualización
- **Script `generar_diagramas_educativos.py`**: Generador automatizado de 4 diagramas científicos:
  1. Perfil glaciar con sobreexcavación basal
  2. Diagrama de flujo: retroalimentación albedo-temperatura
  3. Esquema del sistema hidrológico subglacial
  4. Comparación visual: nieve limpia vs. bioalbedo

#### Mejoras en Interfaz
- Íconos temáticos en cada sección (🏔️ 💧 🦠 ❄️ 🌾)
- Cuadros informativos con ejemplos prácticos y advertencias metodológicas
- Estructura de expanders para navegación intuitiva
- Notas de pie con licencia y fuentes de datos

### Modificado
- **README.md**: Actualizada sección de estructura del proyecto y características
- **app.py**: Versión actualizada a v2.2
- Mejora en la organización del directorio `data/` con documentación científica

### Contexto Científico
Este lanzamiento responde a la necesidad de contextualizar las herramientas cuantitativas de análisis glaciar dentro de un marco científico más amplio que incluya:
- Procesos físicos no capturados por modelos de contorno superficial
- Factores biológicos emergentes (bioalbedo) documentados recientemente
- Integración de conocimientos tradicionales con ciencia occidental
- Transparencia sobre limitaciones metodológicas

### Para Usuarios
La nueva pestaña **NO modifica** los cálculos ni proyecciones existentes. Es un recurso educativo complementario que permite a investigadores, estudiantes y tomadores de decisión comprender el contexto completo de la dinámica glaciar.

---

## [2.1.0] - 2026-10-15 (versión previa)

### Características Base
- Clasificación de coberturas superficiales (hielo limpio, carbono negro, polvo, agua de deshielo)
- Estimación de albedo efectivo y aceleración térmica
- Proyección espacial con mapas interactivos (Folium)
- Análisis de sensibilidad con simulación Monte Carlo
- Escenarios climáticos SSP (IPCC AR6)
- Comparación multi-imagen (2-5 fotos)
- Exportación de reportes técnicos (PDF)
- Datos regionales WGMS/RGI

---

## Versionado

**[MAJOR.MINOR.PATCH]**

- **MAJOR**: Cambios incompatibles en la API o arquitectura fundamental
- **MINOR**: Nueva funcionalidad compatible con versiones anteriores
- **PATCH**: Correcciones de bugs y mejoras menores

---

**Última actualización:** 2026-10-30  
**Desarrollado por:** Equipo GlaciarSense  
**Licencia:** MIT (código) | CC BY 4.0 (documentación)
