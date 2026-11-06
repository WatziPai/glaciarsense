package com.glaciarsense.app

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.glaciarsense.app.databinding.ActivityMainBinding
import com.glaciarsense.app.engine.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var currentGlacier: GlacierProfile = GlaciersDatabase.glaciers.first()
    private var activeBitmap: Bitmap? = null
    private var lastResult: GlacierDetectionResult? = null

    private val takePictureLauncher = registerForActivityResult(
        ActivityResultContracts.TakePicturePreview()
    ) { bitmap: Bitmap? ->
        bitmap?.let {
            activeBitmap = it
            binding.ivOriginal.setImageBitmap(it)
            processActiveImage()
        }
    }

    private val pickGalleryLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            try {
                val bitmap = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    ImageDecoder.decodeBitmap(ImageDecoder.createSource(contentResolver, it))
                } else {
                    @Suppress("DEPRECATION")
                    MediaStore.Images.Media.getBitmap(contentResolver, it)
                }
                activeBitmap = bitmap
                binding.ivOriginal.setImageBitmap(bitmap)
                processActiveImage()
            } catch (e: Exception) {
                Toast.makeText(this, "Error al cargar imagen: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupGlacierSpinner()
        setupListeners()
    }

    private fun setupGlacierSpinner() {
        val names = GlaciersDatabase.glaciers.map { "${it.name} (${it.country})" }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, names)
        binding.spinnerGlacier.adapter = adapter

        binding.spinnerGlacier.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                currentGlacier = GlaciersDatabase.glaciers[position]
                recalculateProjections()
            }

            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
        }
    }

    private fun setupListeners() {
        binding.btnCamera.setOnClickListener {
            takePictureLauncher.launch(null)
        }

        binding.btnGallery.setOnClickListener {
            pickGalleryLauncher.launch("image/*")
        }

        binding.sliderCarbon.addOnChangeListener { _, value, _ ->
            binding.tvSensCarbonLabel.text = String.format(Locale.US, "Sensibilidad Carbono Negro (%.1fx)", value)
            processActiveImage()
        }

        binding.sliderDust.addOnChangeListener { _, value, _ ->
            binding.tvSensDustLabel.text = String.format(Locale.US, "Sensibilidad Polvo Mineral (%.1fx)", value)
            processActiveImage()
        }

        binding.btnShare.setOnClickListener {
            shareReport()
        }
    }

    private fun processActiveImage() {
        val bitmap = activeBitmap ?: return

        binding.progressBar.visibility = View.VISIBLE

        val sensCarbon = binding.sliderCarbon.value
        val sensDust = binding.sliderDust.value

        lifecycleScope.launch(Dispatchers.Default) {
            val (result, annotated) = GlacierImageProcessor.processGlacierImage(
                originalBitmap = bitmap,
                ignoreTopPercent = 0f,
                autoSky = true,
                sensitivityCarbon = sensCarbon,
                sensitivityDust = sensDust,
                sensitivityWater = 1.0f
            )

            withContext(Dispatchers.Main) {
                binding.progressBar.visibility = View.GONE
                lastResult = result
                binding.ivAnnotated.setImageBitmap(annotated)
                displayResults(result)
            }
        }
    }

    private fun displayResults(res: GlacierDetectionResult) {
        val alb = res.albedo
        val pct = res.percentages

        // Métricas de albedo
        binding.tvAlbedo.text = String.format(Locale.US, "%.3f", alb.alphaEff)
        binding.tvAlbedoLoss.text = String.format(Locale.US, "Pérdida de reflectancia: -%.1f %%", alb.lossPct)
        binding.tvMeltAccel.text = String.format(Locale.US, "Aceleración de fusión Delta M: +%.1f %%", alb.meltAccelerationDeltaM * 100f)

        // Coberturas
        binding.tvCleanIce.text = String.format(Locale.US, "Hielo Limpio: %.1f %%", pct.cleanIce)
        binding.tvCarbon.text = String.format(Locale.US, "Carbono Negro: %.1f %%", pct.blackCarbon)
        binding.tvDust.text = String.format(Locale.US, "Polvo Mineral: %.1f %%", pct.mineralDust)
        binding.tvWater.text = String.format(Locale.US, "Lagunas / Deshielo: %.1f %%", pct.meltwater)

        val bioText = if (res.bioalbedoDetected) "Detectado (%.1f %%)".format(res.bioalbedoPercentage) else "No detectado"
        binding.tvAdvancedFeatures.text = "Grietas: ${res.crevasseCount} | Bioalbedo: $bioText | Rugosidad: ${String.format(Locale.US, "%.2f", res.roughnessIndex)}"

        recalculateProjections()
    }

    private fun recalculateProjections() {
        val res = lastResult ?: return
        val lifespan = GlaciologyEngine.computeLifespan(
            areaKm2 = currentGlacier.areaKm2,
            historicalRateKm2 = currentGlacier.retreatRateKm2,
            albedo = res.albedo,
            kCoef = 0.60f,
            bioalbedoDetected = res.bioalbedoDetected
        )

        binding.tvLifespanClean.text = String.format(
            Locale.US, "Proyección sin impurezas: %.1f años (área: %.2f km²)",
            lifespan.cleanYears, currentGlacier.areaKm2
        )
        binding.tvLifespanActual.text = String.format(
            Locale.US, "Con impurezas detectadas: %.1f años", lifespan.actualYears
        )
        binding.tvLifespanDelta.text = String.format(
            Locale.US, "Reducción de longevidad por impurezas: %.1f años menos", kotlin.math.abs(lifespan.deltaYears)
        )
    }

    private fun shareReport() {
        val res = lastResult
        if (res == null) {
            Toast.makeText(this, "Primero toma o carga una imagen para generar el reporte.", Toast.LENGTH_SHORT).show()
            return
        }

        val report = buildString {
            appendLine("=== INFORME CRIOSFÉRICO GLACIARSENSE ===")
            appendLine("Glaciar: ${currentGlacier.name} (${currentGlacier.country})")
            appendLine("Área base: ${currentGlacier.areaKm2} km² | Tasa: ${currentGlacier.retreatRateKm2} km²/año")
            appendLine("----------------------------------------")
            appendLine("Albedo efectivo (alpha_eff): ${String.format(Locale.US, "%.3f", res.albedo.alphaEff)}")
            appendLine("Pérdida de reflectancia: -${String.format(Locale.US, "%.1f", res.albedo.lossPct)} %")
            appendLine("Aceleración de fusión (Delta M): +${String.format(Locale.US, "%.1f", res.albedo.meltAccelerationDeltaM * 100f)} %")
            appendLine("----------------------------------------")
            appendLine("COBERTURAS DETECTADAS:")
            appendLine("- Hielo limpio: ${String.format(Locale.US, "%.1f", res.percentages.cleanIce)} %")
            appendLine("- Carbono negro: ${String.format(Locale.US, "%.1f", res.percentages.blackCarbon)} %")
            appendLine("- Polvo mineral: ${String.format(Locale.US, "%.1f", res.percentages.mineralDust)} %")
            appendLine("- Agua de deshielo: ${String.format(Locale.US, "%.1f", res.percentages.meltwater)} %")
            appendLine("Bioalbedo: ${if (res.bioalbedoDetected) "Detectado (${res.bioalbedoPercentage}%)" else "No detectado"}")
            appendLine("Grietas detectadas: ${res.crevasseCount}")
            appendLine("Confianza radiométrica: ${String.format(Locale.US, "%.0f", res.confidence * 100f)} %")
            appendLine("========================================")
        }

        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "Reporte GlaciarSense - ${currentGlacier.name}")
            putExtra(Intent.EXTRA_TEXT, report)
        }
        startActivity(Intent.createChooser(shareIntent, "Compartir informe vía"))
    }
}

