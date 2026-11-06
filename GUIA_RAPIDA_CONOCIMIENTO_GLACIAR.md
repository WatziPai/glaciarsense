# 🎓 Guía Rápida - Módulo de Conocimiento Glaciar

## Acceso Rápido

1. **Iniciar la aplicación:**
   ```bash
   streamlit run app.py
   ```
   O doble clic en `iniciar_app.bat` (Windows)

2. **Navegar al módulo:**
   - Ir a la pestaña **"Conocimiento Glaciar"** (última pestaña)

---

## 📖 Temas Disponibles

### 1. 🏔️ Cavidades Ocultas y Topografía Basal
**¿Por qué importa?**  
Los modelos 2D de retroceso asumen un lecho rocoso uniforme, pero las cubetas profundas pueden causar colapsos abruptos no predichos.

**Qué aprenderás:**
- Sobreexcavaciones glaciales (hasta 200m de profundidad)
- Formación de lagos proglaciares (riesgo GLOF)
- Técnicas: Radar de penetración (GPR), batimetría

**Aplicación práctica:**  
INAIGEM prioriza caracterización de lagos con alto riesgo GLOF.

---

### 2. ♻️ Puntos de No Retorno Irreversibles
**¿Por qué importa?**  
Incluso si el clima se estabiliza hoy, muchos glaciares seguirán retrocediendo por décadas debido a la inercia térmica acumulada.

**Qué aprenderás:**
- Tiempo de respuesta: 10-100 años
- Línea de Equilibrio (ELA) y balance negativo
- Retroalimentación albedo-temperatura (ciclo autosostenido)

**Caso real:**  
Glaciar Chacaltaya (Bolivia) desapareció en 2009 tras superar su punto de no retorno en los 90s.

---

### 3. 💧 Dinámica del Agua Subglacial
**¿Por qué importa?**  
El agua bajo el glaciar acelera el deslizamiento basal y erosiona el lecho rocoso, procesos invisibles desde la superficie.

**Qué aprenderás:**
- Canales de Röthlisberger vs película de Weertman
- Aceleración de flujo: 2-5x en verano
- Erosión: 1-10 mm/año de lecho rocoso
- Transporte de sedimentos → colmatación de embalses

**Riesgo infraestructura:**  
Hidroeléctricas andinas pierden 20-30% de vida útil por sedimentos.

---

### 4. 🦠 Bioalbedo y Ecosistemas Microbianos
**¿Por qué importa?**  
Algas y bacterias oscurecen el hielo, reduciendo el albedo de 0.85 a 0.40, acelerando la fusión hasta +30%.

**Qué aprenderás:**
- Algas de nieve: *Chlamydomonas nivalis*, *Sanguina nivaloides*
- Crioconita: agregados de polvo + materia orgánica + microorganismos
- Retroalimentación bioalbedo-clima
- Detección con índices espectrales (NDVI, NDWI)

**⚠️ Importante:**  
GlaciarSense actualmente NO detecta bioalbedo (solo partículas inertes). Próximas versiones lo incorporarán.

---

### 5. ❄️ Contribución de Avalanchas
**¿Por qué importa?**  
En glaciares de circo, las avalanchas aportan 30-50% de la masa anual, creando variaciones de espesor no capturadas por modelos continuos.

**Qué aprenderás:**
- Recarga episódica desde paredes >45°
- Variabilidad espacial del espesor (10-20m de diferencia)
- Glaciares pulsantes (*surging glaciers*)
- Monitoreo con InSAR

**Dato técnico:**  
Modelos de propagación: RAMMS, SAMOS-AT

---

### 6. 🌾 Conocimiento Comunitario Local
**¿Por qué importa?**  
Los saberes tradicionales complementan datos satelitales con observaciones generacionales sobre patrones de deshielo.

**Qué aprenderás:**
- Indicadores biofísicos: fenología, fauna, *puquiales*
- Toponimia quechua/aymara (memoria territorial)
- Prácticas ancestrales: *amunas*, *qochas*, rituales
- Monitoreo participativo y co-diseño
- Marco legal: Convenio 169 OIT, Ley 29338

**Proyecto destacado:**  
PACC Perú capacita a líderes comunitarios en interpretación de pronósticos.

---

## 🔍 Cómo Navegar el Módulo

### Estructura Visual
```
Conocimiento Glaciar
│
├─ 🏔️ Cavidades Ocultas          [Expandir →]
│   ├─ Texto explicativo
│   ├─ 💡 Aplicación práctica
│   └─ ⚠️ Limitación del modelo
│
├─ ♻️ Puntos de No Retorno        [Expandir →]
│   ├─ Texto explicativo
│   └─ 🔬 Caso de estudio
│
├─ 💧 Agua Subglacial             [Expandir →]
│   ├─ Texto explicativo
│   ├─ 🌊 Monitoreo en tiempo real
│   └─ ⚠️ Riesgo infraestructura
│
├─ 🦠 Bioalbedo                   [Expandir →]
│   ├─ Texto explicativo
│   ├─ 🔬 Innovación metodológica
│   └─ ⚠️ Advertencia científica (NO implementado)
│
├─ ❄️ Avalanchas                 [Expandir →]
│   ├─ Texto explicativo
│   ├─ 📊 Datos de campo
│   └─ 🔍 Para modeladores
│
└─ 🌾 Conocimiento Comunitario    [Expandir →]
    ├─ Texto explicativo
    ├─ 🤝 Iniciativa destacada
    └─ 📢 Llamado a la acción
```

### Consejos de Navegación
1. **Haz clic en cada tema** para expandir y leer el contenido
2. **Lee los cuadros de colores:**
   - 🔵 Azul (Info): Aplicaciones prácticas
   - 🟢 Verde (Success): Casos de éxito
   - 🟡 Amarillo (Warning): Limitaciones
   - 🔴 Rojo (Error): Advertencias importantes
3. **Consulta las referencias** en `data/REFERENCIAS_CONOCIMIENTO_GLACIAR.md`

---

## 📚 Recursos Adicionales

### Archivo de Referencias
```
📂 data/REFERENCIAS_CONOCIMIENTO_GLACIAR.md
```
Contiene:
- +40 referencias científicas con DOIs
- Enlaces a bases de datos globales (WGMS, RGI, GLIMS)
- Contactos de observatorios andinos
- Proyectos de adaptación colaborativa

### Diagramas Educativos
```bash
# Generar diagramas (requiere matplotlib)
python scripts/generar_diagramas_educativos.py
```
Genera 4 diagramas:
1. Perfil glaciar con sobreexcavación
2. Retroalimentación albedo-temperatura
3. Sistema hidrológico subglacial
4. Comparación bioalbedo

---

## 🎯 Casos de Uso

### Para Estudiantes
**Objetivo:** Comprender procesos complejos más allá de la teoría básica

**Flujo de trabajo:**
1. Procesar una imagen en Tab 1
2. Ver proyección espacial en Tab 2
3. Explorar Conocimiento Glaciar (Tab 5) para entender **por qué** los modelos tienen limitaciones
4. Citar referencias en trabajos académicos

---

### Para Investigadores
**Objetivo:** Contextualizar resultados cuantitativos en marco científico amplio

**Flujo de trabajo:**
1. Usar GlaciarSense para análisis inicial
2. Identificar procesos no capturados (bioalbedo, topografía basal, etc.)
3. Consultar referencias específicas para profundizar
4. Diseñar estudios complementarios (GPR, InSAR, muestreo microbiológico)

---

### Para Gestores de Políticas
**Objetivo:** Tomar decisiones informadas sobre adaptación climática

**Flujo de trabajo:**
1. Revisar datos regionales (Tab 4)
2. Entender incertidumbres (Tab 3)
3. Leer sección de Conocimiento Comunitario (Tab 5)
4. Diseñar estrategias que integren ciencia occidental y saberes locales

---

### Para Comunidades Locales
**Objetivo:** Validar observaciones tradicionales con ciencia moderna

**Flujo de trabajo:**
1. Compartir fotografías del glaciar local
2. Comparar resultados con observaciones de *puquiales* y fenología
3. Leer sección de Conocimiento Comunitario
4. Participar en monitoreo colaborativo (contactar PACC/INAIGEM)

---

## ❓ Preguntas Frecuentes

### ¿El módulo modifica los cálculos de GlaciarSense?
**No.** Es puramente educativo. Los cálculos de albedo y proyección siguen siendo los mismos.

### ¿Por qué dice que el bioalbedo NO está implementado?
Porque la clasificación actual solo distingue partículas inertes (carbono negro, polvo), no microorganismos vivos. Futuras versiones usarán índices espectrales (NDVI/NDWI) para detectarlos.

### ¿Puedo citar estas referencias en mi tesis?
**Sí.** Todas las referencias son publicaciones científicas revisadas por pares con DOI verificable.

### ¿Cómo contribuir con nuevos temas?
1. Fork el repositorio en GitHub
2. Editar `app.py` → sección `with tab5:`
3. Agregar referencias en `data/REFERENCIAS_CONOCIMIENTO_GLACIAR.md`
4. Enviar Pull Request

### ¿Está disponible en inglés?
Actualmente solo en español. Traducciones bienvenidas (ver GitHub).

---

## 🚀 Próximos Pasos

### Corto Plazo
- [ ] Generar diagramas con `python scripts/generar_diagramas_educativos.py`
- [ ] Explorar cada tema y leer las referencias
- [ ] Compartir con colegas/estudiantes

### Mediano Plazo
- [ ] Implementar detección de bioalbedo con NDVI
- [ ] Integrar datos de monitoreo comunitario
- [ ] Traducir a inglés y quechua

### Largo Plazo
- [ ] Módulo 3D de topografía basal
- [ ] Simulador interactivo de retroalimentación climática
- [ ] Plataforma de ciencia ciudadana

---

## 📞 Contacto y Soporte

**Documentación completa:**  
- `README.md` - Descripción general del proyecto
- `CHANGELOG.md` - Historial de versiones
- `IMPLEMENTACION_COMPLETA.md` - Detalles técnicos de esta versión

**Reportar errores:**  
GitHub Issues (si el proyecto está en GitHub)

**Contribuir:**  
Pull Requests bienvenidas

---

**¡Explora, aprende y contextualiza la ciencia glaciar! 🏔️❄️🌍**

---

*Versión 2.2 - Octubre 2026*  
*GlaciarSense Development Team*
