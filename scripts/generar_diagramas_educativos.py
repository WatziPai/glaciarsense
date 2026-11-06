"""
scripts/generar_diagramas_educativos.py
========================================
Script para generar visualizaciones educativas del módulo de Conocimiento Glaciar.

Genera diagramas explicativos de:
- Topografía basal y sobreexcavaciones
- Retroalimentación albedo-temperatura
- Sistema hidrológico subglacial
- Ciclo del bioalbedo

Uso:
    python scripts/generar_diagramas_educativos.py
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon as MplPolygon
import numpy as np
from pathlib import Path

# Configuración de estilo
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10

OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "diagramas"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def diagrama_topografia_basal():
    """Genera diagrama de perfil glaciar con sobreexcavación."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Coordenadas del perfil
    x = np.linspace(0, 100, 200)
    
    # Lecho rocoso con sobreexcavación
    lecho = 20 - 0.15 * x + 0.002 * x**2
    lecho[40:70] -= 15 * np.exp(-((x[40:70] - 55)**2) / 50)  # Cubeta profunda
    
    # Superficie del hielo (parabólica)
    superficie = 80 - 0.8 * x + 0.008 * x**2
    
    # Dibujar
    ax.fill_between(x, lecho, -20, color='#8B4513', alpha=0.7, label='Lecho rocoso')
    ax.fill_between(x, lecho, superficie, color='#B0E0E6', alpha=0.6, label='Hielo glaciar')
    ax.plot(x, superficie, 'b-', linewidth=2, label='Superficie')
    ax.plot(x, lecho, 'k-', linewidth=2)
    
    # Marcar sobreexcavación
    ax.annotate('Sobreexcavación\n(Overdeepening)', 
                xy=(55, lecho[110]), xytext=(55, -10),
                arrowprops=dict(arrowstyle='->', lw=2, color='red'),
                fontsize=12, ha='center', color='red', weight='bold')
    
    # Marcar zona de riesgo GLOF
    ax.add_patch(mpatches.Ellipse((55, 10), 20, 25, 
                                   color='red', alpha=0.2, 
                                   label='Zona de riesgo\nlago proglaciar'))
    
    # Nivel del mar / datum
    ax.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.text(2, 2, 'Nivel de referencia', fontsize=9, color='gray')
    
    # Configuración
    ax.set_xlim(0, 100)
    ax.set_ylim(-20, 90)
    ax.set_xlabel('Distancia horizontal (unidades relativas)', fontsize=12)
    ax.set_ylabel('Elevación (unidades relativas)', fontsize=12)
    ax.set_title('Perfil Glaciar con Topografía Basal Compleja', fontsize=14, weight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'topografia_basal.png', dpi=300, bbox_inches='tight')
    print(f"✓ Generado: {OUTPUT_DIR / 'topografia_basal.png'}")
    plt.close()


def diagrama_retroalimentacion_albedo():
    """Diagrama de flujo: retroalimentación albedo-temperatura."""
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Nodos del ciclo
    nodos = [
        (5, 8.5, '↑ Temperatura'),
        (2, 6, '↑ Fusión superficial'),
        (2, 3, '↓ Albedo\n(oscurecimiento)'),
        (5, 1, '↑ Absorción solar'),
        (8, 3, '↑ Energía térmica'),
        (8, 6, '↑ Tasa de fusión'),
    ]
    
    # Dibujar nodos
    for x, y, texto in nodos:
        bbox = FancyBboxPatch((x-0.8, y-0.4), 1.6, 0.8,
                               boxstyle="round,pad=0.1", 
                               facecolor='lightblue', 
                               edgecolor='navy', linewidth=2)
        ax.add_patch(bbox)
        ax.text(x, y, texto, ha='center', va='center', 
                fontsize=11, weight='bold')
    
    # Flechas de conexión
    flechas = [
        ((5, 8.1), (2.5, 6.5)),
        ((2, 5.6), (2, 3.8)),
        ((2.5, 2.5), (4.5, 1.3)),
        ((5.5, 1.3), (7.5, 2.5)),
        ((8, 3.4), (8, 5.6)),
        ((7.5, 6.5), (5.5, 8.1)),
    ]
    
    for (x1, y1), (x2, y2) in flechas:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=3, color='red'))
    
    # Título central
    ax.text(5, 9.5, 'Retroalimentación Albedo-Temperatura', 
            ha='center', fontsize=14, weight='bold')
    
    # Nota explicativa
    ax.text(5, 0.2, 'Ciclo autosostenido de aceleración térmica glaciar', 
            ha='center', fontsize=10, style='italic', color='gray')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'retroalimentacion_albedo.png', dpi=300, bbox_inches='tight')
    print(f"✓ Generado: {OUTPUT_DIR / 'retroalimentacion_albedo.png'}")
    plt.close()


def diagrama_sistema_subglacial():
    """Esquema del sistema hidrológico subglacial."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Perfil simplificado
    x = np.linspace(0, 100, 200)
    superficie = 60 - 0.5 * x + 0.005 * x**2
    lecho = 20 - 0.2 * x
    
    # Dibujar glaciar
    ax.fill_between(x, lecho, superficie, color='#ADD8E6', alpha=0.6)
    ax.plot(x, superficie, 'b-', linewidth=2)
    ax.plot(x, lecho, 'k-', linewidth=2)
    
    # Grietas (crevasses)
    for xc in [15, 25, 40, 55, 70]:
        yc = superficie[int(xc*2)]
        ax.plot([xc, xc], [yc, yc-8], 'b-', linewidth=3, alpha=0.7)
    
    # Moulins (conductos verticales)
    ax.plot([30, 30], [superficie[60], lecho[60] + 2], 'b--', 
            linewidth=4, label='Moulin')
    ax.scatter([30], [superficie[60]], s=100, c='blue', marker='o', zorder=5)
    
    # Canales subglaciales
    canal_y = lecho + 1
    ax.plot(x[60:180], canal_y[60:180], 'r-', linewidth=5, 
            label='Canal subglacial (Röthlisberger)', alpha=0.8)
    
    # Película de agua
    ax.fill_between(x[20:60], lecho[20:60], lecho[20:60] + 0.5, 
                     color='cyan', alpha=0.5, 
                     label='Película de agua (Weertman)')
    
    # Flujo de salida
    ax.arrow(90, lecho[180], 5, -3, head_width=2, head_length=2, 
             fc='blue', ec='blue', linewidth=2)
    ax.text(92, 10, 'Salida\nproglaciar', fontsize=10, weight='bold')
    
    # Anotaciones
    ax.text(30, 55, 'Agua de\nfusión', fontsize=9, ha='center', 
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.text(70, 23, 'Lubricación\nbasal', fontsize=9, ha='center',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    # Configuración
    ax.set_xlim(0, 100)
    ax.set_ylim(10, 70)
    ax.set_xlabel('Distancia longitudinal', fontsize=12)
    ax.set_ylabel('Elevación', fontsize=12)
    ax.set_title('Sistema Hidrológico Subglacial', fontsize=14, weight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'sistema_subglacial.png', dpi=300, bbox_inches='tight')
    print(f"✓ Generado: {OUTPUT_DIR / 'sistema_subglacial.png'}")
    plt.close()


def diagrama_bioalbedo():
    """Comparación de albedo: nieve limpia vs. con algas."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Panel 1: Nieve limpia
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    ax1.set_title('Nieve Limpia', fontsize=14, weight='bold', pad=20)
    
    # Superficie blanca
    rect1 = mpatches.Rectangle((1, 3), 8, 4, facecolor='white', 
                                edgecolor='black', linewidth=2)
    ax1.add_patch(rect1)
    
    # Radiación solar
    for x in np.linspace(2, 8, 7):
        ax1.arrow(x, 8.5, 0, -1, head_width=0.3, head_length=0.2, 
                  fc='yellow', ec='orange', linewidth=2)
    ax1.text(5, 9, 'Radiación solar', ha='center', fontsize=11, weight='bold')
    
    # Reflexión
    for x in np.linspace(2.5, 7.5, 5):
        ax1.arrow(x, 7.2, 0, 1, head_width=0.3, head_length=0.2, 
                  fc='yellow', ec='orange', linewidth=2, alpha=0.6)
    
    # Métricas
    ax1.text(5, 5, 'Albedo: 0.80 - 0.90', ha='center', fontsize=13, 
             weight='bold', bbox=dict(boxstyle='round', facecolor='lightblue'))
    ax1.text(5, 2, 'Fusión: BAJA', ha='center', fontsize=12, color='blue')
    
    # Panel 2: Nieve con bioalbedo
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    ax2.set_title('Nieve con Algas / Crioconita', fontsize=14, weight='bold', pad=20)
    
    # Superficie oscurecida
    rect2 = mpatches.Rectangle((1, 3), 8, 4, facecolor='#CD853F', 
                                edgecolor='black', linewidth=2)
    ax2.add_patch(rect2)
    
    # Microorganismos
    for _ in range(20):
        x_alga = np.random.uniform(1.5, 8.5)
        y_alga = np.random.uniform(3.5, 6.5)
        ax2.scatter(x_alga, y_alga, s=50, c='darkgreen', 
                    marker='o', alpha=0.7, edgecolors='black', linewidth=0.5)
    
    # Radiación solar
    for x in np.linspace(2, 8, 7):
        ax2.arrow(x, 8.5, 0, -1, head_width=0.3, head_length=0.2, 
                  fc='yellow', ec='orange', linewidth=2)
    ax2.text(5, 9, 'Radiación solar', ha='center', fontsize=11, weight='bold')
    
    # Reflexión reducida
    for x in [3, 5, 7]:
        ax2.arrow(x, 7.2, 0, 0.6, head_width=0.3, head_length=0.15, 
                  fc='yellow', ec='orange', linewidth=2, alpha=0.3)
    
    # Absorción
    for x in [2.5, 4.5, 6.5, 8]:
        ax2.arrow(x, 6.8, 0, -0.8, head_width=0.3, head_length=0.2, 
                  fc='red', ec='darkred', linewidth=2, alpha=0.7)
    
    # Métricas
    ax2.text(5, 5, 'Albedo: 0.40 - 0.60', ha='center', fontsize=13, 
             weight='bold', bbox=dict(boxstyle='round', facecolor='lightcoral'))
    ax2.text(5, 2, 'Fusión: ALTA (+30%)', ha='center', fontsize=12, 
             color='red', weight='bold')
    
    plt.suptitle('Efecto del Bioalbedo en la Fusión Glaciar', 
                 fontsize=16, weight='bold', y=0.98)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'comparacion_bioalbedo.png', dpi=300, bbox_inches='tight')
    print(f"✓ Generado: {OUTPUT_DIR / 'comparacion_bioalbedo.png'}")
    plt.close()


def main():
    """Genera todos los diagramas educativos."""
    print("\n" + "="*60)
    print("Generando diagramas educativos - Conocimiento Glaciar")
    print("="*60 + "\n")
    
    try:
        diagrama_topografia_basal()
        diagrama_retroalimentacion_albedo()
        diagrama_sistema_subglacial()
        diagrama_bioalbedo()
        
        print("\n" + "="*60)
        print("✓ Todos los diagramas generados exitosamente")
        print(f"✓ Ubicación: {OUTPUT_DIR.absolute()}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error al generar diagramas: {e}")
        raise


if __name__ == "__main__":
    main()
