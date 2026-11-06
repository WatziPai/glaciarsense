"""
Script para corregir el problema de .area vs .área en propiedades de Shapely.
"""
import re

files_to_fix = ['gis_engine.py', 'app.py']

for filename in files_to_fix:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Corregir .área por .area (propiedad de Shapely)
        content = re.sub(r'\.área\b', '.area', content)
        
        # Corregir área = cuando es variable local de geometría
        content = re.sub(r'\barea\s*=\s*0\.0 if g\.is_empty else g\.área', 
                        'area = 0.0 if g.is_empty else g.area', content)
        
        if content != original:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ {filename} corregido")
        else:
            print(f"- {filename} sin cambios")
            
    except FileNotFoundError:
        print(f"⚠ {filename} no encontrado")

print("\n✓ Corrección completada")
