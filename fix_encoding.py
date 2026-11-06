"""Script para corregir problemas de encoding en todos los archivos Python."""
import re
from pathlib import Path

# Diccionario de correcciones
CORRECTIONS = {
    r'\banio\b': 'año',
    r'\banios\b': 'años',
    r'\bAnio\b': 'Año',
    r'\bAnios\b': 'Años',
    r'\banalisis\b': 'análisis',
    r'\bAnalisis\b': 'Análisis',
    r'\bestimacion\b': 'estimación',
    r'\bEstimacion\b': 'Estimación',
    r'\bcalculo\b': 'cálculo',
    r'\bCalculo\b': 'Cálculo',
    r'\binformacion\b': 'información',
    r'\bInformacion\b': 'Información',
    r'\bgeografica\b': 'geográfica',
    r'\bGeografica\b': 'Geográfica',
    r'\btopografia\b': 'topografía',
    r'\bTopografia\b': 'Topografía',
    r'\bparametro\b': 'parámetro',
    r'\bParametro\b': 'Parámetro',
    r'\bparametros\b': 'parámetros',
    r'\bParametros\b': 'Parámetros',
    r'\bporcent': 'porcient',  # NO - mantener porcent
    r'\bmexico\b': 'méxico',
    r'\bMexico\b': 'México',
    r'\bperu\b': 'perú',
    r'\bPeru\b': 'Perú',
    r'\bCordillera\b': 'Cordillera',
    r'\bmetodo\b': 'método',
    r'\bMetodo\b': 'Método',
    r'\bmetodos\b': 'métodos',
    r'\bMetodos\b': 'Métodos',
    r'\bepoca\b': 'época',
    r'\bEpoca\b': 'Época',
    r'\barea\b': 'área',
    r'\bArea\b': 'Área',
    r'\bareas\b': 'áreas',
    r'\bAreas\b': 'Áreas',
    r'\bindice\b': 'índice',
    r'\bIndice\b': 'Índice',
    r'\bindices\b': 'índices',
    r'\bIndices\b': 'Índices',
    r'\blinea\b': 'línea',
    r'\bLinea\b': 'Línea',
    r'\blineas\b': 'líneas',
    r'\bLineas\b': 'Líneas',
    r'\bpestana\b': 'pestaña',
    r'\bPestana\b': 'Pestaña',
    r'\bpestanas\b': 'pestañas',
    r'\bPestanas\b': 'Pestañas',
    r'\bPestanias\b': 'Pestañas',
    r'\bsenal\b': 'señal',
    r'\bSenal\b': 'Señal',
    r'\bsenales\b': 'señales',
    r'\bSenales\b': 'Señales',
    r'\bdiagnostico\b': 'diagnóstico',
    r'\bDiagnostico\b': 'Diagnóstico',
    r'\bsismico\b': 'sísmico',
    r'\bSismico\b': 'Sísmico',
    r'\batmosfera\b': 'atmósfera',
    r'\bAtmosfera\b': 'Atmósfera',
    r'\bhidrico\b': 'hídrico',
    r'\bHidrico\b': 'Hídrico',
    r'\bhidrica\b': 'hídrica',
    r'\bHidrica\b': 'Hídrica',
}

# NO corregir estas (nombres de variable/función):
SKIP_PATTERNS = [
    r'def \w+',  # Definiciones de función
    r'class \w+',  # Definiciones de clase
    r'\w+\s*=',  # Asignaciones
    r'import \w+',  # Imports
    r'from \w+',  # From imports
]

def should_skip_line(line):
    """Verifica si una línea debe saltarse."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, line):
            return True
    return False

def fix_file(filepath):
    """Corrige un archivo."""
    print(f"Procesando: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = 0
    
    # Aplicar correcciones línea por línea para evitar cambios en código
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if should_skip_line(line) or line.strip().startswith('#'):
            # No corregir definiciones, comentarios de código
            fixed_line = line
        else:
            # Aplicar correcciones
            fixed_line = line
            for pattern, replacement in CORRECTIONS.items():
                old_line = fixed_line
                fixed_line = re.sub(pattern, replacement, fixed_line, flags=re.IGNORECASE)
                if old_line != fixed_line:
                    changes += 1
        
        fixed_lines.append(fixed_line)
    
    new_content = '\n'.join(fixed_lines)
    
    if new_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✓ {changes} correcciones aplicadas")
        return changes
    else:
        print(f"  - Sin cambios necesarios")
        return 0

def main():
    """Procesa todos los archivos Python."""
    base_dir = Path('.')
    
    # Archivos a procesar
    files_to_fix = [
        'app.py',
        'config.py',
        'detector.py',
        'gis_engine.py',
        'advanced_analysis.py',
    ]
    
    total_changes = 0
    
    print("\n" + "="*60)
    print("Corrigiendo problemas de encoding...")
    print("="*60 + "\n")
    
    for filename in files_to_fix:
        filepath = base_dir / filename
        if filepath.exists():
            changes = fix_file(filepath)
            total_changes += changes
        else:
            print(f"⚠ No encontrado: {filename}")
    
    print("\n" + "="*60)
    print(f"✓ Total de correcciones: {total_changes}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
