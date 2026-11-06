package com.glaciarsense.app.engine

data class CoveragePercentages(
    val cleanIce: Float,
    val blackCarbon: Float,
    val mineralDust: Float,
    val meltwater: Float
)

data class AlbedoSummary(
    val alphaEff: Float,
    val alphaClean: Float,
    val lossAbs: Float,
    val lossPct: Float,
    val meltAccelerationDeltaM: Float
)

data class SpectralIndices(
    val ndvi: Float,
    val ndwi: Float,
    val ndsi: Float
)

data class GlacierDetectionResult(
    val percentages: CoveragePercentages,
    val albedo: AlbedoSummary,
    val confidence: Float,
    val warnings: List<String>,
    val bioalbedoDetected: Boolean,
    val bioalbedoPercentage: Float,
    val crevasseCount: Int,
    val roughnessIndex: Float,
    val spectralIndices: SpectralIndices,
    val spatialDistribution: Map<String, Float>
)

data class LifespanProjection(
    val cleanYears: Float,
    val actualYears: Float,
    val bioYears: Float,
    val deltaYears: Float,
    val ablationRateCleanKm2: Float,
    val ablationRateActualKm2: Float
)

data class GlacierProfile(
    val name: String,
    val country: String,
    val lat: Double,
    val lon: Double,
    val areaKm2: Float,
    val retreatRateKm2: Float,
    val type: String,
    val source: String
)

