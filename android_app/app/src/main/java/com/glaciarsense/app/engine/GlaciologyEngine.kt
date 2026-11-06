package com.glaciarsense.app.engine

import kotlin.math.max
import kotlin.math.min

object GlaciologyEngine {

    // Albedos de referencia según literatura glaciológica (Warren & Wiscombe 1980, Painter et al. 2001)
    const val ALBEDO_CLEAN_ICE = 0.55f
    const val ALBEDO_BLACK_CARBON = 0.12f
    const val ALBEDO_MINERAL_DUST = 0.28f
    const val ALBEDO_MELTWATER = 0.22f

    fun computeAlbedo(pct: CoveragePercentages): AlbedoSummary {
        val fClean = pct.cleanIce / 100.0f
        val fCarbon = pct.blackCarbon / 100.0f
        val fDust = pct.mineralDust / 100.0f
        val fWater = pct.meltwater / 100.0f

        val alphaEff = (fClean * ALBEDO_CLEAN_ICE) +
                (fCarbon * ALBEDO_BLACK_CARBON) +
                (fDust * ALBEDO_MINERAL_DUST) +
                (fWater * ALBEDO_MELTWATER)

        val lossAbs = max(0.0f, ALBEDO_CLEAN_ICE - alphaEff)
        val lossPct = if (ALBEDO_CLEAN_ICE > 0f) (lossAbs / ALBEDO_CLEAN_ICE) * 100f else 0f

        // Aceleración de deshielo Delta M: max( (1 - alpha_eff)/(1 - alpha_clean) - 1, 0 )
        val deltaM = max(0.0f, ((1.0f - alphaEff) / (1.0f - ALBEDO_CLEAN_ICE)) - 1.0f)

        return AlbedoSummary(
            alphaEff = alphaEff,
            alphaClean = ALBEDO_CLEAN_ICE,
            lossAbs = lossAbs,
            lossPct = lossPct,
            meltAccelerationDeltaM = deltaM
        )
    }

    fun computeLifespan(
        areaKm2: Float,
        historicalRateKm2: Float,
        albedo: AlbedoSummary,
        kCoef: Float = 0.60f,
        bioalbedoDetected: Boolean = false
    ): LifespanProjection {
        if (historicalRateKm2 <= 0f || areaKm2 <= 0f) {
            return LifespanProjection(0f, 0f, 0f, 0f, 0f, 0f)
        }

        // Tasa limpia: sin impurezas
        val rateClean = historicalRateKm2

        // Factor de contaminantes: clip(k * Delta M, 0, 1.5)
        val factorContaminante = min(1.5f, max(0.0f, kCoef * albedo.meltAccelerationDeltaM))
        val rateActual = historicalRateKm2 * (1.0f + factorContaminante)

        val cleanYears = areaKm2 / rateClean
        val actualYears = areaKm2 / rateActual

        val rateBio = if (bioalbedoDetected) rateActual * 1.20f else rateActual
        val bioYears = areaKm2 / rateBio

        val deltaYears = actualYears - cleanYears

        return LifespanProjection(
            cleanYears = cleanYears,
            actualYears = actualYears,
            bioYears = bioYears,
            deltaYears = deltaYears,
            ablationRateCleanKm2 = rateClean,
            ablationRateActualKm2 = rateActual
        )
    }
}

