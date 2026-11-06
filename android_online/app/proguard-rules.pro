# Mantener la interfaz JavaScript usada para descargas blob:
-keepclassmembers class com.glaciarsense.online.BlobDownloader {
    @android.webkit.JavascriptInterface <methods>;
}
