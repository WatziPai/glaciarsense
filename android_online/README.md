# GlaciarSense Online (Android)

App Android que abre **la versión completa de GlaciarSense** (la app web de Streamlit) desde internet.
Todo el análisis (segmentación, albedo, mapas Folium, comparador multi-imagen, informes PDF, GeoJSON…)
se ejecuta en el servidor; el teléfono aporta:

- 📷 **Cámara y galería** para subir fotos del glaciar (incluida la selección múltiple del comparador).
- 📍 **GPS** para la geolocalización en el mapa.
- ⬇️ **Descargas** (PDF, CSV, PNG, ZIP, GeoJSON) directo a la carpeta *Descargas* del teléfono.
- 🔌 Pantalla de "sin conexión" con botón *Reintentar*.
- ⚙️ Menú ⋮ → **Servidor…** para cambiar la URL sin recompilar.
- Los enlaces externos (referencias, WGMS, etc.) se abren en el navegador.

> ¿Sin señal en la montaña? Usa la otra app, `../android_app` (100 % offline, procesa en el móvil).

---

## Paso 1 — Publicar la app web en internet (gratis)

La app Android necesita que GlaciarSense esté publicada en una URL pública. Lo más sencillo es
**Streamlit Community Cloud**:

1. Crea un repositorio en GitHub y sube la carpeta `glaciar_app` (al menos `app.py`, `config.py`,
   `detector.py`, `gis_engine.py`, `glaciares_database.py`, `advanced_analysis.py`, `utils/`, `data/`,
   `sample_images/`, `.streamlit/` y `requirements.txt`). No hace falta subir `android_app/` ni `android_online/`.
2. Entra a <https://share.streamlit.io>, inicia sesión con GitHub y pulsa **Create app**.
3. Elige el repositorio, rama `main` y archivo principal `app.py`. En *Advanced settings* elige Python 3.12.
4. En *App URL* escribe, por ejemplo, `glaciar-sense` → quedará `https://glaciar-sense.streamlit.app`.
5. Pulsa **Deploy** y espera a que instale las dependencias (unos minutos la primera vez).

> Las apps gratuitas de Streamlit Cloud "se duermen" tras días sin uso; al abrirlas aparece un botón
> para despertarlas (tarda ~30 s). La app Android lo muestra igual que el navegador.

Otras opciones: Render, Railway o Hugging Face Spaces (plantilla Streamlit). También sirve tu PC en la
misma Wi-Fi: `http://192.168.1.16:8501` (configúralo desde el menú **Servidor…**).

## Paso 2 — Poner la URL en la app

Edita `app/build.gradle.kts`:

```kotlin
val glaciarSenseUrl = "https://glaciar-sense.streamlit.app"
```

(Si no la cambias, puedes escribirla después desde el menú ⋮ → **Servidor…** dentro de la app.)

## Paso 3 — Compilar el APK

Requisitos: **Android Studio** (Ladybug o más reciente), que incluye el SDK de Android y Java 17+.

1. Android Studio → **File › Open…** → elige `glaciar_app\android_online`.
2. Espera a que Gradle sincronice (descarga Gradle 8.11.1 y las librerías la primera vez).
3. Conecta el teléfono con *Depuración USB* activada y pulsa **Run ▶**, o genera el APK con
   **Build › Build App Bundle(s) / APK(s) › Build APK(s)**.
4. El APK queda en `app/build/outputs/apk/debug/app-debug.apk`. Cópialo al teléfono e instálalo
   (permite "instalar apps de origen desconocido").

Desde terminal (con el SDK instalado y `ANDROID_HOME` configurado):

```bash
gradlew.bat assembleDebug
```

## Detalles técnicos

| Elemento | Valor |
|---|---|
| Paquete | `com.glaciarsense.online` (se puede instalar junto a la app offline) |
| Android mínimo | 7.0 (API 24) · objetivo API 35 |
| Motor | `WebView` con JavaScript, DOM storage, cookies de terceros (iframe de Streamlit Cloud) |
| Permisos | Internet, cámara, ubicación; almacenamiento solo en Android 7–9 |
| Código | `MainActivity.kt` (WebView, cámara, GPS, errores) · `Downloads.kt` (descargas http y blob) |
