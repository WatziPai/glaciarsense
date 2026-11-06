package com.glaciarsense.online

import android.Manifest
import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.view.View
import android.webkit.CookieManager
import android.webkit.GeolocationPermissions
import android.webkit.MimeTypeMap
import android.webkit.PermissionRequest
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.FrameLayout
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.glaciarsense.online.databinding.ActivityMainBinding
import java.io.File

/**
 * GlaciarSense Online: cliente Android de la app web (Streamlit) publicada en internet.
 * Toda la segmentación, mapas, informes PDF, etc. se ejecutan en el servidor;
 * el teléfono aporta cámara, galería, GPS y la carpeta de Descargas.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val web get() = binding.webview

    private val prefs by lazy { getSharedPreferences("glaciarsense", Context.MODE_PRIVATE) }
    private var serverUrl: String
        get() = prefs.getString(KEY_SERVER, null) ?: BuildConfig.DEFAULT_SERVER_URL
        set(value) = prefs.edit().putString(KEY_SERVER, value).apply()

    // Estado de selector de archivos (subir foto del glaciar)
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private var pendingChooserParams: WebChromeClient.FileChooserParams? = null
    private var cameraPhotoUri: Uri? = null

    // Permisos pendientes
    private var pendingGeo: Pair<String, GeolocationPermissions.Callback>? = null
    private var pendingWebPermission: PermissionRequest? = null
    private var pendingStorageAction: (() -> Unit)? = null
    private var mainFrameFailed = false

    // ─── Lanzadores de resultados ───────────────────────────────────────

    private val fileChooserLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val callback = filePathCallback ?: return@registerForActivityResult
            filePathCallback = null
            var uris: Array<Uri>? = null
            if (result.resultCode == RESULT_OK) {
                val data = result.data
                val clip = data?.clipData
                uris = when {
                    clip != null && clip.itemCount > 0 -> Array(clip.itemCount) { clip.getItemAt(it).uri }
                    data?.data != null -> arrayOf(data.data!!)
                    else -> cameraPhotoUri?.takeIf { cameraFileHasData() }?.let { arrayOf(it) }
                }
            }
            callback.onReceiveValue(uris)
            cameraPhotoUri = null
        }

    private val cameraPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            val params = pendingChooserParams
            pendingChooserParams = null
            if (params != null) launchFileChooser(params, withCamera = granted)
        }

    private val locationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { res ->
            val granted = res.values.any { it }
            pendingGeo?.let { (origin, cb) -> cb.invoke(origin, granted, false) }
            pendingGeo = null
        }

    private val webMediaPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            pendingWebPermission?.let { req ->
                if (granted) req.grant(arrayOf(PermissionRequest.RESOURCE_VIDEO_CAPTURE)) else req.deny()
            }
            pendingWebPermission = null
        }

    private val storagePermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) pendingStorageAction?.invoke()
            else Downloads.toast(this, getString(R.string.storage_permission_needed))
            pendingStorageAction = null
        }

    // ─── Ciclo de vida ──────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupToolbar()
        setupWebView()

        binding.retryButton.setOnClickListener { loadServer() }
        binding.serverButton.setOnClickListener { showServerDialog() }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (binding.errorView.visibility != View.VISIBLE && web.canGoBack()) {
                    web.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })

        if (savedInstanceState != null && web.restoreState(savedInstanceState) != null) {
            // Sesión restaurada (p. ej. tras volver de la cámara con poca memoria)
        } else {
            loadServer()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    override fun onResume() {
        super.onResume()
        web.onResume()
    }

    override fun onPause() {
        web.onPause()
        CookieManager.getInstance().flush()
        super.onPause()
    }

    override fun onDestroy() {
        (web.parent as? FrameLayout)?.removeView(web)
        web.destroy()
        super.onDestroy()
    }

    // ─── UI ─────────────────────────────────────────────────────────────

    private fun setupToolbar() {
        binding.toolbar.inflateMenu(R.menu.main_menu)
        binding.toolbar.subtitle = Uri.parse(serverUrl).host ?: getString(R.string.toolbar_subtitle)
        binding.toolbar.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                R.id.action_reload -> { loadServer(); true }
                R.id.action_browser -> { openExternal(web.url ?: serverUrl); true }
                R.id.action_server -> { showServerDialog(); true }
                else -> false
            }
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        web.settings.apply {
            javaScriptEnabled = true          // Streamlit es una app React: imprescindible
            domStorageEnabled = true          // estado de sesión de Streamlit
            @Suppress("DEPRECATION")
            databaseEnabled = true
            setGeolocationEnabled(true)       // ubicación en el mapa
            mediaPlaybackRequiresUserGesture = false
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = true
            displayZoomControls = false
            allowFileAccess = false
            allowContentAccess = true
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            cacheMode = WebSettings.LOAD_DEFAULT
            userAgentString = "$userAgentString GlaciarSenseAndroid/${BuildConfig.VERSION_NAME}"
        }
        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(web, true)   // Streamlit Cloud sirve la app dentro de un iframe
        }

        web.addJavascriptInterface(BlobDownloader(this), "AndroidDownloader")
        web.webViewClient = GlaciarWebViewClient()
        web.webChromeClient = GlaciarChromeClient()
        web.setDownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
            handleDownload(url, userAgent, contentDisposition, mimeType)
        }
    }

    private fun loadServer() {
        mainFrameFailed = false
        if (!isOnline()) {
            showError(getString(R.string.error_no_internet))
            return
        }
        hideError()
        val current = web.url
        if (current != null && current.startsWith("http") && sameSite(current)) web.reload()
        else web.loadUrl(serverUrl)
    }

    private fun showError(message: String) {
        binding.errorMessage.text = message
        binding.errorView.visibility = View.VISIBLE
        binding.progress.visibility = View.GONE
    }

    private fun hideError() {
        binding.errorView.visibility = View.GONE
    }

    private fun showServerDialog() {
        val input = EditText(this).apply {
            setText(serverUrl)
            hint = getString(R.string.server_hint)
            setSingleLine()
            inputType = android.text.InputType.TYPE_TEXT_VARIATION_URI
        }
        val pad = (20 * resources.displayMetrics.density).toInt()
        val container = FrameLayout(this).apply {
            setPadding(pad, pad / 2, pad, 0)
            addView(input)
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.server_title)
            .setMessage(R.string.server_help)
            .setView(container)
            .setPositiveButton(R.string.save) { _, _ ->
                var url = input.text.toString().trim()
                if (url.isNotEmpty() && !url.startsWith("http://") && !url.startsWith("https://")) {
                    url = "https://$url"
                }
                if (URLUtil.isNetworkUrl(url) && Uri.parse(url).host != null) {
                    serverUrl = url
                    applyNewServer()
                } else {
                    Downloads.toast(this, getString(R.string.invalid_url))
                }
            }
            .setNeutralButton(R.string.restore_default) { _, _ ->
                prefs.edit().remove(KEY_SERVER).apply()
                applyNewServer()
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }

    private fun applyNewServer() {
        binding.toolbar.subtitle = Uri.parse(serverUrl).host
        web.clearHistory()
        web.loadUrl("about:blank")
        mainFrameFailed = false
        if (isOnline()) {
            hideError()
            web.loadUrl(serverUrl)
        } else {
            showError(getString(R.string.error_no_internet))
        }
    }

    // ─── Utilidades ─────────────────────────────────────────────────────

    private fun isOnline(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    /** ¿La URL pertenece al servidor de GlaciarSense (o a la infraestructura de Streamlit Cloud)? */
    private fun sameSite(url: String): Boolean {
        val host = Uri.parse(url).host ?: return false
        val serverHost = Uri.parse(serverUrl).host ?: return false
        return host == serverHost ||
            host.endsWith(".streamlit.app") || host == "streamlit.app" ||
            host.endsWith(".streamlit.io") || host == "streamlit.io"
    }

    private fun openExternal(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
        }
    }

    private fun granted(permission: String) =
        ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

    private fun needsLegacyStoragePermission() =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
            !granted(Manifest.permission.WRITE_EXTERNAL_STORAGE)

    private fun withStoragePermission(action: () -> Unit) {
        if (needsLegacyStoragePermission()) {
            pendingStorageAction = action
            storagePermissionLauncher.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        } else {
            action()
        }
    }

    // ─── Descargas (PDF, CSV, PNG, ZIP, GeoJSON) ────────────────────────

    private fun handleDownload(url: String, userAgent: String, contentDisposition: String?, mimeType: String?) {
        val mime = mimeType?.takeIf { it.isNotBlank() } ?: "application/octet-stream"
        when {
            url.startsWith("blob:") -> {
                val name = URLUtil.guessFileName(url, contentDisposition, mime)
                    .let { if (it.endsWith(".bin")) defaultName(mime) else it }
                withStoragePermission {
                    web.evaluateJavascript(Downloads.blobFetchScript(url, name, mime), null)
                }
            }
            url.startsWith("data:") -> withStoragePermission {
                val comma = url.indexOf(',')
                val bytes = android.util.Base64.decode(url.substring(comma + 1), android.util.Base64.DEFAULT)
                val name = defaultName(mime)
                val ok = Downloads.saveBytes(this, name, mime, bytes)
                Downloads.toast(this,
                    if (ok) getString(R.string.saved_to_downloads, name) else getString(R.string.download_failed))
            }
            else -> withStoragePermission {
                Downloads.enqueue(this, url, userAgent, contentDisposition, mime)
            }
        }
    }

    private fun defaultName(mime: String): String {
        val ext = MimeTypeMap.getSingleton().getExtensionFromMimeType(mime) ?: "bin"
        return "glaciarsense_${System.currentTimeMillis()}.$ext"
    }

    // ─── Selector de archivos: cámara + galería ─────────────────────────

    private fun launchFileChooser(params: WebChromeClient.FileChooserParams, withCamera: Boolean) {
        val mimeTypes = params.acceptTypes
            .flatMap { it.split(',') }
            .map { it.trim().lowercase() }
            .filter { it.isNotEmpty() }
            .mapNotNull { type ->
                when {
                    type.contains('/') -> type
                    else -> MimeTypeMap.getSingleton().getMimeTypeFromExtension(type.removePrefix("."))
                }
            }
            .distinct()
        val acceptsImages = mimeTypes.isEmpty() || mimeTypes.any { it.startsWith("image") }

        val contentIntent = Intent(Intent.ACTION_GET_CONTENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            when {
                mimeTypes.isEmpty() -> type = "*/*"
                mimeTypes.size == 1 -> type = mimeTypes.first()
                else -> {
                    type = if (mimeTypes.all { it.startsWith("image/") }) "image/*" else "*/*"
                    putExtra(Intent.EXTRA_MIME_TYPES, mimeTypes.toTypedArray())
                }
            }
            if (params.mode == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE) {
                putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
            }
        }

        val extraIntents = mutableListOf<Intent>()
        if (withCamera && acceptsImages) createCameraIntent()?.let { extraIntents += it }

        val chooser = Intent.createChooser(contentIntent, getString(R.string.pick_image)).apply {
            if (extraIntents.isNotEmpty()) putExtra(Intent.EXTRA_INITIAL_INTENTS, extraIntents.toTypedArray())
        }
        try {
            fileChooserLauncher.launch(chooser)
        } catch (_: ActivityNotFoundException) {
            filePathCallback?.onReceiveValue(null)
            filePathCallback = null
        }
    }

    private fun createCameraIntent(): Intent? {
        val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        if (intent.resolveActivity(packageManager) == null &&
            !packageManager.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)
        ) return null
        return try {
            val dir = File(cacheDir, "camera").apply { mkdirs() }
            dir.listFiles()?.forEach { it.delete() }   // limpiar fotos de sesiones anteriores
            val photo = File(dir, "glaciar_${System.currentTimeMillis()}.jpg")
            val uri = FileProvider.getUriForFile(this, "$packageName.fileprovider", photo)
            cameraPhotoUri = uri
            intent.apply {
                putExtra(MediaStore.EXTRA_OUTPUT, uri)
                addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION or Intent.FLAG_GRANT_READ_URI_PERMISSION)
                clipData = ClipData.newRawUri("", uri)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun cameraFileHasData(): Boolean {
        val dir = File(cacheDir, "camera")
        return dir.listFiles()?.any { it.length() > 0 } == true
    }

    // ─── Clientes del WebView ───────────────────────────────────────────

    private inner class GlaciarWebViewClient : WebViewClient() {

        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
            val url = request.url.toString()
            return when {
                url.startsWith("http://") || url.startsWith("https://") -> {
                    // Enlaces a otras webs (referencias, WGMS, papers…) se abren en el navegador
                    if (request.isForMainFrame && !sameSite(url)) { openExternal(url); true } else false
                }
                url.startsWith("about:") || url.startsWith("blob:") || url.startsWith("data:") -> false
                else -> { openExternal(url); true }   // mailto:, tel:, intent:, geo:…
            }
        }

        override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
            binding.progress.visibility = View.VISIBLE
        }

        override fun onPageFinished(view: WebView, url: String?) {
            binding.progress.visibility = View.GONE
            if (!mainFrameFailed && url != "about:blank") hideError()
        }

        override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
            if (request.isForMainFrame) {
                mainFrameFailed = true
                showError(
                    if (!isOnline()) getString(R.string.error_no_internet)
                    else getString(R.string.error_server, "${serverUrl}\n(${error.description})")
                )
            }
        }
    }

    private inner class GlaciarChromeClient : WebChromeClient() {

        override fun onProgressChanged(view: WebView, newProgress: Int) {
            binding.progress.setProgressCompat(newProgress, true)
            binding.progress.visibility = if (newProgress < 100) View.VISIBLE else View.GONE
        }

        override fun onShowFileChooser(
            webView: WebView,
            callback: ValueCallback<Array<Uri>>,
            params: FileChooserParams
        ): Boolean {
            filePathCallback?.onReceiveValue(null)
            filePathCallback = callback
            val hasCamera = packageManager.hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)
            if (hasCamera && !granted(Manifest.permission.CAMERA)) {
                pendingChooserParams = params
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            } else {
                launchFileChooser(params, withCamera = hasCamera)
            }
            return true
        }

        override fun onGeolocationPermissionsShowPrompt(
            origin: String,
            callback: GeolocationPermissions.Callback
        ) {
            if (granted(Manifest.permission.ACCESS_FINE_LOCATION) ||
                granted(Manifest.permission.ACCESS_COARSE_LOCATION)
            ) {
                callback.invoke(origin, true, false)
            } else {
                pendingGeo = origin to callback
                locationPermissionLauncher.launch(
                    arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
                )
            }
        }

        override fun onPermissionRequest(request: PermissionRequest) {
            // Solo la cámara (p. ej. si la web usa st.camera_input); el resto se deniega.
            if (request.resources.contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE)) {
                if (granted(Manifest.permission.CAMERA)) {
                    request.grant(arrayOf(PermissionRequest.RESOURCE_VIDEO_CAPTURE))
                } else {
                    pendingWebPermission = request
                    webMediaPermissionLauncher.launch(Manifest.permission.CAMERA)
                }
            } else {
                request.deny()
            }
        }
    }

    companion object {
        private const val KEY_SERVER = "server_url"
    }
}
