plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// ─────────────────────────────────────────────────────────────
// URL pública donde está publicada GlaciarSense (Streamlit).
// Cámbiala aquí antes de compilar, o desde la app: menú ⋮ > "Servidor".
// ─────────────────────────────────────────────────────────────
val glaciarSenseUrl = "https://glaciarsense.streamlit.app"

android {
    namespace = "com.glaciarsense.online"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.glaciarsense.online"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "2.2.0-online"
        buildConfigField("String", "DEFAULT_SERVER_URL", "\"$glaciarSenseUrl\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // Firma con la clave debug para poder instalar el APK release sin configurar keystore.
            // Para publicar en Google Play, crea tu propia clave de firma.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        buildConfig = true
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.webkit:webkit:1.12.1")
}
