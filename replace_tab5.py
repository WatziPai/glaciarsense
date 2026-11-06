"""Script para reemplazar Tab 5 con versión sin matplotlib."""

# Leer archivo original
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar inicio de tab5
tab5_start = next(i for i, l in enumerate(lines) if 'with tab5:' in l)

# Mantener todo hasta tab5
new_lines = lines[:tab5_start]

# Agregar nuevo tab5 simplificado
new_tab5 = '''with tab5:
    st.subheader("🔬 Análisis Avanzado de Características Glaciares")
    st.caption("Detección de bioalbedo, grietas, rugosidad superficial, índices espectrales y distribución espacial de contaminantes.")

    if "detection" not in st.session_state or st.session_state["detection"] is None:
        st.warning("⚠️ Primero procesa una imagen en la pestaña 'Clasificación de imagen' para habilitar el análisis avanzado.")
        st.info("💡 El análisis avanzado incluye:\\n- Detección de bioalbedo\\n- Grietas\\n- Rugosidad\\n- Índices espectrales\\n- Distribución espacial")
        st.stop()

    det = st.session_state["detection"]
    samples = cached_samples()
    img_rgb = st.session_state.get("uploaded_image") or samples.get("2. Polvo moderado", list(samples.values())[0])

    st.markdown("---")
    
    with st.spinner("🔍 Analizando características avanzadas..."):
        advanced_result = advanced_analysis.perform_advanced_analysis(img_rgb, det.masks, det.percentages)
    
    st.metric("🎯 Confianza", f"{advanced_result.confidence * 100:.0f}%")
    
    if advanced_result.warnings:
        for warning in advanced_result.warnings:
            st.warning(warning)
    
    st.markdown("---")
    
    with st.expander("🦠 Bioalbedo (Algas y Crioconita)", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Estado", "✅ SÍ" if advanced_result.bioalbedo_detected else "❌ NO")
        col2.metric("Cobertura", f"{advanced_result.bioalbedo_percentage:.2f}%")
        if advanced_result.bioalbedo_detected:
            col3.metric("Impacto", "+10-30% fusión")
        
        if advanced_result.bioalbedo_detected:
            c1, c2 = st.columns(2)
            c1.image(img_rgb, "Original", use_container_width=True)
            overlay = img_rgb.copy()
            overlay[advanced_result.bioalbedo_map] = [255, 0, 255]
            c2.image(cv2.addWeighted(img_rgb, 0.6, overlay, 0.4, 0), "Bioalbedo (magenta)", use_container_width=True)
    
    with st.expander("❄️ Grietas"):
        col1, col2 = st.columns(2)
        col1.metric("Estado", "✅ SÍ" if advanced_result.crevasses_detected else "❌ NO")
        col2.metric("Cantidad", advanced_result.crevasse_count)
        
        if advanced_result.crevasses_detected:
            c1, c2 = st.columns(2)
            c1.image(img_rgb, "Original", use_container_width=True)
            overlay = img_rgb.copy()
            overlay[advanced_result.crevasse_map] = [255, 255, 0]
            c2.image(cv2.addWeighted(img_rgb, 0.7, overlay, 0.3, 0), "Grietas (amarillo)", use_container_width=True)
    
    with st.expander("📊 Rugosidad"):
        col1, col2 = st.columns(2)
        col1.metric("Índice", f"{advanced_result.roughness_index:.2f}")
        estado = "🔴 MUY RUGOSO" if advanced_result.roughness_index > 0.6 else "🟡 MODERADO" if advanced_result.roughness_index > 0.3 else "🟢 LISO"
        col2.metric("Estado", estado)
        st.image(img_rgb, use_container_width=True)
    
    with st.expander("🌈 Índices Espectrales"):
        col1, col2, col3 = st.columns(3)
        col1.metric("NDVI", f"{advanced_result.ndvi:.3f}")
        col2.metric("NDWI", f"{advanced_result.ndwi:.3f}")
        col3.metric("NDSI", f"{advanced_result.ndsi:.3f}")
        
        fig = go.Figure(data=[go.Bar(
            x=['NDVI', 'NDWI', 'NDSI'],
            y=[advanced_result.ndvi, advanced_result.ndwi, advanced_result.ndsi],
            marker_color=['green' if v>0 else 'red' for v in [advanced_result.ndvi, advanced_result.ndwi, advanced_result.ndsi]]
        )])
        fig.update_layout(title="Índices Espectrales", yaxis_range=[-1, 1], height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("🗺️ Distribución Espacial"):
        st.metric("Clusters", advanced_result.contamination_clusters)
        st.table({
            "Cuadrante": ["Sup. Izq.", "Sup. Der.", "Inf. Izq.", "Inf. Der."],
            "Contaminación (%)": [
                f"{advanced_result.spatial_distribution['superior_izq']:.1f}",
                f"{advanced_result.spatial_distribution['superior_der']:.1f}",
                f"{advanced_result.spatial_distribution['inferior_izq']:.1f}",
                f"{advanced_result.spatial_distribution['inferior_der']:.1f}"
            ]
        })
    
    st.markdown("### 📋 Resumen")
    st.table({
        "Parámetro": ["Bioalbedo", "Grietas", "Rugosidad", "NDVI", "NDWI", "NDSI", "Clusters", "Confianza"],
        "Valor": [
            f"{'SÍ' if advanced_result.bioalbedo_detected else 'NO'} ({advanced_result.bioalbedo_percentage:.1f}%)",
            str(advanced_result.crevasse_count),
            f"{advanced_result.roughness_index:.2f}",
            f"{advanced_result.ndvi:.3f}",
            f"{advanced_result.ndwi:.3f}",
            f"{advanced_result.ndsi:.3f}",
            str(advanced_result.contamination_clusters),
            f"{advanced_result.confidence * 100:.0f}%"
        ]
    })
    
    st.success("✅ Análisis completado.")
'''

new_lines.append(new_tab5)

# Escribir archivo nuevo
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Tab5 reemplazado exitosamente (SIN matplotlib)")
print(f"Líneas eliminadas: {len(lines) - len(new_lines)}")
print(f"Nuevo total: {len(new_lines)} líneas")
