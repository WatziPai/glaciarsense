"""
Nuevo Tab 5 sin matplotlib - solo con análisis numéricos y Plotly
"""

NEW_TAB5 = '''
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
    
    # Sección 1: Bioalbedo - VERSIÓN SIMPLIFICADA
    with st.expander("🦠 Detección de Bioalbedo (Algas y Crioconita)", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Estado", "✅ DETECTADO" if advanced_result.bioalbedo_detected else "❌ NO DETECTADO")
        with col2:
            st.metric("Cobertura", f"{advanced_result.bioalbedo_percentage:.2f}%")
        with col3:
            if advanced_result.bioalbedo_detected:
                st.metric("Impacto estimado", "+10-30% fusión")
        
        st.markdown("""
        **¿Qué es el bioalbedo?**  
        Presencia de microorganismos vivos (algas, cianobacterias) y material biológicamente 
        activo (crioconita) que oscurece la superficie del hielo.
        
        **Características detectadas:**
        - Algas de nieve: tonos verdes/rojos por clorofila y carotenoides
        - Crioconita: agregados oscuros de 1-5mm con textura granular
        - Impacto: reducción de albedo de 0.85 → 0.40-0.60
        """)
        
        if advanced_result.bioalbedo_detected:
            # Mostrar imágenes lado a lado
            col_img1, col_img2 = st.columns(2)
            with col_img1:
                st.image(img_rgb, caption="Imagen original", use_container_width=True)
            with col_img2:
                overlay = img_rgb.copy()
                overlay[advanced_result.bioalbedo_map] = [255, 0, 255]
                blended = cv2.addWeighted(img_rgb, 0.6, overlay, 0.4, 0)
                st.image(blended, caption="Zonas con bioalbedo (magenta)", use_container_width=True)
    
    st.markdown("---")
    
    # Sección 2: Grietas
    with st.expander("❄️ Detección de Grietas (Crevasses)"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Estado", "✅ DETECTADAS" if advanced_result.crevasses_detected else "❌ NO DETECTADAS")
        with col2:
            st.metric("Cantidad", f"{advanced_result.crevasse_count} grietas")
        
        st.markdown("""
        **Significado de las grietas:**
        - Tensión glaciar activa por velocidad diferencial
        - Cambios en pendiente del lecho
        - Adelgazamiento del hielo
        - Riesgo de fragmentación
        """)
        
        if advanced_result.crevasses_detected:
            col_img1, col_img2 = st.columns(2)
            with col_img1:
                st.image(img_rgb, caption="Imagen original", use_container_width=True)
            with col_img2:
                overlay = img_rgb.copy()
                overlay[advanced_result.crevasse_map] = [255, 255, 0]
                blended = cv2.addWeighted(img_rgb, 0.7, overlay, 0.3, 0)
                st.image(blended, caption="Grietas detectadas (amarillo)", use_container_width=True)
    
    st.markdown("---")
    
    # Sección 3: Rugosidad
    with st.expander("📊 Índice de Rugosidad Superficial"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Índice de rugosidad", f"{advanced_result.roughness_index:.2f} / 1.00")
        with col2:
            if advanced_result.roughness_index > 0.6:
                estado = "🔴 MUY RUGOSO (ablación avanzada)"
            elif advanced_result.roughness_index > 0.3:
                estado = "🟡 MODERADO (hielo envejecido)"
            else:
                estado = "🟢 LISO (nieve fresca)"
            st.metric("Estado", estado)
        
        st.markdown(f"""
        **Interpretación:**
        - 0.0 - 0.3: Superficie lisa (nieve fresca o hielo pulido)
        - 0.3 - 0.6: Rugosidad moderada (hielo envejecido)
        - 0.6 - 1.0: Muy rugoso (ablación avanzada, penitentes, crioconita)
        
        **Valor actual: {advanced_result.roughness_index:.2f}**
        
        La rugosidad superficial indica edad del hielo, intensidad de ablación y presencia 
        de estructuras de fusión.
        """)
        
        # Mostrar imagen original
        st.image(img_rgb, caption="Imagen original", use_container_width=True)
    
    st.markdown("---")
    
    # Sección 4: Índices Espectrales - SIMPLIFICADO CON PLOTLY
    with st.expander("🌈 Índices Espectrales (NDVI, NDWI, NDSI)"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("NDVI", f"{advanced_result.ndvi:.3f}")
        with col2:
            st.metric("NDWI", f"{advanced_result.ndwi:.3f}")
        with col3:
            st.metric("NDSI", f"{advanced_result.ndsi:.3f}")
        
        st.markdown("""
        **Índices calculados (aproximación desde RGB):**
        
        - **NDVI (Normalized Difference Vegetation Index):** Detecta vegetación (>0.3 = vegetación)
        - **NDWI (Normalized Difference Water Index):** Detecta agua superficial (>0.3 = agua)
        - **NDSI (Normalized Difference Snow Index):** Detecta nieve/hielo (>0.4 = nieve)
        
        ⚠️ **Nota:** Estos son aproximaciones desde RGB. Los valores reales requieren 
        imágenes multiespectrales (NIR, SWIR).
        """)
        
        # Gráfico de barras con Plotly
        import plotly.graph_objects as go
        fig = go.Figure(data=[
            go.Bar(
                x=['NDVI', 'NDWI', 'NDSI'],
                y=[advanced_result.ndvi, advanced_result.ndwi, advanced_result.ndsi],
                marker_color=['green' if v > 0 else 'red' for v in [advanced_result.ndvi, advanced_result.ndwi, advanced_result.ndsi]],
                text=[f"{v:.3f}" for v in [advanced_result.ndvi, advanced_result.ndwi, advanced_result.ndsi]],
                textposition='auto',
            )
        ])
        fig.update_layout(
            title="Índices Espectrales",
            yaxis_title="Valor del índice",
            yaxis_range=[-1, 1],
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Sección 5: Distribución Espacial
    with st.expander("🗺️ Distribución Espacial de Contaminantes"):
        st.metric("Clusters detectados", f"{advanced_result.contamination_clusters}")
        
        # Tabla de distribución
        dist_data = {
            "Cuadrante": ["Superior Izquierda", "Superior Derecha", "Inferior Izquierda", "Inferior Derecha"],
            "Contaminación (%)": [
                f"{advanced_result.spatial_distribution['superior_izq']:.1f}",
                f"{advanced_result.spatial_distribution['superior_der']:.1f}",
                f"{advanced_result.spatial_distribution['inferior_izq']:.1f}",
                f"{advanced_result.spatial_distribution['inferior_der']:.1f}"
            ]
        }
        st.table(dist_data)
        
        st.markdown("""
        **Análisis por cuadrantes:**
        - Identifica zonas de mayor deposición de contaminantes
        - Detecta patrones de transporte eólico
        - Señala áreas más afectadas por ablación
        """)
    
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
            "Clusters",
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
        "y procesamiento de imagen. Los resultados son estimaciones exploratorias."
    )
'''

print("Nuevo Tab5 creado")
