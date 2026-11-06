"""
app.py
======
GlaciarSense -- Fotoclasificacion de coberturas superficiales en glaciares,
estimación de albedo efectivo y modelado parametrico de retroceso de área.
"""
from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path

import cv2
import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import config
import detector
import gis_engine
import advanced_analysis
import glaciares_database
from utils import pdf_report, sample_images

# ----------------------------------------------------------------------------
# Configuracion de pagina
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="GlaciarSense",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ocultar unicamente el boton Deploy sin afectar la barra lateral ni el selector de temas
st.markdown(
    """
    <style>
    .stDeployButton, [data-testid="stAppDeployButton"], [data-testid="manage-app-button"] {
        display: none !important;
    }
    footer { visibility: hidden !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Inicializacion de sesion y parametros por defecto
# (Debe ocurrir ANTES de instanciar los widgets para permitir callbacks)
# ----------------------------------------------------------------------------
def apply_preset():
    """Carga los parámetros del glaciar predefinido seleccionado."""
    preset_name = st.session_state.get("preset", config.DEFAULT_PRESET)
    p = config.GLACIER_PRESETS.get(preset_name, config.GLACIER_PRESETS[config.DEFAULT_PRESET])
    st.session_state["lat"] = float(p["lat"])
    st.session_state["lon"] = float(p["lon"])
    st.session_state["area_km2"] = float(p["area_km2"])
    st.session_state["rate_km2"] = float(min(max(p["rate_km2"], 0.001), 5.0))


if "preset" not in st.session_state:
    st.session_state["preset"] = config.DEFAULT_PRESET
    apply_preset()

st.session_state.setdefault("k_coef", config.K_DEFAULT)
st.session_state.setdefault("decay_model", "linear")
st.session_state.setdefault("history", [])
st.session_state.setdefault(
    "percentages",
    {"clean_ice": 65.0, "black_carbon": 5.0, "dust": 20.0, "meltwater_pool": 10.0},
)
st.session_state.setdefault(
    "albedo",
    gis_engine.albedo_summary(st.session_state["percentages"]),
)

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("GlaciarSense")
    st.caption("v2.2 -- Procesamiento de imagen glaciar, modelado de retroceso y conocimiento avanzado")

    st.markdown("---")
    st.selectbox(
        "Glaciar de referencia",
        list(config.GLACIER_PRESETS),
        key="preset",
        on_change=apply_preset,
        help="Carga coordenadas y datos de inventario del glaciar seleccionado.",
    )

    p_info = config.GLACIER_PRESETS.get(st.session_state.get("preset", config.DEFAULT_PRESET), {})
    if "fuente" in p_info:
        st.caption(f"Fuente: {p_info['fuente']}")
        st.caption(f"Tipo: {p_info.get('tipo', 'Referencial')}")

    st.markdown("---")
    st.markdown("**parámetros del modelo**")

    st.number_input("Latitud", -90.0, 90.0, key="lat", format="%.4f", step=0.01)
    st.number_input("Longitud", -180.0, 180.0, key="lon", format="%.4f", step=0.01)
    st.number_input("Area actual (km2)", 0.01, 5000.0, key="area_km2", step=0.5)
    st.slider(
        "Tasa historica de retroceso (km2/año)",
        0.001, 3.0, step=0.001, key="rate_km2", format="%.3f",
    )
    st.slider(
        "Coeficiente k (sensibilidad albedo-deshielo)",
        0.0, 1.5, step=0.05, key="k_coef",
    )
    st.radio(
        "Modelo de contraccion",
        ["linear", "exponential"],
        key="decay_model",
        format_func=lambda x: "Lineal" if x == "linear" else "Exponencial",
        horizontal=True,
    )

    st.markdown("---")
    st.caption("Repositorio universitario -- 2024-2025")


# ----------------------------------------------------------------------------
# Funciones auxiliares
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def cached_samples():
    return sample_images.get_samples()


@st.cache_data(show_spinner="Procesando imagen...")
def cached_detection(
    rgb: np.ndarray,
    ignore_top: float,
    method_name: str = "color",
    auto_sky: bool = True,
    compare_kmeans: bool = False,
    sensitivity_carbon: float = 1.0,
    sensitivity_dust: float = 1.0,
    sensitivity_water: float = 1.0,
):
    return detector.detect(
        rgb,
        ignore_top_pct=ignore_top,
        method_name=method_name,
        auto_sky=auto_sky,
        compare_kmeans=compare_kmeans,
        sensitivity_carbon=sensitivity_carbon,
        sensitivity_dust=sensitivity_dust,
        sensitivity_water=sensitivity_water,
    )


@st.cache_data(show_spinner=False)
def cached_projection(lat, lon, area_m2, rate_adj_m2, glacier_name, decay_model):
    return gis_engine.build_projection(
        lat, lon, area_m2, rate_adj_m2,
        glacier_name=glacier_name,
        decay_model=decay_model,
    )


def fmt_years(y: float) -> str:
    if not np.isfinite(y) or y >= 9999:
        return "Sin perdida neta"
    if y <= 0:
        return "Area = 0"
    return f"{y:,.1f}"


def _mask_to_png_bytes(mask: np.ndarray) -> bytes:
    """Convierte una mascara booleana a bytes PNG para descarga."""
    img = (mask.astype(np.uint8) * 255)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _gdf_to_geojson_bytes(gdf) -> bytes:
    """Serializa un GeoDataFrame a bytes GeoJSON para descarga."""
    features = []
    for _, row in gdf.iterrows():
        if row.geometry.is_empty:
            continue
        feat = {
            "type": "Feature",
            "geometry": row.geometry.__geo_interface__,
            "properties": {
                "horizonte": row.get("etiqueta", ""),
                "area_km2": round(row.get("area_km2", 0), 4),
                "estado": row.get("estado", ""),
            },
        }
        features.append(feat)
    geojson = {"type": "FeatureCollection", "features": features}
    return json.dumps(geojson, indent=2, ensure_ascii=False).encode("utf-8")


# ----------------------------------------------------------------------------
# Encabezado
# ----------------------------------------------------------------------------
st.title("GlaciarSense")
st.caption(
    "Clasificacion de coberturas superficiales por procesamiento digital de imagen "
    "y modelado parametrico de retroceso glaciar."
)

# ----------------------------------------------------------------------------
# Pestanias
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Clasificación de imagen",
    "Proyección espacial (GIS)",
    "Sensibilidad y proyecciones",
    "Datos regionales (WGMS)",
    "Análisis Avanzado",
])


# ============================================================================
# TAB 1 -- Clasificacion de imagen
# ============================================================================
with tab1:
    st.subheader("Segmentacion de coberturas y albedo efectivo")

    sub_modo = st.radio(
        "Modo de entrada",
        ["Imagen individual", "Comparacion multiple (2 a 5 fotos)"],
        horizontal=True,
    )

    if sub_modo == "Imagen individual":
        col_in, col_cfg = st.columns([2, 1])

        with col_in:
            origen = st.radio("Fuente", ["Muestra incluida", "Subir archivo"], horizontal=True)
            samples = cached_samples()
            rgb = None

            if origen == "Subir archivo":
                up = st.file_uploader("Imagen del glaciar (JPG, PNG, WEBP)", type=["jpg", "jpeg", "png", "webp"])
                if up is not None:
                    try:
                        rgb = detector.load_image(up.getvalue())
                        st.session_state["uploaded_image"] = rgb
                    except detector.ImageError as e:
                        st.error(str(e))
                if rgb is None:
                    st.info("Sin archivo cargado. Se usa la muestra por defecto.")
                    rgb = samples["2. Polvo moderado"]
                    st.session_state["uploaded_image"] = None
            else:
                nombre = st.selectbox("Muestra", list(samples), index=1)
                rgb = samples[nombre]
                st.session_state["uploaded_image"] = None

        with col_cfg:
            st.markdown("**Configuración**")
            metodo_sel = st.selectbox(
                "Método de segmentación",
                ["color", "kmeans"],
                format_func=lambda x: "Umbrales LAB+HSV (CLAHE)" if x == "color" else "K-means (k=4, espacio LAB)",
            )
            auto_sky_chk = st.checkbox("Exclusión automática de cielo", value=True)
            ignore_top = st.slider("Recorte superior manual (%)", 0, 60, 0)
            comparar_km = st.checkbox("Comparar ambos métodos", value=False)
            
            # MEJORA DE PRECISIÓN: Ajuste manual de sensibilidad
            with st.expander("Ajustar sensibilidad (avanzado)"):
                st.caption("Ajusta la sensibilidad de detección para cada tipo de contaminante")
                
                sensibilidad_carbon = st.slider(
                    "Carbono negro",
                    0.5, 2.0, 1.0, 0.1,
                    help="Mayor valor = detecta más carbono negro (más sensible)"
                )
                
                sensibilidad_polvo = st.slider(
                    "Polvo mineral",
                    0.5, 2.0, 1.0, 0.1,
                    help="Mayor valor = detecta más polvo (más sensible)"
                )
                
                sensibilidad_agua = st.slider(
                    "Agua de deshielo",
                    0.5, 2.0, 1.0, 0.1,
                    help="Mayor valor = detecta más agua (más sensible)"
                )
                
                if st.button("Restaurar valores por defecto"):
                    st.rerun()
                
                st.info("Si ves mucho/poco de un contaminante, ajusta su sensibilidad y vuelve a procesar")
            
            # Guardar sensibilidades en session_state
            st.session_state["sens_carbon"] = sensibilidad_carbon
            st.session_state["sens_polvo"] = sensibilidad_polvo  
            st.session_state["sens_agua"] = sensibilidad_agua

        # Procesamiento
        try:
            det = cached_detection(
                rgb,
                float(ignore_top),
                method_name=metodo_sel,
                auto_sky=auto_sky_chk,
                compare_kmeans=comparar_km,
                sensitivity_carbon=float(sensibilidad_carbon),
                sensitivity_dust=float(sensibilidad_polvo),
                sensitivity_water=float(sensibilidad_agua),
            )
        except detector.ImageError as e:
            st.error(str(e))
            st.stop()

        st.session_state["detection"] = det
        st.session_state["percentages"] = det.percentages
        pct = det.percentages

        # Confianza y avisos
        col_met, col_conf = st.columns([3, 1])
        col_met.caption(f"método aplicado: **{det.method}**")
        col_conf.metric("Confianza", f"{det.confidence * 100:.0f} %")

        for w in det.warnings:
            st.warning(w)

        # Imagenes
        c1, c2 = st.columns(2)
        c1.image(rgb, caption="Imagen original", width="stretch")
        c2.image(det.annotated, caption="Mapa de clasificacion", width="stretch")

        # Albedo
        alb = gis_engine.albedo_summary(pct)
        st.session_state["albedo"] = alb

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Albedo efectivo", f"{alb['alpha_eff']:.3f}")
        m2.metric("Albedo ref. hielo limpio", f"{alb['alpha_clean']:.3f}")
        m3.metric("Reduccion absoluta", f"-{alb['loss_abs']:.3f}")
        m4.metric("Reduccion relativa", f"{alb['loss_pct']:.1f} %")

        # Grafico y tabla de coberturas
        g1, g2 = st.columns([1, 1])
        df_cobertura = pd.DataFrame({
            "Clase": [config.LABELS_ES[c] for c in config.CLASSES],
            "Cobertura (%)": [round(pct[c], 2) for c in config.CLASSES],
            "Albedo ref.": [config.ALBEDOS[c] for c in config.CLASSES],
            "_c": list(config.CLASSES),
        })

        fig_pie = px.pie(
            df_cobertura,
            names="Clase",
            values="Cobertura (%)",
            hole=0.45,
            color="Clase",
            color_discrete_map={config.LABELS_ES[c]: config.color_hex(c) for c in config.CLASSES},
        )
        fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
        g1.plotly_chart(fig_pie, width="stretch")
        g2.dataframe(df_cobertura.drop(columns="_c"), hide_index=True, width="stretch")

        # Comparacion K-means si esta activa
        if det.comparison is not None:
            st.markdown("**Comparativa de métodos**")
            cmp_p = det.comparison["percentages"]
            df_cmp = pd.DataFrame({
                "Superficie": [config.LABELS_ES[c] for c in config.CLASSES],
                f"Umbrales ({metodo_sel})": [f"{pct[c]:.1f} %" for c in config.CLASSES],
                "K-means (k=4)": [f"{cmp_p[c]:.1f} %" for c in config.CLASSES],
            })
            st.dataframe(df_cmp, hide_index=True, width="stretch")

        # Perfiles radiometricos
        if getattr(det, "spectral_profiles", None):
            with st.expander("Perfiles radiometricos por cobertura (L* CIELAB)"):
                df_spec = pd.DataFrame([
                    {
                        "Superficie": config.LABELS_ES.get(cls, cls),
                        "L* media": f"{data['mean_L']:.1f}",
                        "Desv. est.": f"{data['std_L']:.1f}",
                        "Pixeles": f"{data['pixels']:,}",
                    }
                    for cls, data in det.spectral_profiles.items()
                    if data.get("pixels", 0) > 0
                ])
                st.dataframe(df_spec, hide_index=True, width="stretch")

        with st.expander("Frontera del modelo: Bioalbedo y Ecosistemas Microbianos"):
            st.markdown(
                """
                - **Comunidades microbianas criosféricas:** Algas de nieve (*Chloromonas*, *Chlamydomonas*) y cianobacterias fijadoras colonizan la capa superficial del hielo durante la estación húmeda/cálida.
                - **Impacto radiométrica:** Producen pigmentos fotoprotectores oscuros (astaxantina, purpurina) que pueden reducir el albedo local hasta valores entre 0.15 y 0.30, similar al polvo fino o carbono negro.
                - **Limitación en imágenes RGB:** Con cámaras estándar sin bandas hiperespectrales (índices clorofílicos específicos en ~680 nm), las colonias biológicas densas pueden agruparse con 'polvo mineral' o 'carbono negro'.
                """
            )

        # Historial
        registro_actual = {
            "Hora": datetime.now().strftime("%H:%M:%S"),
            "método": det.method[:22],
            "Albedo": round(alb["alpha_eff"], 3),
            "Hielo (%)": round(pct["clean_ice"], 1),
            "Carbon (%)": round(pct["black_carbon"], 1),
            "Polvo (%)": round(pct["dust"], 1),
            "Agua (%)": round(pct["meltwater_pool"], 1),
            "Confianza (%)": round(det.confidence * 100, 0),
        }
        if not st.session_state["history"] or st.session_state["history"][-1].get("Albedo") != registro_actual["Albedo"]:
            st.session_state["history"].append(registro_actual)

        # --- Exportaciones ---
        st.markdown("---")
        st.markdown("**Exportar resultados**")
        exp1, exp2, exp3, exp4 = st.columns(4)

        # CSV de metricas
        csv_buf = io.StringIO()
        pd.DataFrame([registro_actual]).to_csv(csv_buf, index=False)
        exp1.download_button(
            "Metricas (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"metricas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width="stretch",
        )

        # Mascara de clasificacion (PNG)
        if hasattr(det, "annotated") and det.annotated is not None:
            ann_pil = det.annotated
            ann_buf = io.BytesIO()
            from PIL import Image as PILImage
            PILImage.fromarray(ann_pil).save(ann_buf, format="PNG")
            exp2.download_button(
                "Mapa clasificado (PNG)",
                data=ann_buf.getvalue(),
                file_name=f"clasificacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png",
                width="stretch",
            )

        # Mascaras binarias individuales (ZIP)
        if hasattr(det, "masks") and det.masks:
            import zipfile
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for cls_name, mask_arr in det.masks.items():
                    zf.writestr(f"mascara_{cls_name}.png", _mask_to_png_bytes(mask_arr))
            exp3.download_button(
                "Mascaras binarias (ZIP)",
                data=zip_buf.getvalue(),
                file_name=f"mascaras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                width="stretch",
            )

        # PDF
        with exp4:
            try:
                scen_pdf = gis_engine.compute_scenarios(
                    float(st.session_state["area_km2"]) * 1e6,
                    float(st.session_state["rate_km2"]) * 1e6,
                    alb["alpha_eff"],
                    alb["alpha_clean"],
                    float(st.session_state["k_coef"]),
                    include_ssp=True,
                )
                mc_pdf = gis_engine.simulate_monte_carlo(
                    float(st.session_state["area_km2"]) * 1e6,
                    float(st.session_state["rate_km2"]) * 1e6,
                    pct,
                    float(st.session_state["k_coef"]),
                    n_runs=500,
                )
                pdf_data = pdf_report.generate_pdf_report(
                    st.session_state["preset"],
                    float(st.session_state["lat"]),
                    float(st.session_state["lon"]),
                    float(st.session_state["area_km2"]),
                    float(st.session_state["rate_km2"]),
                    det, alb, scen_pdf, mc_pdf, det.annotated,
                )
                st.download_button(
                    "Informe (PDF)",
                    data=pdf_data,
                    file_name=f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    width="stretch",
                )
            except Exception:
                st.caption("PDF no disponible en este momento.")

    else:
        # --- Comparador multi-imagen ---
        archivos_subidos = st.file_uploader(
            "Selecciona entre 2 y 5 imagenes",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )

        fotos_a_comparar = []
        nombres_fotos = []

        if archivos_subidos and 2 <= len(archivos_subidos) <= 5:
            for arch in archivos_subidos:
                try:
                    fotos_a_comparar.append(detector.load_image(arch.getvalue()))
                    nombres_fotos.append(arch.name)
                except Exception as e:
                    st.error(f"Error al procesar {arch.name}: {e}")
        else:
            st.info("Carga entre 2 y 5 imagenes, o revisa el lote de muestras incluidas:")
            samples_dict = cached_samples()
            nombres_fotos = list(samples_dict.keys())
            fotos_a_comparar = [samples_dict[k] for k in nombres_fotos]

        if len(fotos_a_comparar) >= 2:
            cols_img = st.columns(len(fotos_a_comparar))
            resultados_multi = []

            for idx, (im, nom) in enumerate(zip(fotos_a_comparar, nombres_fotos)):
                res_i = cached_detection(im, 0.0, "color", auto_sky=True)
                alb_i = gis_engine.albedo_summary(res_i.percentages)
                resultados_multi.append({"nombre": nom, "res": res_i, "alb": alb_i})

                with cols_img[idx]:
                    st.image(res_i.annotated, caption=f"{nom[:18]}", width="stretch")
                    st.metric(f"Albedo #{idx+1}", f"{alb_i['alpha_eff']:.3f}")

            if resultados_multi:
                st.session_state["percentages"] = resultados_multi[0]["res"].percentages
                st.session_state["albedo"] = resultados_multi[0]["alb"]
                pct = resultados_multi[0]["res"].percentages

            data_chart = []
            for item in resultados_multi:
                p = item["res"].percentages
                for c in config.CLASSES:
                    data_chart.append({
                        "Imagen": item["nombre"][:20],
                        "Material": config.LABELS_ES[c],
                        "Cobertura (%)": round(p[c], 1),
                    })
            df_chart = pd.DataFrame(data_chart)
            fig_bar = px.bar(
                df_chart, x="Imagen", y="Cobertura (%)", color="Material",
                barmode="stack",
                color_discrete_map={config.LABELS_ES[c]: config.color_hex(c) for c in config.CLASSES},
            )
            fig_bar.update_layout(height=320, margin=dict(t=10, b=10))
            st.plotly_chart(fig_bar, width="stretch")

            df_alb_comp = pd.DataFrame([
                {"Imagen": item["nombre"][:20], "Albedo efectivo": item["alb"]["alpha_eff"]}
                for item in resultados_multi
            ])
            fig_alb = px.line(
                df_alb_comp, x="Imagen", y="Albedo efectivo", markers=True,
            )
            fig_alb.update_yaxes(range=[0.0, 0.6])
            fig_alb.update_layout(height=260)
            st.plotly_chart(fig_alb, width="stretch")

    if st.session_state["history"]:
        with st.expander("Historial de la sesion"):
            st.dataframe(pd.DataFrame(st.session_state["history"]), hide_index=True, width="stretch")


# ============================================================================
# TAB 2 -- Proyeccion espacial (GIS)
# ============================================================================
with tab2:
    st.subheader("Mapa de perímetros proyectados")
    
    # Verificar si hay datos procesados
    if "albedo" not in st.session_state or "detection" not in st.session_state:
        st.info("**Primero procesa una imagen en la Tab 1** para ver las proyecciones espaciales basadas en el albedo detectado.")
        st.markdown("""
        Este mapa mostrará:
        - Perímetro actual del glaciar
        - Proyecciones a 5, 10 y 20 años
        - Basado en el albedo y contaminantes detectados en tu imagen
        """)
        st.stop()

    lat_val = float(st.session_state.get("lat", -13.93))
    lon_val = float(st.session_state.get("lon", -70.83))
    area_m2_val = float(st.session_state.get("area_km2", 42.0)) * 1e6
    rate_m2_val = float(st.session_state.get("rate_km2", 0.35)) * 1e6
    k_val = float(st.session_state.get("k_coef", config.K_DEFAULT))
    alb_val = st.session_state.get("albedo", {"alpha_eff": 0.40, "alpha_clean": 0.45})

    scen_all = gis_engine.compute_scenarios(
        area_m2_val, rate_m2_val, alb_val["alpha_eff"], alb_val["alpha_clean"], k_val, include_ssp=True
    )
    central_scen = scen_all[1]

    try:
        gdf_proj = cached_projection(
            lat_val, lon_val, area_m2_val, central_scen.rate_adj,
            st.session_state["preset"], st.session_state["decay_model"]
        )
    except ValueError as e:
        st.error(str(e))
        st.stop()

    is_real = gdf_proj.attrs.get("is_real_contour", False)
    source_desc = gdf_proj.attrs.get("source", "Elipse parametrica")
    if is_real:
        st.success(f"Contorno vectorial activo: {source_desc}")
    else:
        st.info(f"Contorno proyectado: {source_desc} (elipse parametrica ajustada al área en UTM)")

    st.markdown(
        "El mapa muestra la imagen satelital real del glaciar con los **perimetros de contraccion superficial** "
        "calculados a diferentes horizontes temporales bajo la tasa de ablacion ajustada."
    )

    # Leyenda visual de colores
    st.markdown(
        """
        <div style="display: flex; flex-wrap: wrap; gap: 20px; padding: 8px 12px; background-color: rgba(255,255,255,0.05); border-radius: 6px; margin-bottom: 12px; font-size: 14px;">
            <span><strong style="color: #00e5ff;">■ Cyan:</strong> Perimetro actual (observado)</span>
            <span><strong style="color: #ffd60a;">■ Amarillo:</strong> Proyeccion a +5 anios</span>
            <span><strong style="color: #ff8c00;">■ Naranja:</strong> Proyeccion a +10 anios</span>
            <span><strong style="color: #e63946;">■ Rojo:</strong> Proyeccion a +20 anios</span>
            <span><strong style="color: #3388ff;">● Marcador:</strong> Coordenada centroide</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nonempty_geoms = gdf_proj[~gdf_proj.geometry.is_empty]
    if not nonempty_geoms.empty:
        minx, miny, maxx, maxy = nonempty_geoms.total_bounds
    else:
        minx, miny, maxx, maxy = lon_val - 0.05, lat_val - 0.05, lon_val + 0.05, lat_val + 0.05

    # Mapa con imagen satelital como capa base predeterminada
    mapa = folium.Map(
        location=[lat_val, lon_val],
        zoom_start=13,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satelite (Esri)",
        control_scale=True,
    )
    folium.TileLayer("OpenStreetMap", name="Mapa Callejero (OSM)").add_to(mapa)
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="OpenTopoMap",
        name="Topografico (Relieve)",
    ).add_to(mapa)

    for _, row in gdf_proj.iloc[::-1].iterrows():
        if row.geometry.is_empty:
            continue
        folium.GeoJson(
            row.geometry.__geo_interface__,
            name=row["etiqueta"],
            style_function=lambda _f, col=row["color"], act=(row["anios"] == 0): dict(
                color=col,
                weight=3,
                fillColor=col,
                fillOpacity=0.30 if act else 0.18,
            ),
            tooltip=f"{row['etiqueta']}: {row['area_km2']:.2f} km2",
        ).add_to(mapa)

    # Marcador del glaciar actual
    folium.Marker(
        [lat_val, lon_val],
        tooltip=f"Centroide: {st.session_state['preset']}",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(mapa)
    
    # AGREGAR GLACIARES CONOCIDOS COMO MARCADORES CLICKEABLES
    st.markdown("---")
    st.markdown("### Seleccionar otro glaciar")
    
    # Selector de país
    paises = glaciares_database.get_paises()
    pais_sel = st.selectbox("País", ["Todos"] + paises, index=0)
    
    # Filtrar glaciares
    if pais_sel == "Todos":
        glaciares_mostrar = glaciares_database.get_glaciares_activos()
    else:
        glaciares_mostrar = glaciares_database.get_glaciares_por_pais(pais_sel)
    
    # Agregar marcadores de glaciares conocidos al mapa
    for nombre, info in glaciares_mostrar.items():
        if info['area_km2'] > 0:  # Solo glaciares activos
            # Crear popup con botón para seleccionar
            popup_html = f"""
            <div style="font-family: Arial; min-width: 200px;">
                <h4 style="margin: 0 0 10px 0;">{nombre}</h4>
                <p style="margin: 5px 0;"><b>Área:</b> {info['area_km2']} km²</p>
                <p style="margin: 5px 0;"><b>Retroceso:</b> {info['rate_km2']} km²/año</p>
                <p style="margin: 5px 0;"><b>Tipo:</b> {info['tipo']}</p>
                <p style="margin: 5px 0; font-size: 10px; color: #666;">{info['fuente']}</p>
            </div>
            """
            
            folium.Marker(
                [info['lat'], info['lon']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=nombre,
                icon=folium.Icon(color="green", icon="mountain" if "volc" not in info['tipo'].lower() else "fire", prefix="fa")
            ).add_to(mapa)
    
    mapa.fit_bounds([[miny, minx], [maxy, maxx]], padding=(30, 30))
    folium.LayerControl(position="topright").add_to(mapa)

    # Renderizar mapa con captura de clicks
    map_data = st_folium(mapa, height=520, use_container_width=True, returned_objects=["last_clicked"])
    
    # SELECCIÓN RÁPIDA POR LISTA
    st.markdown("#### Selección rápida")
    col_sel1, col_sel2 = st.columns([3, 1])
    
    with col_sel1:
        glaciar_seleccionado = st.selectbox(
            "Selecciona un glaciar",
            list(glaciares_mostrar.keys()),
            index=list(glaciares_mostrar.keys()).index(st.session_state['preset']) if st.session_state['preset'] in glaciares_mostrar else 0
        )
    
    with col_sel2:
        if st.button("Cargar glaciar", use_container_width=True):
            info_glaciar = glaciares_database.get_glaciar_info(glaciar_seleccionado)
            if info_glaciar:
                # Actualizar session_state con el nuevo glaciar
                st.session_state["lat"] = info_glaciar["lat"]
                st.session_state["lon"] = info_glaciar["lon"]
                st.session_state["area_km2"] = info_glaciar["area_km2"]
                st.session_state["rate_km2"] = info_glaciar["rate_km2"]
                st.session_state["preset"] = glaciar_seleccionado
                st.success(f"Glaciar cargado: **{glaciar_seleccionado}**")
                st.rerun()  # Recargar para actualizar el mapa

    # Tabla de perimetros
    tab_perimetros = gdf_proj[["etiqueta", "area_km2", "estado"]].rename(
        columns={"etiqueta": "Horizonte", "area_km2": "Area (km2)", "estado": "Estado"}
    )
    st.dataframe(tab_perimetros, hide_index=True, width="stretch")

    # Retroceso frontal
    retreat_res = gis_engine.estimate_frontal_retreat(area_m2_val, gdf_proj)
    if retreat_res:
        st.markdown("**Retroceso frontal lineal estimado**")
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("+5 años", f"{retreat_res.get(5, 0):.1f} m")
        rc2.metric("+10 años", f"{retreat_res.get(10, 0):.1f} m")
        rc3.metric("+20 años", f"{retreat_res.get(20, 0):.1f} m")

    with st.expander("Procesos Geomorfológicos no observables en superficie (Cavidades y Dinámica Subglacial)"):
        st.markdown(
            """
            - **Cavidades basales y topografía subyacente:** Los modelos de contracción bidimensional 2D (buffer o elipse) asumen un lecho rocoso uniforme. Si existen sobreexcavaciones glaciales o cubetas profundas, el hielo remanente puede colapsar abruptamente por descalce basal antes de que la línea de contorno prediga su retroceso.
            - **Redes hidráulicas subglaciales y sedimentos:** Los canales de agua de deshielo a presión en la base del glaciar aceleran el deslizamiento basal por lubricación y transportan sedimentos que erosionan el lecho rocoso, alterando la estabilidad estructural sin manifestarse en la fotografía superficial.
            """
        )

    # Descarga del GeoJSON proyectado
    st.markdown("---")
    geojson_bytes = _gdf_to_geojson_bytes(gdf_proj)
    st.download_button(
        "Descargar perimetros proyectados (GeoJSON)",
        data=geojson_bytes,
        file_name=f"perimetros_{st.session_state['preset'].split('(')[0].strip()}_{datetime.now().strftime('%Y%m%d')}.geojson",
        mime="application/geo+json",
        width="stretch",
    )


# ============================================================================
# TAB 3 -- Sensibilidad y proyecciones
# ============================================================================
with tab3:
    st.subheader("Escenarios de retroceso y análisis de incertidumbre")
    
    # Verificar si hay datos procesados
    if "percentages" not in st.session_state or "detection" not in st.session_state:
        st.info("**Primero procesa una imagen en la Tab 1** para ver los escenarios de sensibilidad basados en los contaminantes detectados.")
        st.markdown("""
        Este análisis mostrará:
        - Escenarios SSP (optimista, central, pesimista)
        - Simulación Monte Carlo (1000 corridas)
        - Basado en el albedo real detectado en tu imagen
        """)
        st.stop()

    # Lectura de parametros activos
    pct = st.session_state.get(
        "percentages",
        {"clean_ice": 65.0, "black_carbon": 5.0, "dust": 20.0, "meltwater_pool": 10.0},
    )
    alb_val = st.session_state.get("albedo", gis_engine.albedo_summary(pct))

    area_m2_val = float(st.session_state.get("area_km2", 42.0)) * 1e6
    rate_m2_val = float(st.session_state.get("rate_km2", 0.35)) * 1e6
    k_val = float(st.session_state.get("k_coef", config.K_DEFAULT))

    scen_all = gis_engine.compute_scenarios(
        area_m2_val, rate_m2_val, alb_val["alpha_eff"], alb_val["alpha_clean"], k_val, include_ssp=True
    )
    central_scen = scen_all[1]

    # Formulacion matematica
    st.latex(r"\Delta M = \max\!\left(\frac{1-\alpha_{ef}}{1-\alpha_{limpio}} - 1,\; 0\right)")
    st.latex(r"Tasa_{adj} = Tasa_{hist} \times \bigl(1 + \mathrm{clip}(k \cdot \Delta M,\;0,\;1.5)\bigr)")

    dm_val = gis_engine.melt_acceleration(alb_val["alpha_eff"], alb_val["alpha_clean"])
    mr1, mr2, mr3, mr4 = st.columns(4)
    mr1.metric("Albedo efectivo", f"{alb_val['alpha_eff']:.3f}")
    mr2.metric("Delta M", f"+{dm_val * 100:.1f} %")
    mr3.metric("Factor contaminante", f"+{central_scen.factor * 100:.1f} %")
    mr4.metric("Tasa ajustada (km2/a)", f"{central_scen.rate_adj / 1e6:.4f}")

    opt_scen, pes_scen = scen_all[0], scen_all[2]
    if np.isfinite(opt_scen.years) and opt_scen.years > 0:
        st.info(
            f"Rango proyectado: {pes_scen.years:,.0f} -- {opt_scen.years:,.0f} años "
            f"(central: {central_scen.years:,.0f} años)."
        )

    # Tabla de escenarios
    st.markdown("**Escenarios de sensibilidad (incluye SSP del IPCC AR6)**")
    tabla_scen = pd.DataFrame([
        {
            "Escenario": s.name,
            "Tipo": s.tipo,
            "Tasa adj. (km2/a)": round(s.rate_adj / 1e6, 4),
            "años restantes": fmt_years(s.years),
            "Fundamento": s.descripcion,
        }
        for s in scen_all
    ])
    st.dataframe(tabla_scen, hide_index=True, width="stretch")

    # Curvas de contraccion
    st.markdown("**Curvas de contraccion de área**")
    finite_years = [s.years for s in scen_all if np.isfinite(s.years) and s.years > 0]
    horizon_max = min(max(finite_years) * 1.15, 300) if finite_years else 60
    t_span = np.linspace(0, horizon_max, 250)

    fig_curves = go.Figure()
    colores_map = {
        "Optimista": "#2a9d8f",
        "Central": "#f4a261",
        "Pesimista": "#e63946",
        "SSP1-2.6 (Bajas emisiones)": "#3a86ff",
        "SSP2-4.5 (Emisiones intermedias)": "#8338ec",
        "SSP5-8.5 (Altas emisiones)": "#d90429",
    }
    for s in scen_all:
        col = colores_map.get(s.name, "#777777")
        dash_style = "dash" if "SSP" in s.name else "solid"
        fig_curves.add_trace(go.Scatter(
            x=t_span,
            y=gis_engine.area_curve(area_m2_val, s.rate_adj, t_span, model=st.session_state["decay_model"]) / 1e6,
            mode="lines", name=s.name,
            line=dict(color=col, width=2.5, dash=dash_style),
        ))

    fig_curves.add_trace(go.Scatter(
        x=t_span,
        y=gis_engine.area_curve(area_m2_val, rate_m2_val, t_span, model=st.session_state["decay_model"]) / 1e6,
        mode="lines", name="Tasa base (sin impurezas)",
        line=dict(color="#888888", width=1.5, dash="dot"),
    ))
    fig_curves.update_layout(
        xaxis_title="Anios",
        yaxis_title="Area restante (km2)",
        height=360,
        margin=dict(t=10, b=10),
        legend=dict(orientation="h", y=-0.25),
    )
    st.plotly_chart(fig_curves, width="stretch")

    # Monte Carlo
    st.markdown("---")
    st.markdown("**Simulacion Monte Carlo (1,000 corridas)**")
    st.caption(
        "Perturbacion estocastica del coeficiente k (+/-25%), "
        "la tasa historica (+/-20%) y los albedos de referencia (+/-10%)."
    )

    mc_res = gis_engine.simulate_monte_carlo(area_m2_val, rate_m2_val, pct, k_val, n_runs=1000)
    col_mc1, col_mc2, col_mc3, col_mc4 = st.columns(4)
    col_mc1.metric("Mediana", f"{mc_res['median']:.1f} años")
    col_mc2.metric("P10", f"{mc_res['p10']:.1f} años")
    col_mc3.metric("P90", f"{mc_res['p90']:.1f} años")
    col_mc4.metric("Desv. est.", f"{mc_res['std']:.1f} años")

    valid_samples = mc_res["samples"][mc_res["samples"] < 1000]
    if len(valid_samples) > 0:
        fig_hist = px.histogram(
            x=valid_samples, nbins=35,
            labels={"x": "Anios restantes", "y": "Frecuencia"},
            color_discrete_sequence=["#2a9d8f"],
        )
        fig_hist.add_vline(x=mc_res["median"], line_dash="dash", line_color="#e76f51", annotation_text="Mediana")
        fig_hist.add_vline(x=mc_res["p10"], line_dash="dot", line_color="#e63946", annotation_text="P10")
        fig_hist.add_vline(x=mc_res["p90"], line_dash="dot", line_color="#457b9d", annotation_text="P90")
        fig_hist.update_layout(height=300, margin=dict(t=20, b=10))
        st.plotly_chart(fig_hist, width="stretch")

    # Diagrama de tornado
    st.markdown("---")
    st.markdown("**análisis de sensibilidad univariada (tornado)**")
    tornado_list = gis_engine.compute_sensitivity_tornado(area_m2_val, rate_m2_val, pct, k_val)
    if tornado_list:
        tornado_df = pd.DataFrame(tornado_list)
        fig_tornado = px.bar(
            tornado_df, x="amplitud", y="parámetro", orientation="h",
            labels={"amplitud": "Amplitud (años)", "parámetro": "Parámetro"},
            color="amplitud", color_continuous_scale="Viridis",
        )
        fig_tornado.update_layout(height=260, margin=dict(t=10, b=10, l=10))
        st.plotly_chart(fig_tornado, width="stretch")

        t_disp = tornado_df[["parámetro", "min_years", "base_years", "max_years", "amplitud"]].rename(
            columns={
                "parámetro": "Parámetro",
                "min_years": "Min (años)",
                "base_years": "Base (años)",
                "max_years": "Max (años)",
                "amplitud": "Amplitud",
            }
        )
        st.dataframe(t_disp, hide_index=True, width="stretch")

    with st.expander("Dinámica Glaciológica: Inercia, Avalanchas y Puntos de No Retorno"):
        st.markdown(
            """
            - **Inercia térmica y respuesta desacoplada (*Tipping Points*):** Los glaciares de gran volumen tienen tiempos de relajación dinámicos de décadas. Aunque el clima se estabilizara hoy, la masa continuará perdiéndose por el desequilibrio geométrico acumulado. Superada cierta cota de línea de equilibrio (ELA), el glaciar entra en un régimen irreversible de balance negativo continuo.
            - **Contribución de avalanchas a gran altitud:** En cuencas andinas empinadas, el manto glaciar no solo se nutre de precipitación nival directa, sino de avalanchas periódicas de nieve y hielo desde cornisas superiores. Este flujo masa localizado genera variaciones de espesor que los modelos continuos de retroceso superficial simplifican en un valor medio.
            """
        )


# ============================================================================
# TAB 4 -- Datos regionales (WGMS)
# ============================================================================
with tab4:
    st.subheader("Registros historicos de perdida glaciar (WGMS / RGI)")
    st.caption(
        "Datos consolidados del World Glacier Monitoring Service (WGMS) "
        "y el Randolph Glacier Inventory (RGI). "
        "Estos datos son independientes del procesamiento de imagen."
    )

    path_regiones = config.DATA_DIR / "wgms_global_regions.csv"
    path_andean = config.DATA_DIR / "wgms_andean_glaciers.csv"

    if path_regiones.exists() and path_andean.exists():
        df_reg = pd.read_csv(path_regiones)
        df_and = pd.read_csv(path_andean)

        st.markdown("**Reduccion acumulada de área por region (1970 - presente)**")
        fig_global_bar = px.bar(
            df_reg.sort_values("perdida_pct", ascending=True),
            x="perdida_pct", y="region", orientation="h",
            color="perdida_pct", color_continuous_scale="Reds_r",
            labels={"perdida_pct": "Variacion (%)", "region": "Region"},
        )
        fig_global_bar.update_layout(height=340, margin=dict(t=10, b=10, l=10))
        st.plotly_chart(fig_global_bar, width="stretch")

        st.markdown("**Series historicas en glaciares andinos**")
        fig_and_line = px.line(
            df_and, x="anio", y="area_km2", color="glaciar", markers=True,
            labels={"anio": "Año", "area_km2": "Área (km²)", "glaciar": "Glaciar"},
        )
        fig_and_line.update_layout(height=340, margin=dict(t=10, b=10))
        st.plotly_chart(fig_and_line, width="stretch")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**Inventario global (WGMS)**")
            st.dataframe(
                df_reg[["region", "perdida_pct", "tasa_anual_pct", "balance_masa_m_we_yr"]].rename(
                    columns={
                        "region": "Region",
                        "perdida_pct": "Perdida (%)",
                        "tasa_anual_pct": "Tasa (%/año)",
                        "balance_masa_m_we_yr": "Balance masa (m w.e./a)",
                    }
                ),
                hide_index=True, width="stretch",
            )
        with col_t2:
            st.markdown("**Mediciones andinas (INAIGEM / IRD)**")
            st.dataframe(
                df_and.rename(columns={
                    "glaciar": "Glaciar", "pais": "Pais", "año": "año",
                    "area_km2": "área (km2)", "fuente": "Fuente",
                }),
                hide_index=True, width="stretch",
            )

        st.caption(
            "Licencia: CC BY 4.0. Datos actualizables con scripts/descargar_datos.py."
        )

        with st.expander("Dimensión Socioecológica: Conocimiento Comunitario Local y Gestión del Territorio"):
            st.markdown(
                """
                - **Saber empírico tradicional vs. datos de satélite:** Las comunidades altoandinas que habitan las zonas de amortiguamiento poseen observaciones generacionales sobre patrones de deshielo, variaciones en caudales de manantiales y cambios en la fenología de pastizales (*bofedales*).
                - **Desconexión con modelos cuantitativos:** Los modelos satelitales y numéricos suelen ignorar las dinámicas locales de acceso y uso del agua para agricultura comunal, ritualidad y gobernanza del territorio. Una gestión climática integral requiere integrar la información métrica remota con los sistemas de monitoreo y adaptación comunitaria.
                """
            )
    else:
        st.warning("Archivos de datos no encontrados en data/. Ejecuta: python scripts/descargar_datos.py")


# ============================================================================
# TAB 5 -- Análisis Avanzado
# ============================================================================
with tab5:
    st.subheader("Análisis Avanzado")

    if "detection" not in st.session_state or st.session_state["detection"] is None:
        st.warning("Procesa una imagen en la Tab 1 primero para ver el análisis avanzado.")
        st.stop()

    det = st.session_state["detection"]
    samples = cached_samples()
    
    if "uploaded_image" in st.session_state and st.session_state["uploaded_image"] is not None:
        img_rgb = st.session_state["uploaded_image"]
    else:
        img_rgb = samples.get("2. Polvo moderado", list(samples.values())[0])
    
    with st.spinner("Analizando..."):
        result = advanced_analysis.perform_advanced_analysis(img_rgb, det.masks, det.percentages)
    
    # RESULTADOS DIRECTOS - Sin expanders
    st.markdown("### Resultados del Análisis")
    
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
        st.markdown("### Mapas de Detección")
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
    st.markdown("### Índices Espectrales")
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
    st.markdown("### Distribución de Contaminantes")
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
    
    st.markdown("---")
    
    # ESTIMACIÓN DE TIEMPO DE VIDA BASADA EN ESTA IMAGEN
    st.markdown("### Estimación de Impacto en Tiempo de Vida")
    
    # Obtener parámetros del glaciar
    area_km2 = st.session_state.get("area_km2", 42.0)
    rate_km2 = st.session_state.get("rate_km2", 0.35)
    
    # Calcular albedo de esta imagen
    alb = gis_engine.albedo_summary(det.percentages)
    
    # Escenario 1: Con contaminantes de esta imagen
    dm_actual = gis_engine.melt_acceleration(alb['alpha_eff'], alb['alpha_clean'])
    k_val = st.session_state.get("k_coef", config.K_DEFAULT)
    factor_actual = gis_engine.contaminant_factor(dm_actual, k_val)
    tasa_actual = rate_km2 * (1.0 + factor_actual)
    tiempo_actual = area_km2 / tasa_actual if tasa_actual > 0 else 0
    
    # Escenario 2: Sin contaminantes (solo hielo limpio)
    alb_limpio = alb['alpha_clean']
    dm_limpio = gis_engine.melt_acceleration(alb_limpio, alb_limpio)  # Sin degradación
    factor_limpio = gis_engine.contaminant_factor(dm_limpio, k_val)
    tasa_limpia = rate_km2 * (1.0 + factor_limpio)
    tiempo_limpio = area_km2 / tasa_limpia if tasa_limpia > 0 else 0
    
    # Impacto adicional del bioalbedo (si fue detectado)
    if result.bioalbedo_detected:
        # Bioalbedo acelera 10-30% adicional
        aceleracion_bio = 0.20  # 20% promedio
        tasa_con_bio = tasa_actual * (1.0 + aceleracion_bio)
        tiempo_con_bio = area_km2 / tasa_con_bio if tasa_con_bio > 0 else 0
    else:
        tiempo_con_bio = tiempo_actual
    
    # Mostrar comparación
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Si estuviera limpio",
            f"{tiempo_limpio:.1f} años",
            help="Tiempo de vida si el glaciar tuviera solo hielo limpio"
        )
    
    with col2:
        diferencia = tiempo_actual - tiempo_limpio
        st.metric(
            "Con contaminantes detectados",
            f"{tiempo_actual:.1f} años",
            f"{diferencia:.1f} años",
            delta_color="inverse",
            help="Tiempo de vida considerando los contaminantes visibles en esta imagen"
        )
    
    with col3:
        if result.bioalbedo_detected:
            diferencia_bio = tiempo_con_bio - tiempo_actual
            st.metric(
                "Con bioalbedo detectado",
                f"{tiempo_con_bio:.1f} años",
                f"{diferencia_bio:.1f} años",
                delta_color="inverse",
                help="Tiempo de vida si se considera la aceleración por bioalbedo"
            )
        else:
            st.metric(
                "Bioalbedo",
                "No detectado",
                help="No se detectó bioalbedo en esta imagen"
            )
    
    # Interpretación basada en la imagen
    st.info(
        f"**Interpretación:** Los contaminantes detectados en esta imagen "
        f"(carbono negro: {det.percentages.get('black_carbon', 0):.1f}%, "
        f"polvo: {det.percentages.get('dust', 0):.1f}%) "
        f"reducen el albedo a {alb['alpha_eff']:.3f}, acelerando la fusión. "
        f"Esto podría reducir el tiempo de vida en aproximadamente {abs(diferencia):.1f} años "
        f"comparado con un glaciar limpio."
    )
    
    if result.bioalbedo_detected:
        st.warning(
            f"**Bioalbedo detectado ({result.bioalbedo_percentage:.1f}%):** "
            f"La presencia de algas/crioconita podría acelerar aún más la fusión, "
            f"reduciendo potencialmente otros {abs(diferencia_bio):.1f} años el tiempo de vida."
        )
    
    st.markdown("---")
    
    # TABLA RESUMEN FINAL
    st.markdown("### Resumen Completo")
    st.table({
        "Parámetro": ["Bioalbedo", "Grietas", "Rugosidad", "NDVI", "NDWI", "NDSI", "Clusters", "Confianza"],
        "Valor Calculado": [
            f"{'Detectado' if result.bioalbedo_detected else 'No detectado'} ({result.bioalbedo_percentage:.1f}%)",
            f"{result.crevasse_count} grietas",
            f"{result.roughness_index:.2f} ({'Rugoso' if result.roughness_index > 0.6 else 'Moderado' if result.roughness_index > 0.3 else 'Liso'})",
            f"{result.ndvi:.3f}",
            f"{result.ndwi:.3f}",
            f"{result.ndsi:.3f}",
            f"{result.contamination_clusters}",
            f"{result.confidence * 100:.0f}%"
        ]
    })
