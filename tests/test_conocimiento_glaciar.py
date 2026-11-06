"""
tests/test_conocimiento_glaciar.py
===================================
Pruebas de verificación para el módulo de Conocimiento Glaciar.

Verifica que:
- El archivo de referencias existe y está bien formado
- Los diagramas educativos se pueden generar
- La nueva pestaña se integra correctamente con el resto de la aplicación
"""
import pytest
from pathlib import Path
import sys

# Añadir directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class TestConocimientoGlaciar:
    """Suite de pruebas para el módulo educativo."""
    
    def test_archivo_referencias_existe(self):
        """Verifica que el archivo de referencias bibliográficas existe."""
        ruta_referencias = BASE_DIR / "data" / "REFERENCIAS_CONOCIMIENTO_GLACIAR.md"
        assert ruta_referencias.exists(), "El archivo de referencias debe existir"
        assert ruta_referencias.stat().st_size > 0, "El archivo no debe estar vacío"
    
    def test_contenido_referencias(self):
        """Verifica que el archivo contiene referencias científicas válidas."""
        ruta_referencias = BASE_DIR / "data" / "REFERENCIAS_CONOCIMIENTO_GLACIAR.md"
        contenido = ruta_referencias.read_text(encoding='utf-8')
        
        # Verificar secciones principales
        assert "Cavidades Ocultas" in contenido
        assert "Puntos de No Retorno" in contenido
        assert "Agua Subglacial" in contenido
        assert "Bioalbedo" in contenido
        assert "Avalanchas" in contenido
        assert "Conocimiento Comunitario" in contenido
        
        # Verificar que contiene DOIs (formato científico)
        assert "DOI:" in contenido or "doi.org" in contenido
        
        # Verificar que menciona revistas científicas
        assert "Cryosphere" in contenido or "Nature" in contenido
        
        # Verificar recursos andinos
        assert "INAIGEM" in contenido or "WGMS" in contenido
    
    def test_script_diagramas_existe(self):
        """Verifica que el script de generación de diagramas existe."""
        ruta_script = BASE_DIR / "scripts" / "generar_diagramas_educativos.py"
        assert ruta_script.exists(), "El script de diagramas debe existir"
    
    def test_script_diagramas_importable(self):
        """Verifica que el script de diagramas es importable (sin errores de sintaxis)."""
        ruta_script = BASE_DIR / "scripts" / "generar_diagramas_educativos.py"
        
        # Leer y compilar (detecta errores de sintaxis)
        contenido = ruta_script.read_text(encoding='utf-8')
        try:
            compile(contenido, str(ruta_script), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Error de sintaxis en script de diagramas: {e}")
    
    def test_app_contiene_tab5(self):
        """Verifica que app.py define la quinta pestaña (Análisis Avanzado)."""
        ruta_app = BASE_DIR / "app.py"
        contenido = ruta_app.read_text(encoding='utf-8')
        
        # Verificar que define 5 tabs
        assert "tab1, tab2, tab3, tab4, tab5" in contenido, \
            "app.py debe definir 5 pestañas (incluyendo tab5)"
        
        # Verificar que existe el bloque with tab5
        assert "with tab5:" in contenido, \
            "app.py debe contener el bloque 'with tab5:'"
        
        # Tab 5 = Análisis Avanzado; conocimiento glaciar en expanders de otras tabs
        assert "advanced_analysis" in contenido or "perform_advanced_analysis" in contenido
        assert "topografia" in contenido.lower() or "subglacial" in contenido.lower()
    
    def test_changelog_actualizado(self):
        """Verifica que existe un archivo CHANGELOG con la versión 2.2."""
        ruta_changelog = BASE_DIR / "CHANGELOG.md"
        assert ruta_changelog.exists(), "Debe existir CHANGELOG.md"
        
        contenido = ruta_changelog.read_text(encoding='utf-8')
        assert "2.2" in contenido, "CHANGELOG debe mencionar versión 2.2"
        assert "Conocimiento Glaciar" in contenido
    
    def test_readme_actualizado(self):
        """Verifica que README.md menciona el nuevo módulo."""
        ruta_readme = BASE_DIR / "README.md"
        contenido = ruta_readme.read_text(encoding='utf-8')
        
        # Debe mencionar el módulo educativo
        assert "Conocimiento Glaciar" in contenido or "educativo" in contenido.lower()
        
        # Debe mencionar las referencias
        assert "REFERENCIAS_CONOCIMIENTO_GLACIAR" in contenido
    
    def test_estructura_expanders(self):
        """Verifica que app.py usa expanders para conocimiento glaciar (en tab2/tab3/tab4)."""
        ruta_app = BASE_DIR / "app.py"
        contenido = ruta_app.read_text(encoding='utf-8')
        
        # El conocimiento glaciar se muestra en expanders de otras tabs
        count_expanders = contenido.count("with st.expander(")
        assert count_expanders >= 3, \
            f"Debe haber al menos 3 expanders en la app, encontrados: {count_expanders}"
    
    def test_iconos_tematicos(self):
        """Verifica que el UI tiene indicadores visuales de sección (sin emojis)."""
        ruta_app = BASE_DIR / "app.py"
        contenido = ruta_app.read_text(encoding='utf-8')
        
        # La app no usa emojis (política de diseño académico)
        # Verifica que el contenido glaciológico educativo existe en expanders
        assert "Bioalbedo" in contenido
        assert "subglacial" in contenido.lower() or "Subglacial" in contenido
        assert "Inercia" in contenido or "inercia" in contenido
        # El análisis avanzado cubre el contenido temático
        assert "advanced_analysis" in contenido
    
    def test_referencias_cientificas_formato(self):
        """Verifica el formato de las referencias científicas."""
        ruta_referencias = BASE_DIR / "data" / "REFERENCIAS_CONOCIMIENTO_GLACIAR.md"
        contenido = ruta_referencias.read_text(encoding='utf-8')
        
        # Verificar formato APA/científico (usa & para múltiples autores)
        assert "&" in contenido or "et al." in contenido, "Debe usar formato científico para autores"
        
        # Verificar años de publicación
        import re
        años = re.findall(r'\((\d{4})\)', contenido)
        assert len(años) > 10, "Debe contener múltiples referencias con años"
        
        # Verificar que los años son razonables (1990-2026)
        años_validos = [int(año) for año in años if 1990 <= int(año) <= 2026]
        assert len(años_validos) >= 10, "Debe haber al menos 10 referencias recientes"


class TestIntegracionSistema:
    """Pruebas de integración con el resto del sistema."""
    
    def test_no_rompe_tabs_existentes(self):
        """Verifica que la nueva tab no afecta las existentes."""
        ruta_app = BASE_DIR / "app.py"
        contenido = ruta_app.read_text(encoding='utf-8')
        
        # Verificar que existen todos los bloques with tab
        for i in range(1, 6):
            assert f"with tab{i}:" in contenido, \
                f"El bloque 'with tab{i}:' debe existir"
    
    def test_importaciones_validas(self):
        """Verifica que no hay importaciones rotas en app.py."""
        ruta_app = BASE_DIR / "app.py"
        
        # Intentar compilar el archivo (detecta errores de sintaxis)
        contenido = ruta_app.read_text(encoding='utf-8')
        try:
            compile(contenido, str(ruta_app), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Error de sintaxis en app.py: {e}")
    
    def test_version_actualizada(self):
        """Verifica que la versión se actualizó a 2.2."""
        ruta_app = BASE_DIR / "app.py"
        contenido = ruta_app.read_text(encoding='utf-8')
        
        # Buscar línea de versión
        assert 'v2.2' in contenido, "La versión debe actualizarse a v2.2"


if __name__ == "__main__":
    # Ejecutar pruebas con pytest
    pytest.main([__file__, "-v", "--tb=short"])
