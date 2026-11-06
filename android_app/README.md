# GlaciarSense Mobile (Android 100% Offline)

Versión nativa para Android de **GlaciarSense v2.2**, diseñada específicamente para trabajo de campo glaciológico en alta montaña (sin señal celular ni conexión a internet).

---

## 🏔️ Características Principales

1. **Procesamiento On-Device (Sin Internet ni Servidores):**
   - Algoritmo de segmentación radiométrica adaptado a procesadores móviles ARM (Cortex/Snapdragon).
   - Conversión de espacio de color RGB a CIE $L^*$ y HSV en memoria (<150 ms por captura).
   - Detección de cielo automática para excluir la atmósfera de alta montaña.
   - Detección de grietas superficiales (filtro de gradiente tipo Sobel/Canny).
   - Detección de bioalbedo (colonias de algas y crioconita con absorción en longitudes de onda cortas).

2. **Cálculo Glaciológico en Tiempo Real:**
   - **Albedo Efectivo:** $\alpha_{ef} = \sum f_i \cdot \alpha_i$
   - **Aceleración de Fusión:** $\Delta M = \max\left(\frac{1 - \alpha_{ef}}{1 - \alpha_{limpio}} - 1,\; 0\right)$
   - **Tasa de Ablación Ajustada:** $Tasa_{adj} = Tasa_{hist} \times \left(1 + \mathrm{clip}(k \cdot \Delta M,\; 0,\; 1.5)\right)$
   - **Proyección de Longevidad Glaciar:** Estimación comparativa (glaciar limpio vs. con impurezas detectadas en la foto).

3. **Base de Datos Andina Offline Embebida:**
   - Perfiles preconfigurados de 10 glaciares monitoreados (Quelccaya, Pastoruri, Coropuna, Huascarán, Chacaltaya, Zongo, Antisana, Ritacuba Blanco, Martial, Echaurren Norte).

4. **Captura Directa con la Cámara del Móvil:**
   - Permite tomar fotos directamente durante la expedición o cargar fotos tomadas previamente desde la galería del dispositivo.
   - Ajustes interactivos de sensibilidad para carbono negro y polvo mineral.

---

## 🛠️ Requisitos y Compilación

### Requisitos del Sistema
- **Android:** Versión 7.0 (Nougat, API 24) o superior.
- **Entorno de desarrollo:** Android Studio (Hedgehog, Iguana, Jellyfish o Ladybug).
- **JDK:** Java 17 o Java 21 (OpenJDK).

### Pasos para Abrir y Compilar en Android Studio
1. Abre **Android Studio**.
2. Selecciona **File > Open...** y elige la carpeta:
   ```
   c:\Users\MANUEL\Downloads\glaciar_app\android_app
   ```
3. Espera a que Gradle sincronice las dependencias del proyecto.
4. Conecta tu teléfono Android por USB (con la depuración USB activada) o inicia un emulador.
5. Presiona el botón verde **Run (Shift + F10)** o compila el archivo APK mediante el menú:
   - **Build > Build Bundle(s) / APK(s) > Build APK(s)**
6. El archivo APK resultante se generará en:
   ```
   app/build/outputs/apk/debug/app-debug.apk
   ```

---

## 📲 Probar de Inmediato en tu Teléfono Android (Por Red WiFi Local)

Si deseas probar la aplicación completa con tu teléfono Android **ahora mismo sin esperar la compilación**:

1. Asegúrate de que tu celular Android esté conectado a la **misma red Wi-Fi** que tu computadora.
2. Abre el navegador Google Chrome en tu teléfono.
3. Ingresa la dirección IP local del servidor:
   ```
   http://192.168.1.16:8501
   ```
4. Podrás usar la cámara de tu teléfono, subir fotos de glaciares, ajustar los deslizadores de sensibilidad y ver los mapas interactivos con geolocalización.

