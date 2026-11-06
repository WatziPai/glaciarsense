package com.glaciarsense.online

import android.app.DownloadManager
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Base64
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.URLUtil
import android.widget.Toast
import java.io.File

/** Guarda archivos (PDF, CSV, GeoJSON…) que la app web ofrece para descargar. */
object Downloads {

    /** Descarga http(s) normal mediante el DownloadManager del sistema (con las cookies de la sesión). */
    fun enqueue(context: Context, url: String, userAgent: String, contentDisposition: String?, mimeType: String?) {
        val fileName = URLUtil.guessFileName(url, contentDisposition, mimeType)
        try {
            val request = DownloadManager.Request(Uri.parse(url)).apply {
                setMimeType(mimeType)
                CookieManager.getInstance().getCookie(url)?.let { addRequestHeader("Cookie", it) }
                addRequestHeader("User-Agent", userAgent)
                setTitle(fileName)
                setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName)
            }
            val dm = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            dm.enqueue(request)
            toast(context, context.getString(R.string.downloading, fileName))
        } catch (e: Exception) {
            toast(context, context.getString(R.string.download_failed))
        }
    }

    /** Guarda bytes ya descargados (descargas "blob:" o "data:") en la carpeta Descargas. */
    fun saveBytes(context: Context, fileName: String, mimeType: String, bytes: ByteArray): Boolean = try {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                put(MediaStore.Downloads.MIME_TYPE, mimeType)
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: error("No se pudo crear el archivo")
            resolver.openOutputStream(uri)?.use { it.write(bytes) }
            values.clear()
            values.put(MediaStore.Downloads.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        } else {
            @Suppress("DEPRECATION")
            val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
            dir.mkdirs()
            File(dir, fileName).writeBytes(bytes)
        }
        true
    } catch (e: Exception) {
        false
    }

    fun toast(context: Context, msg: String) =
        Toast.makeText(context, msg, Toast.LENGTH_LONG).show()

    /**
     * JavaScript que lee un blob: URL dentro de la página y lo envía a [BlobDownloader] en base64.
     * Se ejecuta en el mismo origen que creó el blob.
     */
    fun blobFetchScript(blobUrl: String, fileName: String, mimeType: String): String {
        fun q(s: String) = "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"
        return """
            (function() {
              fetch(${q(blobUrl)}).then(function(r) { return r.blob(); }).then(function(b) {
                var reader = new FileReader();
                reader.onloadend = function() {
                  var data = String(reader.result);
                  AndroidDownloader.save(data.substring(data.indexOf(',') + 1), ${q(fileName)}, b.type || ${q(mimeType)});
                };
                reader.readAsDataURL(b);
              }).catch(function(e) { AndroidDownloader.fail(String(e)); });
            })();
        """.trimIndent()
    }
}

/** Puente JS → Android para descargas blob:. Expuesto como `AndroidDownloader`. */
class BlobDownloader(private val activity: MainActivity) {

    @JavascriptInterface
    fun save(base64: String, fileName: String, mimeType: String) {
        val ok = try {
            Downloads.saveBytes(activity, fileName, mimeType, Base64.decode(base64, Base64.DEFAULT))
        } catch (e: Exception) {
            false
        }
        activity.runOnUiThread {
            Downloads.toast(
                activity,
                if (ok) activity.getString(R.string.saved_to_downloads, fileName)
                else activity.getString(R.string.download_failed)
            )
        }
    }

    @JavascriptInterface
    fun fail(@Suppress("UNUSED_PARAMETER") reason: String) {
        activity.runOnUiThread { Downloads.toast(activity, activity.getString(R.string.download_failed)) }
    }
}
