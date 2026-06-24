import pyodbc
from rapidfuzz import process, fuzz
import unicodedata

def normalize_text(text):
    if not text: return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8').upper()
    text = text.replace('+', '-').replace('/', '-')
    return " ".join(text.split())

class MasterCatalog:
    def __init__(self, conn_str):
        self.conn_str = conn_str
        self.catalogs = {}
        self.load_catalogs()

    def load_catalogs(self):
        conn = pyodbc.connect(self.conn_str)
        cursor = conn.cursor()
        
        # Define table configurations: table_name, id_col, desc_col
        tables = {
            "principio_activo": ("Procurement.principio_activo", "codigo", "descripcion"),
            "concentracion": ("Procurement.concentracion", "codigo", "descripcion"),
            "forma_farmaceutica": ("Procurement.ff", "id", "descripcion"),
            "fabricante": ("Procurement.Fabricante", "cod_fab", "Nombre_fabricante"),
            "marca": ("Procurement.marca", "id", "marca"),
            "codigo_atc": ("Procurement.codigo_atc", "id", "codigo"), # Or descripcion? We match ATC by code usually
            "clasificacion_insumo": ("Procurement.clasificacion_insumo", "codigo", "descripcion"),
            "origen": ("Procurement.origen", "codigo", "descripcion"),
            "contenido_neto_unidad": ("Procurement.contenido_neto_unidad", "id", "unidad")
        }

        for key, (tbl, id_col, desc_col) in tables.items():
            try:
                cursor.execute(f"SELECT {id_col}, {desc_col} FROM {tbl}")
                rows = cursor.fetchall()
                # Store mappings: { normalized_name: id }
                mapping = {}
                names = []
                for r in rows:
                    if r[1]:
                        norm = normalize_text(r[1])
                        mapping[norm] = r[0]
                        names.append(norm)
                self.catalogs[key] = {"mapping": mapping, "names": names}
            except Exception as e:
                print(f"Warning: Could not load catalog {tbl}: {e}")
                self.catalogs[key] = {"mapping": {}, "names": []}
                
        conn.close()

    def find_id(self, catalog_key, search_text, threshold=90.0):
        if not search_text: return None
        cat = self.catalogs.get(catalog_key)
        if not cat or not cat["names"]: return None
        
        norm_search = normalize_text(search_text)

        # Mapeo explicito de las 22 categorias de AppSheet a Procurement.clasificacion_insumo
        if catalog_key == "clasificacion_insumo":
            mapping_dict = {
                "HIGIENE BUCODENTAL": 98,              # HIGIENE PERSONAL
                "CUIDADO FEMENINO": 94,                # HIGIENE FEMENINA
                "CUIDADO CORPORAL Y BANIO": 92,        # CUIDADO PERSONAL
                "CUIDADO CORPORAL Y BANO": 92,         # CUIDADO PERSONAL
                "DESODORANTES": 92,                    # CUIDADO PERSONAL
                "CUIDADO DE LA PIEL": 92,              # CUIDADO PERSONAL
                "CUIDADO DEL CABELLO": 92,             # CUIDADO PERSONAL
                "FOTOPROTECCION": 92,                  # CUIDADO PERSONAL
                "PANALES Y TOALLITAS": 103,           # ARTICULOS PARA BEBE
                "ALIMENTACION Y FORMULAS INFANTILES": 103, # ARTICULOS PARA BEBE
                "ACCESORIOS INFANTILES": 103,          # ARTICULOS PARA BEBE
                "VITAMINAS Y MINERALES": 117,          # SUPLEMENTO NUTRICIONAL
                "NUTRICION DEPORTIVA": 117,            # SUPLEMENTO NUTRICIONAL
                "ALIMENTOS Y BEBIDAS DIETETICAS": 84,  # ALIMENTO
                "MATERIAL DE CURACION": 79,            # MATERIAL DE CURACION
                "INSUMOS DESCARTABLES": 87,            # DESCARTABLE
                "EQUIPOS DE MONITOREO DE SALUD": 80,   # EQUIPO MEDICO
                "ARTICULOS ORTOPEDICOS": 110,          # MATERIAL MEDICO
                "PRODUCTOS DE LIMPIEZA": 106,          # PRODUCTO DE LIMPIEZA
                "REPELENTES DE INSECTOS": 83,          # REPELENTE DE INSECTOS
                "OTROS MISCELANEOS": 88,               # MISCELANEOS
                "PRUEBAS RAPIDAS DE DIAGNOSTICO": 82,  # REACTIVO
                "REACTIVOS QUIMICOS": 82,              # REACTIVO
            }
            if norm_search in mapping_dict:
                return mapping_dict[norm_search]
        
        # Limpieza profunda para fabricantes (remover palabras genéricas corporativas)
        if catalog_key == "fabricante":
            import re
            generics = [
                'PHARMACEUTICALS', 'PHARMACEUTICAL', 'PHARMA', 'FARMAC UTICO', 'FARMACEUTICO', 'QU MICO', 'QUIMICO',
                'MEDICAL', 'MEDICA', 'MEDICS', 'MEDIC', 'MEDICAMENTO', 'MEDICAMENTOS', 'HEALTHCARE', 'BIOSCIENCE',
                'MEGALABS', 'BIOGLASS', 'ROWE', 'VARGAS', 'BIOTECH', 'SIEGFRIED', 'LETI', 'VALMORCA', 'WALIFE',
                'PHARMETIQUE', 'DROTAFARMA', 'PLUSANDEX', 'BEHRENS', 'MEDIHEALTH', 'DOLLDER', 'DISTRILAB', 'VINCENTI',
                'UNIPHARMA', 'CALOX', 'CLEOPHARMA', 'HERBAPLANT', 'TECNOFARMA', 'BIOFARCO', 'CIFARMA', 'FARMAGENIK',
                'LAPROFF', 'PHARMALAB', 'TIARES', 'DROS', 'LATTAN', 'LATTAM', 'COFASA', 'BRUCEN', 'ANGELUS', 'DISTRILAB',
                'DPT', 'BIOVENEZUELA', 'ARTE M DICO', 'ARTE MEDICO', 'M DICO', 'MEDICO', 'GROUPMEDICAL', 'PHARMATECH',
                'BIOSKY', 'COASPHARMA', 'NATURLIFE', 'LIFE', 'LABORATORIO', 'LABORATORIOS', 'S.A.', 'C.A.', 'SA', 'CA'
            ]
            generics.sort(key=len, reverse=True)
            pattern = re.compile(r'\b(' + '|'.join(re.escape(g) for g in generics) + r')\b', re.IGNORECASE)
            
            cleaned = pattern.sub('', norm_search)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned != "": 
                norm_search = cleaned

        # Limpieza profunda para orígenes (ignorar basura de la BD)
        if catalog_key == "origen":
            import re
            basura = ['IMPORTADO', 'NACIONAL', 'GENERICO', 'GENERIC', 'ALCOHOL', 'TERMOMETRO', 'N-A', 'N/A', 'DESCONOCIDO']
            basura.sort(key=len, reverse=True)
            pattern = re.compile(r'\b(' + '|'.join(re.escape(g) for g in basura) + r')\b', re.IGNORECASE)
            cleaned = pattern.sub('', norm_search)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned == "":
                return None
            norm_search = cleaned

        # ATC is usually exact match of code
        if catalog_key == "codigo_atc":
            return cat["mapping"].get(norm_search)
            
        match = process.extractOne(norm_search, cat["names"], scorer=fuzz.WRatio)
        if match:
            best_match_str, score, _ = match
            if score >= threshold:
                return cat["mapping"][best_match_str]
        return None
