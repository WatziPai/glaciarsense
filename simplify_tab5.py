"""Simplificar Tab 5 - Solo datos, sin texto teórico."""

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar inicio de tab5
tab5_start = next(i for i, l in enumerate(lines) if 'with tab5:' in l)

# Mantener todo hasta tab5
new_lines = lines[:tab5_start]

# Nuevo tab5 ULTRA DIRECTO - Solo datos
new_tab5 = '''with tab5:
    st.subheader("🔬 Análisis Avanzado")

    if "detection" not in st.session_state or st.session_state["detection"] is None:
        st.warning("⚠️ Procesa una imagen en la Tab 1 primero")
        st.stop()

    det = st.session_state["detection"]
    samples = cached_samples()
    
    if "uploaded_image" in st.session_state and st.session_state["uploaded_image"] is not None:
        img_rgb = st.session_state["uploaded_image"]
    else:
        img_rgb = samples.get("2. Polvo moderado", list(samples.values())[0])
    
    with st.spinner("🔍 Analizando..."):
        result = advanced_analysis.perform_advanced_analysis(img_rgb, det.masks, det.percentages)
    
    # RESULTADOS DIRECTOS - Sin expanders
    st.markdown("### 📊 Resultados del Análisis")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Confianza", f"{result.confidence * 100:.0f}%")
    col2.metric("Bioalbedo", f"{result.bioalbedo_percentage:.1f}%")
    col3.metric("Grietas", result.crevasse_count)
    col4.metric("Rugosidad", f"{result.roughness_index:.2f}")
    
    # Advertencias (solo si hay)
    if result.warnings:
        for w in result.warnings:
            st.warning(w)
    
    st.markdown("---")
    
    # VISUALIZACIONES DIRECTAS
    if result.bioalbedo_detected or result.crevasses_detected:
        st.markdown("### 🗺️ Mapas de Detección")
        cols = st.columns(2 if result.bioalbedo_detected and result.crevasses_detected else 1)
        
        if result.bioalbedo_detected:
            with cols[0] if len(cols) > 1 else cols[0]:
                overlay = img_rgb.copy()
                overlay[result.bioalbedo_map] = [255, 0, 255]
                st.image(cv2.addWeighted(img_rgb, 0.6, overlay, 0.4, 0), 
                        "Bioalbedo detectado (magenta)", use_container_width=True)
        
        if result.crevasses_detected:
            with cols[1] if len(cols) > 1 else cols[0]:
                overlay = img_rgb.copy()
                overlay[result.crevasse_map] = [255, 255, 0]
                st.image(cv2.addWeighted(img_rgb, 0.7, overlay, 0.3, 0),
                        "Grietas detectadas (amarillo)", use_container_width=True)
        
        st.markdown("---")
    
    # ÍNDICES ESPECTRALES
    st.markdown("### 🌈 Índices Espectrales")
    col1, col2, col3 = st.columns(3)
    col1.metric("NDVI", f"{result.ndvi:.3f}")
    col2.metric("NDWI", f"{result.ndwi:.3f}")
    col3.metric("NDSI", f"{result.ndsi:.3f}")
    
    fig = go.Figure(data=[go.Bar(
        x=['NDVI', 'NDWI', 'NDSI'],
        y=[result.ndvi, result.ndwi, result.ndsi],
        marker_color=['green' if v>0 else 'red' for v in [result.ndvi, result.ndwi, result.ndsi]],
        text=[f"{v:.3f}" for v in [result.ndvi, result.ndwi, result.ndsi]],
        textposition='auto'
    )])
    fig.update_layout(yaxis_range=[-1, 1], height=350, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # DISTRIBUCIÓN ESPACIAL
    st.markdown("### 🗺️ Distribución de Contaminantes")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Clusters detectados", result.contamination_clusters)
    with col2:
        st.table({
            "Zona": ["Superior Izq.", "Superior Der.", "Inferior Izq.", "Inferior Der."],
            "Contaminación": [
                f"{result.spatial_distribution['superior_izq']:.1f}%",
                f"{result.spatial_distribution['superior_der']:.1f}%",
                f"{result.spatial_distribution['inferior_izq']:.1f}%",
                f"{result.spatial_distribution['inferior_der']:.1f}%"
            ]
        })
    
    st.markdown("---")
    
    # TABLA RESUMEN FINAL
    st.markdown("### 📋 Resumen Completo")
    st.table({
        "Parámetro": ["Bioalbedo", "Grietas", "Rugosidad", "NDVI", "NDWI", "NDSI", "Clusters", "Confianza"],
        "Valor Calculado": [
            f"{'✅ Detectado' if result.bioalbedo_detected else '❌ No detectado'} ({result.bioalbedo_percentage:.1f}%)",
            f"{result.crevasse_count} grietas",
            f"{result.roughness_index:.2f} ({'Rugoso' if result.roughness_index > 0.6 else 'Moderado' if result.roughness_index > 0.3 else 'Liso'})",
            f"{result.ndvi:.3f}",
            f"{result.ndwi:.3f}",
            f"{result.ndsi:.3f}",
            f"{result.contamination_clusters}",
            f"{result.confidence * 100:.0f}%"
        ]
    })
'''

new_lines.append(new_tab5)

# Escribir
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Tab 5 simplificado - Solo datos y visualizaciones, SIN texto teórico")
