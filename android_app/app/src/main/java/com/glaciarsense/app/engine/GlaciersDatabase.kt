package com.glaciarsense.app.engine

object GlaciersDatabase {

    val glaciers: List<GlacierProfile> = listOf(
        GlacierProfile(
            name = "Quelccaya (Capa de Hielo)",
            country = "Perú",
            lat = -13.9300,
            lon = -70.8300,
            areaKm2 = 42.8f,
            retreatRateKm2 = 0.550f,
            type = "Capa de hielo tropical",
            source = "Thompson et al. / INAIGEM"
        ),
        GlacierProfile(
            name = "Pastoruri (Cordillera Blanca)",
            country = "Perú",
            lat = -9.9286,
            lon = -77.1983,
            areaKm2 = 0.85f,
            retreatRateKm2 = 0.052f,
            type = "Glaciar de valle relicto",
            source = "INAIGEM Inventario Nacional"
        ),
        GlacierProfile(
            name = "Coropuna (Complejo Volcánico)",
            country = "Perú",
            lat = -15.5167,
            lon = -72.6500,
            areaKm2 = 44.1f,
            retreatRateKm2 = 0.410f,
            type = "Casquete volcánico",
            source = "UGR / INAIGEM"
        ),
        GlacierProfile(
            name = "Huascarán Norte y Sur",
            country = "Perú",
            lat = -9.1233,
            lon = -77.6044,
            areaKm2 = 14.2f,
            retreatRateKm2 = 0.180f,
            type = "Glaciar de alta montaña",
            source = "INAIGEM"
        ),
        GlacierProfile(
            name = "Chacaltaya (Relicto)",
            country = "Bolivia",
            lat = -16.3500,
            lon = -68.1300,
            areaKm2 = 0.01f,
            retreatRateKm2 = 0.015f,
            type = "Glaciar casi extinto (2009)",
            source = "Francou et al. / IRD"
        ),
        GlacierProfile(
            name = "Zongo (Cordillera Real)",
            country = "Bolivia",
            lat = -16.2500,
            lon = -68.1667,
            areaKm2 = 1.9f,
            retreatRateKm2 = 0.040f,
            type = "Glaciar de valle monitoreado",
            source = "GLACIOCLIM / IRD"
        ),
        GlacierProfile(
            name = "Antisana 15 (Volcán)",
            country = "Ecuador",
            lat = -0.4810,
            lon = -78.1470,
            areaKm2 = 1.4f,
            retreatRateKm2 = 0.035f,
            type = "Glaciar estratovolcánico",
            source = "INAMHI / IRD"
        ),
        GlacierProfile(
            name = "Ritacuba Blanco (Sierra Nevada del Cocuy)",
            country = "Colombia",
            lat = 6.4950,
            lon = -72.2930,
            areaKm2 = 1.6f,
            retreatRateKm2 = 0.045f,
            type = "Casquete de cumbre",
            source = "IDEAM Colombia"
        ),
        GlacierProfile(
            name = "Martial (Tierra del Fuego)",
            country = "Argentina",
            lat = -54.7900,
            lon = -68.3900,
            areaKm2 = 0.28f,
            retreatRateKm2 = 0.008f,
            type = "Glaciar de circo subantártico",
            source = "IANIGLA-CONICET"
        ),
        GlacierProfile(
            name = "Echaurren Norte (Andes Centrales)",
            country = "Chile",
            lat = -33.5833,
            lon = -70.1333,
            areaKm2 = 0.19f,
            retreatRateKm2 = 0.012f,
            type = "Glaciar de referencia WGMS",
            source = "DGA Chile / WGMS"
        )
    )

    fun getByName(name: String): GlacierProfile {
        return glaciers.find { it.name == name } ?: glaciers.first()
    }
}

