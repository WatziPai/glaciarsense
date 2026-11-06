"""Script temporal para reemplazar tab5 con análisis avanzado funcional."""

# Leer el archivo original
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar dónde empieza tab5
tab5_start = next(i for i, line in enumerate(lines) if '# TAB 5' in line and 'Análisis' in line)

# Mantener todo hasta tab5
new_content = ''.join(lines[:tab5_start])

# Agregar el nuevo tab5
new_tab5 = """# TAB 5 -- Análisis Avanzado
# ============================================================================
with tab5:
    st.subheader("🔬 Análisis Avanzado de Características Glaciares")
    st.caption(
        "Detección de bioalbedo, grietas, rugosidad superficial, índices espectrales y distribución espacial de contaminantes."
    )

    # Verificar si hay una detección disponible
    if "detection" not in st.session_state or st.session_state["detection"] is None:
        st.warning("⚠️ Primero procesa una imagen en la pestaña 'Clasificación de imagen' para habilitar el análisis avanzado.")
        st.info("💡 El análisis avanzado incluye:\\n- Detección de bioalbedo (algas y crioconita)\\n- Identificación de grietas\\n- Índices de rugosidad superficial\\n- Índices espectrales (NDVI, NDWI, NDSI)\\n- Distribución espacial de contaminantes\\n- Estimación relativa de espesor")
        st.stop()

    # Obtener detección actual
    det = st.session_state["detection"]
    
    # Obtener imagen original
    samples = cached_samples()
    if "uploaded_image" in st.session_state and st.session_state["uploaded_image"] is not None:
        img_rgb = st.session_state["uploaded_image"]
    else:
        # Usar muestra por defecto
        img_rgb = samples.get("2. Polvo moderado", list(samples.values())[0])

    st.markdown("---")
    
    # Ejecutar análisis avanzado
    with st.spinner("🔍 Analizando características avanzadas..."):
        advanced_result = advanced_analysis.perform_advanced_analysis(
            img_rgb, det.masks, det.percentages
        )
    
    # Mostrar confianza
    st.metric("🎯 Confianza del análisis", f"{advanced_result.confidence * 100:.0f}%")
    
    # Mostrar advertencias críticas
    if advanced_result.warnings:
        st.markdown("### ⚠️ Hallazgos Críticos")
        for warning in advanced_result.warnings:
            st.warning(warning)
    
    st.markdown("---")
    
    # Sección 1: Bioalbedo
    with st.expander("🦠 Detección de Bioalbedo (Algas y Crioconita)", expanded=True):
        st.markdown(
            f\"\"\"
            ### Resultado del Análisis
            
            **Estado:** {'✅ DETECTADO' if advanced_result.bioalbedo_detected else '❌ NO DETECTADO'}  
            **Cobertura:** {advanced_result.bioalbedo_percentage:.2f}% del área glaciar
            
            El bioalbedo se refiere a la presencia de microorganismos vivos (algas, cianobacterias) 
            y material biológicamente activo (crioconita) que oscurece la superficie del hielo.
            
            #### Características detectadas:
            - **Algas de nieve:** Tonos verdes/rojos por clorofila y carotenoides
            - **Crioconita:** Agregados oscuros de 1-5mm con textura granular
            - **Impacto:** Reducción de albedo de 0.85 → 0.40-0.60 (+10-30% de fusión)
            \"\"\"
        )
        
        if advanced_result.bioalbedo_detected:
            col1, col2 = st.columns(2)
            with col1:
                st.image(img_rgb, caption="Imagen original", use_container_width=True)
            with col2:
                # Crear overlay de bioalbedo
                overlay = img_rgb.copy()
                overlay[advanced_result.bioalbedo_map] = [255, 0, 255]  # Magenta
                blended = cv2.addWeighted(img_rgb, 0.6, overlay, 0.4, 0)
                st.image(blended, caption="Zonas con bioalbedo (magenta)", use_container_width=True)
            
            st.error(
                f"⚠️ **Impacto estimado:** La presencia de bioalbedo ({advanced_result.bioalbedo_percentage:.1f}%) "
                "puede acelerar la fusión entre 10-30% adicional. Este efecto NO está incluido en el cálculo "
                "estándar de albedo."
            )
        else:
            st.success("✅ No se detectó bioalbedo significativo en esta imagen.")
    
    st.markdown("---")
    
    # Sección 2: Grietas
    with st.expander("❄️ Detección de Grietas (Crevasses)"):
        st.markdown(
            f\"\"\"
            ### Resultado del Análisis
            
            **Estado:** {'✅ DETECTADAS' if advanced_result.crevasses_detected else '❌ NO DETECTADAS'}  
            **Cantidad:** {advanced_result.crevasse_count} grietas identificadas
            
            Las grietas indican tensión glaciar activa causada por:
            - Velocidad diferencial de flujo
            - Cambios en la pendiente del lecho
            - Adelgazamiento del hielo
            
            #### Implicaciones:
            - Fragmentación potencial del glaciar
            - Aceleración de la fusión (agua superficial penetra al lecho)
            - Riesgo de desprendimientos en zonas empinadas
            \"\"\"
        )
        
        if advanced_result.crevasses_detected:
            col1, col2 = st.columns(2)
            with col1:
                st.image(img_rgb, caption="Imagen original", use_container_width=True)
            with col2:
                # Crear overlay de grietas
                overlay = img_rgb.copy()
                overlay[advanced_result.crevasse_map] = [255, 255, 0]  # Amarillo
                blended = cv2.addWeighted(img_rgb, 0.7, overlay, 0.3, 0)
                st.image(blended, caption="Grietas detectadas (amarillo)", use_container_width=True)
            
            st.warning(
                f"⚠️ **Atención:** Se detectaron {advanced_result.crevasse_count} grietas. "
                "Esto indica un glaciar dinámicamente activo o en proceso de fragmentación."
            )
    
    st.markdown("---")
    
    # Sección 3: Rugosidad
    with st.expander("📊 Índice de Rugosidad Superficial"):
        st.markdown(
            f\"\"\"
            ### Resultado del Análisis
            
            **Índice de rugosidad:** {advanced_result.roughness_index:.2f} / 1.00
            
            - **0.0 - 0.3:** Superficie lisa (nieve fresca o hielo pulido)
            - **0.3 - 0.6:** Rugosidad moderada (hielo envejecido)
            - **0.6 - 1.0:** Muy rugoso (ablación avanzada, penitentes, crioconita)
            
            La rugosidad superficial es un indicador de:
            - Edad y condición del hielo
            - Intensidad de la ablación
            - Presencia de estructuras de fusión (penitentes, canales)
            \"\"\"
        )
        
        # Mostrar mapa de rugosidad
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        ax1.imshow(img_rgb)
        ax1.set_title("Imagen Original")
        ax1.axis('off')
        
        im = ax2.imshow(advanced_result.roughness_map, cmap='hot')
        ax2.set_title(f"Mapa de Rugosidad (índice: {advanced_result.roughness_index:.2f})")
        ax2.axis('off')
        plt.colorbar(im, ax=ax2, label="Rugosidad [0-1]")
        
        st.pyplot(fig)
        plt.close()
        
        if advanced_result.roughness_index > 0.6:
            st.warning(
                "⚠️ **Superficie muy rugosa:** Indica ablación avanzada y envejecimiento del hielo. "
                "La fusión es probablemente muy activa en esta zona."
            )
        elif advanced_result.roughness_index > 0.3:
            st.info(
                "ℹ️ **Rugosidad moderada:** Superficie típica de hielo glaciar expuesto durante una temporada."
            )
        else:
            st.success(
                "✅ **Superficie lisa:** Posiblemente nieve fresca o hielo poco expuesto a la ablación."
            )
    
    st.markdown("---")
    
    # Sección 4: Índices Espectrales
    with st.expander("🌈 Índices Espectrales (NDVI, NDWI, NDSI)"):
        st.markdown(
            f\"\"\"
            ### Índices Calculados (aproximación desde RGB)
            
            **NDVI (Normalized Difference Vegetation Index):** {advanced_result.ndvi:.3f}
            - Rango: -1 a +1
            - Valores > 0.3 indican vegetación
            - En glaciares: debe ser < 0.2
            
            **NDWI (Normalized Difference Water Index):** {advanced_result.ndwi:.3f}
            - Rango: -1 a +1
            - Valores > 0.3 indican agua superficial
            - Útil para detectar lagos supraglaciares
            
            **NDSI (Normalized Difference Snow Index):** {advanced_result.ndsi:.3f}
            - Rango: -1 a +1
            - Valores > 0.4 indican nieve/hielo
            - Útil para discriminar nieve de roca
            
            ⚠️ **Nota:** Estos índices son aproximaciones desde RGB. Los valores reales 
            requieren imágenes multiespectrales (NIR, SWIR).
            \"\"\"
        )
        
        # Gráfico de barras
        fig, ax = plt.subplots(figsize=(10, 4))
        indices = ['NDVI', 'NDWI', 'NDSI']
        values = [advanced_result.ndvi, advanced_result.ndwi, advanced_result.ndsi]
        colors = ['green' if v > 0 else 'red' for v in values]
        
        ax.bar(indices, values, color=colors, alpha=0.7, edgecolor='black')
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.set_ylim(-1, 1)
        ax.set_ylabel("Valor del índice")
        ax.set_title("Índices Espectrales Aproximados")
        ax.grid(axis='y', alpha=0.3)
        
        st.pyplot(fig)
        plt.close()
        
        # Interpretación
        if advanced_result.ndvi > 0.2:
            st.warning("⚠️ **NDVI elevado:** Posible presencia de vegetación o algas. Verificar bioalbedo.")
        if advanced_result.ndsi < 0.3:
            st.error("⚠️ **NDSI bajo:** La imagen podría no ser de un glaciar puro, o está muy contaminada.")
    
    st.markdown("---")
    
    # Sección 5: Distribución Espacial
    with st.expander("🗺️ Distribución Espacial de Contaminantes"):
        st.markdown(
            f\"\"\"
            ### Análisis por Cuadrantes
            
            **Clusters de contaminación detectados:** {advanced_result.contamination_clusters}
            
            La distribución espacial ayuda a identificar:
            - Zonas de mayor deposición de contaminantes
            - Patrones de transporte eólico
            - Áreas más afectadas por ablación
            \"\"\"
        )
        
        # Tabla de distribución
        dist_data = {
            "Cuadrante": ["Superior Izquierda", "Superior Derecha", 
                         "Inferior Izquierda", "Inferior Derecha"],
            "Contaminación (%)": [
                f"{advanced_result.spatial_distribution['superior_izq']:.1f}",
                f"{advanced_result.spatial_distribution['superior_der']:.1f}",
                f"{advanced_result.spatial_distribution['inferior_izq']:.1f}",
                f"{advanced_result.spatial_distribution['inferior_der']:.1f}"
            ]
        }
        
        st.table(dist_data)
        
        # Visualización de cuadrantes
        fig, ax = plt.subplots(figsize=(8, 8))
        h, w = img_rgb.shape[:2]
        
        # Mostrar imagen
        ax.imshow(img_rgb)
        
        # Dibujar líneas de cuadrantes
        ax.axhline(h//2, color='yellow', linewidth=2, linestyle='--')
        ax.axvline(w//2, color='yellow', linewidth=2, linestyle='--')
        
        # Anotar porcentajes
        positions = [
            (w*0.25, h*0.25, 'superior_izq'),
            (w*0.75, h*0.25, 'superior_der'),
            (w*0.25, h*0.75, 'inferior_izq'),
            (w*0.75, h*0.75, 'inferior_der')
        ]
        
        for x, y, key in positions:
            value = advanced_result.spatial_distribution[key]
            ax.text(x, y, f"{value:.1f}%", 
                   fontsize=16, weight='bold', color='yellow',
                   ha='center', va='center',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
        ax.set_title("Distribución de Contaminantes por Cuadrante")
        ax.axis('off')
        
        st.pyplot(fig)
        plt.close()
    
    st.markdown("---")
    
    # Sección 6: Espesor Relativo
    with st.expander("📏 Estimación Relativa de Espesor"):
        st.markdown(
            \"\"\"
            ### Mapa de Espesor Relativo
            
            Esta es una estimación **cualitativa** basada en luminancia y sombreado.
            
            **Asunciones:**
            - Hielo más grueso tiende a ser más brillante (menos impurezas)
            - Zonas sombreadas pueden indicar depresiones
            - NO es una medición cuantitativa real
            
            Para mediciones reales de espesor, se requiere:
            - Radar de penetración glaciar (GPR)
            - Sondeos sísmicos
            - Modelos de flujo calibrados con velocidad superficial
            \"\"\"
        )
        
        # Mostrar mapa de espesor
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        ax1.imshow(img_rgb)
        ax1.set_title("Imagen Original")
        ax1.axis('off')
        
        im = ax2.imshow(advanced_result.estimated_thickness_map, cmap='viridis')
        ax2.set_title("Espesor Relativo Estimado")
        ax2.axis('off')
        plt.colorbar(im, ax=ax2, label="Espesor relativo [0-1]")
        
        st.pyplot(fig)
        plt.close()
        
        st.info(
            "ℹ️ **Interpretación:** Zonas más oscuras (azul) indican menor espesor relativo, "
            "mientras que zonas más claras (amarillo) sugieren mayor espesor. Esto es solo una aproximación visual."
        )
    
    st.markdown("---")
    
    # Resumen final
    st.markdown("### 📋 Resumen del Análisis Avanzado")
    
    summary_data = {
        "Parámetro": [
            "Bioalbedo",
            "Grietas",
            "Rugosidad",
            "NDVI",
            "NDWI",
            "NDSI",
            "Clusters de contaminación",
            "Confianza"
        ],
        "Valor": [
            f"{'SÍ' if advanced_result.bioalbedo_detected else 'NO'} ({advanced_result.bioalbedo_percentage:.1f}%)",
            f"{advanced_result.crevasse_count}",
            f"{advanced_result.roughness_index:.2f}",
            f"{advanced_result.ndvi:.3f}",
            f"{advanced_result.ndwi:.3f}",
            f"{advanced_result.ndsi:.3f}",
            f"{advanced_result.contamination_clusters}",
            f"{advanced_result.confidence * 100:.0f}%"
        ]
    }
    
    st.table(summary_data)
    
    st.success(
        "✅ **Análisis completado.** Los resultados proporcionan información complementaria "
        "al análisis básico de albedo y cobertura."
    )
    
    st.caption(
        "**Nota metodológica:** El análisis avanzado usa técnicas de visión por computadora "
        "y procesamiento de imagen. Los resultados son estimaciones exploratorias y deben "
        "complementarse con mediciones de campo cuando sea posible."
    )
"""

new_content += new_tab5

# Escribir el archivo nuevo
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Tab5 reemplazado exitosamente")
