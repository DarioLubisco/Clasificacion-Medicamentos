import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Resultados originales de Pro recopilados antes del fallo del API
PRO_RESULTS_BACKUP = {
  "0000000030373": {
    "descripcion": "DISCOLAYTE POLVO 69.7 G X 10 SOBRES",
    "gemini_2_5_pro": {
      "atrib": {
        "razonamiento": "El análisis se basa en la información explícita de la descripción original, las fuentes web y la imagen del producto. La taxonomía se establece a partir de su uso como laxante, confirmado en múltiples fuentes. El principio activo, Polietilenglicol, se menciona en la imagen y en las descripciones. El fabricante 'Distrilab' y la marca 'Discolayte' son claramente identificables. La presentación se extrae de la descripción original 'X 10 SOBRES' y el peso total '69.7 G'. Se asume que la descripción original es la correcta frente a otras fuentes que podrían estar describiendo una presentación diferente (por unidad). La condición de venta OTC se extrae de una de las fuentes.",
        "confianza_nivel": 4,
        "confianza_razonamiento": "La mayoría de los datos son explícitos y consistentes entre la descripción original, la imagen del producto y el sitio del fabricante (Distrilab). El principio activo, la marca y el fabricante son inequívocos. La taxonomía como laxante gastrointestinal está bien soportada. La única ambigüedad radica en la presentación, ya que algunas fuentes de retail describen un sobre único de 69.7g, mientras que la descripción original and el sitio del fabricante indican una caja de 10 sobres con un peso total de 69.7g. Se ha procedido con la información de la descripción original ('X 10 SOBRES'), asumiendo que es el producto a procesar. La confianza es alta (4/5) y no total debido a esta discrepancia entre fuentes.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "GASTROINTESTINALES",
        "subcategoria": "LAXANTES",
        "principio_activo": "Polietilenglicol, Electrolitos",
        "concentracion": "PEG 3350",
        "forma_farmaceutica": "Polvo",
        "requiere_recipe": 0,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Distrilab",
        "marca": "Discolayte",
        "codigo_atc": None,
        "cantidad_presentacion": 10,
        "contenido_neto": 69.7,
        "contenido_neto_unidad_Des": "g",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 75
    },
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "El producto es Discolayte, un laxante en polvo para reconstituir cuyo principio activo es Polietilenglicol 3350 (con electrolitos). La presentación es de 10 sobres con 69.7 g cada uno. Es fabricado por Distrilab y es de venta libre (OTC).",
        "confianza_nivel": 5,
        "confianza_razonamiento": "Todos los datos coinciden perfectamente entre la descripción original, el contexto web y las imágenes proporcionadas, sin ambigüedades.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "GASTROINTESTINALES",
        "subcategoria": "LAXANTES",
        "principio_activo": "POLIETILENGLICOL Y ELECTROLITOS",
        "concentracion": "3350",
        "forma_farmaceutica": "Polvo",
        "requiere_recipe": 0,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "DISTRILAB",
        "marca": "DISCOLAYTE",
        "codigo_atc": None,
        "cantidad_presentacion": 10,
        "contenido_neto": 69.7,
        "contenido_neto_unidad_Des": "g",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 75
    }
  },
  "0000000163774": {
    "descripcion": "Oxacilina 1g polvo para solución inyectable (IM/IV) x 10 viales Zakimed",
    "gemini_2_5_pro": {
      "atrib": {
        "razonamiento": "El análisis se basa en la descripción original y las fuentes web proporcionadas. El principio activo 'Oxacilina', la concentración '1 g', la forma farmacéutica 'Polvo para Solución Inyectable' y la cantidad '10' viales se extraen directamente de la descripción y son confirmados por las fuentes. El código ATC 'J01CF04' se encuentra explícitamente en Vademecum y Farmatodo. Se clasifica como genérico (1) ya que el producto se comercializa bajo el nombre del principio activo por múltiples laboratorios. La marca y fabricante se establecen como 'Zakimed' basándose en la descripción original, a pesar de que las fuentes mencionan otros laboratorios para productos equivalentes. La taxonomía se establece como MEDICAMENTO_ALOPATICO / ANTIBIOTICOS. La subcategoría se asigna a 'AMOXICILINA' por ser la opción más cercana dentro de la familia de las penicilinas en la taxonomía provista, aunque se reconoce que no es una clasificación precisa ya que el principio activo es Oxacilina. La presentación es en viales, no en blíster (0). Se determina que requiere receta médica ('VENTA CON FÓRMULA MÉDICA'). Se aplican las reglas de negocio para sólidos para 'cantidad_presentacion', 'contenido_neto' y 'contenido_neto_unidad_Des'.",
        "confianza_nivel": 4,
        "confianza_razonamiento": "La confianza es alta (4/5). La mayoría de los atributos se extraen de información explícita y consistente en las fuentes. El nivel no es 5 debido a dos puntos: 1) Existe ambigüedad en el fabricante/marca entre la descripción ('Zakimed') y las fuentes (que listan 'FARMALOGICA', 'Zakipharma', etc.), aunque se priorizó la descripción original. 2) La taxonomía de subcategoría proporcionada es incompleta y no incluye 'Oxacilina', forzando la selección de 'AMOXICILINA' como la clase más próxima (penicilinas), lo cual reduce la precisión absoluta de la clasificación.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ANTIBIOTICOS",
        "subcategoria": "AMOXICILINA",
        "principio_activo": "Oxacilina",
        "concentracion": "1 g",
        "forma_farmaceutica": "Polvo para Solución Inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Zakimed",
        "marca": "Zakimed",
        "codigo_atc": "J01CF04",
        "cantidad_presentacion": 10,
        "contenido_neto": 1,
        "contenido_neto_unidad_Des": "Caja",
        "blister": 0,
        "generico": 1,
        "clasificacion_insumo_Des": None
      },
      "score": 80
    },
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "El producto es un antibiótico cuyo principio activo es la Oxacilina en concentración de 1 g. La forma farmacéutica es polvo para solución inyectable. La presentación indica 10 viales, por lo que la cantidad de presentación es 10 y el contenido neto es 1 g por vial. El código ATC J01CF04 se extrae explícitamente del contexto web. La marca identificada en la descripción original es Zakimed. Al ser un antibiótico, requiere récipe médico.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "Todos los datos críticos (principio activo, concentración, forma farmacéutica, cantidad, ATC) se extraen de forma explícita y sin ambigüedades de la descripción original y el contexto web.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ANTIBIOTICOS",
        "subcategoria": "PENICILINAS",
        "principio_activo": "Oxacilina",
        "concentracion": "1 g",
        "forma_farmaceutica": "Polvo para solución inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": None,
        "marca": "Zakimed",
        "codigo_atc": "J01CF04",
        "cantidad_presentacion": 10,
        "contenido_neto": 1,
        "contenido_neto_unidad_Des": "g",
        "blister": 0,
        "generico": 1,
        "clasificacion_insumo_Des": None
      },
      "score": 75
    }
  },
  "0000000201629": {
    "descripcion": "Metotrexato 50 mg/2 ml solución inyectable (IV/IM) en ampolla.",
    "gemini_2_5_pro": {
      "atrib": {
        "razonamiento": "Se extrajeron los atributos del producto de las fuentes web proporcionadas, principalmente 'farmasmart.com', 'curitek.com' y 'vademecum.es'. El principio activo (Metotrexato), la concentración (50 mg/2 ml), la forma farmacéutica (Solución inyectable), la marca (Traxacord) y el fabricante (Accord) son consistentes. La presentación es de 1 frasco ámpula de 2 ml. El código ATC (L01BA01) se encontró explícitamente. La clasificación taxonómica es imposible de realizar con precisión, ya que el producto es un agente antineoplásico e inmunomodulador (clase ATC 'L'), y la taxonomía proporcionada no incluye una categoría para esta clase terapéutica. Forzar una clasificación violaría la regla de precisión absoluta.",
        "confianza_nivel": 1,
        "confianza_razonamiento": "La confianza es NULA. Aunque la mayoría de los atributos se identificaron con alta certeza, la clasificación taxonómica (dominio, categoría, subcategoría) es un requisito obligatorio e inquebrantable. La taxonomía proporcionada es incompleta y no contiene una categoría para medicamentos antineoplásicos como el Metotrexato. Esta contradicción entre la obligatoriedad de clasificar y la imposibilidad de hacerlo con precisión según las reglas dadas hace que el registro completo no sea fiable.",
        "dominio": None,
        "categoria": None,
        "subcategoria": None,
        "principio_activo": "Metotrexato",
        "concentracion": "50 mg/2 ml",
        "forma_farmaceutica": "Solución inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Accord",
        "marca": "Traxacord",
        "codigo_atc": "L01BA01",
        "cantidad_presentacion": 1,
        "contenido_neto": 2,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 80
    },
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "El producto es Metotrexato, un medicamento antineoplásico e inmunosupresor en forma de solución inyectable. La concentración explícita es de 50 mg/2 ml. Al ser una ampolla líquida, la cantidad de presentación es 1 y el contenido neto es 2 ml. El código ATC (L01BA01) se extrae directamente del contexto web (Vademecum). Al no indicar marca comercial en la descripción original y tener un código de barras interno, se clasifica como genérico. Requiere receta médica por su naturaleza oncológica/inmunosupresora.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "Dato explícito e inequívoco en la descripción original, respaldado por la literatura médica del contexto web para el código ATC y la condición de venta.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ONCOLOGICOS",
        "subcategoria": "ANTINEOPLASICOS",
        "principio_activo": "Metotrexato",
        "concentracion": "50 mg/2 ml",
        "forma_farmaceutica": "Solución Inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": None,
        "marca": None,
        "codigo_atc": "L01BA01",
        "cantidad_presentacion": 1,
        "contenido_neto": 2,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 1,
        "clasificacion_insumo_Des": None
      },
      "score": 70
    }
  },
  "0000000206815": {
    "descripcion": "Gemcitabina 1 g polvo para solución inyectable, 1 ampolla",
    "gemini_2_5_pro": None,
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "La descripción original detalla explícitamente el principio activo (Gemcitabina), la concentración (1 g), la forma farmacéutica (polvo para solución inyectable) y la presentación (1 ampolla). Al no especificar marca ni laboratorio en la descripción ni en la imagen genérica, se clasifica como genérico. El código ATC (L01BC05) y la categoría terapéutica (Oncología / Antineoplásicos) se extraen directamente del contexto web proporcionado (Vademecum y Curitek).",
        "confianza_nivel": 5,
        "confianza_razonamiento": "Información explícita, inequívoca y sin contradicciones. Los datos de concentración, forma farmacéutica y cantidad provienen directamente de la descripción. El código ATC está explícito en el contexto web.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ONCOLOGIA",
        "subcategoria": "ANTINEOPLASICOS",
        "principio_activo": "Gemcitabina",
        "concentracion": "1 g",
        "forma_farmaceutica": "Polvo para solución inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": None,
        "marca": None,
        "codigo_atc": "L01BC05",
        "cantidad_presentacion": 1,
        "contenido_neto": 1,
        "contenido_neto_unidad_Des": "g",
        "blister": 0,
        "generico": 1,
        "clasificacion_insumo_Des": None
      },
      "score": 70
    }
  },
  "0000025525755": {
    "descripcion": "Jarabe de achicoria Farmagenik 120 ml",
    "gemini_2_5_pro": {
      "atrib": {
        "razonamiento": "El producto se identifica como un jarabe natural a base de Achicoria. La marca y fabricante es 'Farmagenik', claramente visible en la descripción y la imagen. El contenido es de 120 ml. La taxonomía se deriva de su naturaleza como producto a base de plantas (Fitoterapia) con propiedades digestivas (laxante, estimulante del apetito) mencionadas en la fuente web. El principio activo es la planta misma, 'Achicoria', como se indica en la etiqueta 'Jarabe de Achicoria'. No se especifica concentración, origen o código ATC.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "La información clave como marca (Farmagenik), forma farmacéutica (Jarabe), contenido neto (120 ml) y principio activo (Achicoria) se encuentra explícitamente en la descripción original, la imagen del producto y la fuente web de Farmadon. La clasificación taxonómica se basa directamente en la descripción del producto como un remedio natural a base de plantas con efectos digestivos, siguiendo las reglas proporcionadas.",
        "dominio": "PRODUCTO_NATURAL_HOMEOPATICO",
        "categoria": "FITOTERAPIA",
        "subcategoria": "DIGESTIVOS",
        "principio_activo": "Achicoria",
        "concentracion": None,
        "forma_farmaceutica": "Jarabe",
        "requiere_recipe": 0,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Farmagenik",
        "marca": "Farmagenik",
        "codigo_atc": None,
        "cantidad_presentacion": 1,
        "contenido_neto": 120,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 0
    },
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "El producto es un jarabe a base de extracto de achicoria, elaborado por la marca Farmagenik. Se presenta en un envase de 120 ml. Al ser un producto natural con propiedades digestivas y laxantes suaves (según el contexto web), se clasifica en fitoterapia como digestivo.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "La información es explícita y consistente entre la descripción original, las imágenes del producto (donde se lee claramente la marca, el nombre y el contenido neto) y el contexto web proporcionado.",
        "dominio": "PRODUCTO_NATURAL_HOMEOPATICO",
        "categoria": "FITOTERAPIA",
        "subcategoria": "DIGESTIVOS",
        "principio_activo": "Achicoria",
        "concentracion": None,
        "forma_farmaceutica": "Jarabe",
        "requiere_recipe": 0,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Farmagenik",
        "marca": "Farmagenik",
        "codigo_atc": None,
        "cantidad_presentacion": 1,
        "contenido_neto": 120,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 0
    }
  },
  "0000025525762": {
    "descripcion": "Jarabe Lamedor 120 ml Farmagenik",
    "gemini_2_5_pro": {
      "atrib": {
        "razonamiento": "El producto es un jarabe expectorante para la tos. La descripción original y las fuentes web confirman que es 'Jarabe Lamedor' de 120 ml, fabricado por 'Farmagenik'. La imagen del producto corrobora esta información. Se clasifica como 'ANTITUSIVOS Y EXPECTORANTES' debido a su función explícita de 'calmante para la tos y la flema' y 'expectorante'. Aunque se menciona como 'medicina natural', la taxonomía provista no tiene una categoría natural para afecciones respiratorias, por lo que se elige la clasificación funcional más precisa. Al ser un líquido en un solo envase, la `cantidad_presentacion` es 1 y el `contenido_neto` es 120 ml. No se especifica el principio activo, por lo que este y la concentración son nulos. El producto tiene una marca clara ('Lamedor'), por lo que no es genérico.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "La confianza es total (5) porque los atributos clave como marca (Lamedor), fabricante (Farmagenik), forma farmacéutica (Jarabe) y contenido neto (120 ml) son explícitos y consistentes en la descripción original, la página web oficial del fabricante y la imagen del producto. La clasificación taxonómica se basa en la función inequívoca del producto ('expectorante', 'calmante para la tos'), que se alinea directamente con una subcategoría disponible.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "RESPIRATORIO",
        "subcategoria": "ANTITUSIVOS Y EXPECTORANTES",
        "principio_activo": None,
        "concentracion": None,
        "forma_farmaceutica": "Jarabe",
        "requiere_recipe": None,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Farmagenik",
        "marca": "Lamedor",
        "codigo_atc": None,
        "cantidad_presentacion": 1,
        "contenido_neto": 120,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 0
    },
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "El producto es un jarabe expectorante y calmante para la tos (Lamedor) de la marca Farmagenik. Aunque es de origen natural, funcionalmente se clasifica en la categoría respiratoria como antitusivo y expectorante según la taxonomía disponible. La presentación es un frasco líquido, por lo que la cantidad es 1 y el contenido neto es 120 ml, tal como se indica en la descripción y la imagen.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "La información sobre la forma farmacéutica, volumen, marca y uso terapéutico está explícita y corroborada tanto en la descripción original como en el contexto web y las imágenes.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "RESPIRATORIO",
        "subcategoria": "ANTITUSIVOS Y EXPECTORANTES",
        "principio_activo": None,
        "concentracion": None,
        "forma_farmaceutica": "Jarabe",
        "requiere_recipe": 0,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Farmagenik",
        "marca": "Farmagenik",
        "codigo_atc": None,
        "cantidad_presentacion": 1,
        "contenido_neto": 120,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 0
    }
  },
  "0000075971199": {
    "descripcion": "PENASTIM 500 mg solución inyectable",
    "gemini_2_5_pro": {
      "atrib": {
        "razonamiento": "El producto es un antibiótico inyectable. Las fuentes web y Vademecum confirman que el principio activo es una combinación de Imipenem y Cilastatina en una concentración de 500 mg / 500 mg. La forma farmacéutica es un polvo para solución inyectable, presentado en un frasco ámpula. El fabricante identificado es PiSA y el origen es México. El código ATC se extrajo explícitamente de Vademecum. La marca 'Penastim' se toma de la descripción original, aunque las fuentes web muestran otras marcas o versiones genéricas. El principal punto de conflicto es la clasificación taxonómica, ya que la subcategoría para antibióticos carbapenémicos no existe en la lista provista, forzando una elección imprecisa que reduce drásticamente la confianza.",
        "confianza_nivel": 2,
        "confianza_razonamiento": "La confianza es BAJA. El principal problema es la taxonomía proporcionada, que es INQUEBRANTABLE pero no contiene una subcategoría correcta para un antibiótico carbapenémico como Imipenem. Se seleccionó 'CEFALOSPORINAS' como el 'menos incorrecto' de los beta-lactámicos disponibles, pero esto es una imprecisión significativa forzada por las reglas. Además, existe una discrepancia entre la marca 'Penastim' de la descripción original y las marcas/genéricos encontrados en las fuentes web y la imagen. Otros datos como el principio activo, la concentración y el fabricante son consistentes.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ANTIBIOTICOS",
        "subcategoria": "CEFALOSPORINAS",
        "principio_activo": "Imipenem, Cilastatina",
        "concentracion": "500 mg/500 mg",
        "forma_farmaceutica": "Solución Inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": "México",
        "fabricante": "PiSA",
        "marca": "Penastim",
        "codigo_atc": "J01DH51",
        "cantidad_presentacion": 1,
        "contenido_neto": 1,
        "contenido_neto_unidad_Des": "Caja",
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 90
    },
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "El producto es un antibiótico inyectable cuyo principio activo es la combinación de Imipenem y Cilastatina, con una concentración de 500 mg/500 mg. La forma farmacéutica es solución inyectable. El código ATC J01DH51 se extrae explícitamente del contexto web (Vademecum). El fabricante PiSA se identifica en la imagen de referencia y el contexto web. La marca PENASTIM se extrae de la descripción original. Al ser un antibiótico, requiere receta médica.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "Los datos coinciden de forma unívoca entre la descripción original, el contexto web y la imagen de referencia, permitiendo una extracción precisa y sin ambigüedades de todos los atributos críticos.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ANTIBIOTICOS",
        "subcategoria": "OTROS ANTIBIOTICOS",
        "principio_activo": "IMIPENEM, CILASTATINA",
        "concentracion": "500 mg/500 mg",
        "forma_farmaceutica": "Solución Inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "PiSA",
        "marca": "PENASTIM",
        "codigo_atc": "J01DH51",
        "cantidad_presentacion": 1,
        "contenido_neto": None,
        "contenido_neto_unidad_Des": None,
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 75
    }
  },
  "0004": {
    "descripcion": "AMP BETAMETASONA 4 MGX1 FV",
    "gemini_2_5_pro": {
      "atrib": {
        "razonamiento": "El análisis se basa principalmente en la imagen del producto y la fuente de 'fahorro.com', que corresponden a 'Marca del Ahorro'. Los datos de principio activo, concentración, forma farmacéutica y presentación son explícitos y consistentes. La marca es 'Marca del Ahorro', una marca propia de la farmacia, pero el fabricante específico no se menciona. La clasificación taxonómica presenta un desafío: la Betametasona es un corticosteroide antiinflamatorio. La categoría más adecuada es 'ANALGESICOS Y ANTIINFLAMATORIOS'. Sin embargo, ninguna de las subcategorías obligatorias (Paracetamol, Ibuprofeno, etc.) es correcta. Para cumplir con la regla de 'PRECISIÓN ABSOLUTA', y ante la falta de una subcategoría adecuada en la taxonomía 'INQUEBRANTABLE', se asigna 'null' a la subcategoría para evitar un error crítico de clasificación. La información sobre el requisito de receta es contradictoria entre las fuentes, por lo que se establece como null.",
        "confianza_nivel": 3,
        "confianza_razonamiento": "La confianza es 'MEDIA'. Atributos clave como principio activo, concentración y forma son de confianza total (5/5) al estar explícitos en la imagen y fuentes. Sin embargo, la confianza general se reduce significativamente debido a la incapacidad de asignar una subcategoría taxonómica correcta según las reglas estrictas, lo que representa una limitación importante del sistema de clasificación provisto. Adicionalmente, la información contradictoria sobre la necesidad de receta médica entre fuentes confiables (Benavides vs. Curitek) obliga a un valor nulo, disminuyendo aún más la certeza del perfil completo del producto.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ANALGESICOS Y ANTIINFLAMATORIOS",
        "subcategoria": null,
        "principio_activo": "Betametasona",
        "concentracion": "4 mg/ml",
        "forma_farmaceutica": "Solución Inyectable",
        "requiere_recipe": null,
        "segmento_etario": "NO_DEFINIDO",
        "origen": null,
        "fabricante": null,
        "marca": "Marca del Ahorro",
        "codigo_atc": None,
        "cantidad_presentacion": 1,
        "contenido_neto": 1,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 1,
        "clasificacion_insumo_Des": None
      },
      "score": 70
    },
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "La imagen y el contexto web confirman que el producto es Betametasona 4 mg/mL en solución inyectable. La presentación es una caja con 1 ampolleta de 1 mL. La marca es Farmacias del Ahorro (marca propia/genérico). El origen es México, evidenciado por la bandera y el contexto de la farmacia. Al ser un corticoide inyectable, requiere receta médica.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "Todos los datos críticos (principio activo, concentración, forma farmacéutica, presentación y marca) están explícitos y corroborados tanto en la imagen de la caja como en el contexto web.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "ANALGESICOS Y ANTIINFLAMATORIOS",
        "subcategoria": "CORTICOIDES",
        "principio_activo": "Betametasona",
        "concentracion": "4 mg/ml",
        "forma_farmaceutica": "Solución Inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": "México",
        "fabricante": None,
        "marca": "Farmacias del Ahorro",
        "codigo_atc": None,
        "cantidad_presentacion": 1,
        "contenido_neto": 1,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 1,
        "clasificacion_insumo_Des": None
      },
      "score": 80
    }
  },
  "0008": {
    "descripcion": "AMP BETAMETASONA 8 MG X1 FV",
    "gemini_2_5_pro": None,
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "La imagen and el contexto web confirman que el producto es Betametasona de la 'Marca del Ahorro' (Farmacias del Ahorro). La caja indica claramente que es una solución inyectable con una concentración de 8 mg / 2 mL, y contiene 1 ampolleta de 2 mL junto con una jeringa. Al ser un corticoide sistémico inyectable, requiere receta médica. La bandera y la marca confirman su origen mexicano. Se clasifica como genérico al ser una marca propia de la farmacia.",
        "confianza_nivel": 5,
        "confianza_razonamiento": "Toda la información crítica (principio activo, concentración, forma farmacéutica, presentación, marca y origen) está explícitamente visible en la imagen de la caja y respaldada por el contexto web proporcionado.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "SISTEMA ENDOCRINO",
        "subcategoria": "CORTICOSTEROIDES",
        "principio_activo": "Betametasona",
        "concentracion": "8 mg/2 ml",
        "forma_farmaceutica": "Solución Inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": "México",
        "fabricante": "Farmacias del Ahorro",
        "marca": "Marca del Ahorro",
        "codigo_atc": None,
        "cantidad_presentacion": 1,
        "contenido_neto": 2,
        "contenido_neto_unidad_Des": "ml",
        "blister": 0,
        "generico": 1,
        "clasificacion_insumo_Des": None
      },
      "score": 85
    }
  },
  "001004002941515": {
    "descripcion": "Hidrocortisona 500mg inyectable (IV/IM) de Drotafarma",
    "gemini_2_5_pro": None,
    "gemini_3_1_pro": {
      "atrib": {
        "razonamiento": "La descripción indica explícitamente que el producto es 'Hidrocortisona 500mg inyectable' fabricado por 'Drotafarma'. Sin embargo, las imágenes de referencia muestran un destornillador (herramienta) y el contexto web es genérico o irrelevante, lo que representa una contradicción severa. Se extraen los datos basándose en el texto descriptivo. Dado que la taxonomía estricta no posee una categoría para corticoides sistémicos inyectables, se clasifica en la opción más cercana disponible (CORTICOIDES TOPICOS) bajo el dominio alopático.",
        "confianza_nivel": 1,
        "confianza_razonamiento": "Nivel nulo/bajo debido a la contradicción total entre la descripción textual (medicamento inyectable) y la evidencia visual (un destornillador), sumado a la falta de una subcategoría taxonómica exacta para corticoides sistémicos.",
        "dominio": "MEDICAMENTO_ALOPATICO",
        "categoria": "DERMATOLOGICOS",
        "subcategoria": "CORTICOIDES TOPICOS",
        "principio_activo": "Hidrocortisona",
        "concentracion": "500 mg",
        "forma_farmaceutica": "Inyectable",
        "requiere_recipe": 1,
        "segmento_etario": "NO_DEFINIDO",
        "origen": None,
        "fabricante": "Drotafarma",
        "marca": None,
        "codigo_atc": None,
        "cantidad_presentacion": None,
        "contenido_neto": None,
        "contenido_neto_unidad_Des": None,
        "blister": 0,
        "generico": 0,
        "clasificacion_insumo_Des": None
      },
      "score": 0
    }
  }
}

def obtener_taxonomias_estrictas():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
        tax = [f"- Dominio: {r[0]} | Categoria: {r[1]} | Subcategoria: {r[2]}" for r in cursor.fetchall()]
        conn.close()
        return "\n".join(tax)
    except Exception as e:
        return ""

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO') if atrib else 'MEDICAMENTO_ALOPATICO'
    es_med = dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']
    
    if not atrib:
        return 0
        
    tiene_cant = atrib.get('cantidad_presentacion') is not None
    
    if es_med:
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0 
        if not tiene_cant:
            return 0
            
    if atrib.get('principio_activo'): score += 15
    if atrib.get('concentracion'): score += 15
    if atrib.get('forma_farmaceutica'): score += 15
    if tiene_cant: score += 10
    if atrib.get('contenido_neto'): score += 5
    if atrib.get('origen'): score += 10
    if atrib.get('segmento_etario'): score += 10
    if atrib.get('fabricante'): score += 5
    if atrib.get('marca'): score += 5
    if atrib.get('codigo_atc'): score += 5
    if atrib.get('generico') in [1, 0]: score += 5
    
    return min(100, score)

def normalizar_segmento_etario(val):
    if not val: return "NO_DEFINIDO"
    v = str(val).upper().strip()
    if "ADULTO" in v: return "ADULTO"
    if "PEDIATRICO" in v or "INFANTIL" in v or "NIÑO" in v: return "PEDIATRICO"
    if "NEONATAL" in v or "BEBE" in v: return "NEONATAL"
    if "MIXTO" in v: return "MIXTO"
    if "GENERAL" in v or "TODO" in v: return "GENERAL"
    return "NO_DEFINIDO"

def llamar_openrouter_multimodal(context_json_str, taxonomias_existentes, model, imagenes_b64):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos y sus descripciones, contextos web y TAMBIÉN IMÁGENES de referencia que debes analizar junto con el texto.
    Tu único objetivo es la PRECISIÓN ABSOLUTA (Zero-Tolerance). Extraer un dato que no está explícitamente en la descripción, en el contexto web adjunto o en las imágenes de referencia es un ERROR CRÍTICO. Ante la menor duda, debes devolver null.

    Analiza TODOS los elementos proporcionados (texto y visuales) para extraer los siguientes atributos:
    - dominio (string OBLIGATORIO)
    - categoria (string OBLIGATORIO)
    - subcategoria (string OBLIGATORIO)
    - principio_activo (string o null si no aplica/es insumo)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)
    - cantidad_presentacion (int o null)
    - contenido_neto (float o null, formato numérico entero si no tiene decimales ej. 500)
    - contenido_neto_unidad_Des (string o null)
    - fabricante (string o null)
    - marca (string o null)
    - origen (string o null)
    - codigo_atc (string o null)
    - blister (1 o 0)
    - generico (1 o 0)
    - clasificacion_insumo_Des (string o null, ej: Inyectadora, Pañal)

    REGLAS ESTRICTAS ANTI-ALUCINACIÓN Y DE NEGOCIO:
    1. ATC: NO deduzcas el código ATC. Solo extráelo si aparece explícitamente.
    2. Sólidos vs Líquidos/Tópicos: 
       - Sólidos (Tabletas/Cápsulas): cantidad_presentacion = total de unidades (ej. 20), contenido_neto = 1, contenido_neto_unidad_Des = 'Caja' o 'Blister'.
       - Líquidos/Cremas/Pomadas: cantidad_presentacion = total de envases (ej. 1), contenido_neto = volumen/peso (ej. 120 o 500 sin decimales '.0'), contenido_neto_unidad_Des = 'ml' o 'g'.
    3. Forma Farmacéutica: Simplifica formas complejas a su familia base (ej. "Comprimido de liberación prolongada" -> "Comprimido"). MANTÉN la vía de administración si es crítica (ej. "Solución Oftálmica").
    4. Marca / Fabricante / Origen: Si no hay información explícita, usa null. NO asumas 'Genérico' como marca. Si ves el laboratorio en la caja de la imagen, utilízalo.
    5. Segmento Etario: NO lo deduzcas sin evidencia (infantil, niños, pediátrico, adulto). Ante la duda, null.

    REGLA DE TAXONOMIA (INQUEBRANTABLE):
    {taxonomias_existentes}
    
    NIVELES DE CONFIANZA (OBLIGATORIOS):
    Debes autoevaluar tu clasificación usando un "confianza_nivel" (entero del 1 al 5) y explicarlo en "confianza_razonamiento".
    5 - TOTAL: Dato explícito, inequívoco, sin contradicciones en el contexto web o imagen.
    4 - ALTA: Se deduce lógicamente con total certeza científica, aunque haya diferencias menores en campos no críticos.
    3 - MEDIA: Información suficiente pero con discrepancias entre sitios o ambigüedad leve.
    2 - BAJA: Inferencias o aproximaciones por información escasa o contradictoria.
    1 - NULA: Falta de información crítica.
    
    Devuelve ÚNICAMENTE un array JSON válido con este formato exacto:
    [
      {{
        "registro": {{"codbarras": "...", "descripcion_original": "..."}},
        "atributos_nuevos_consolidados": {{"razonamiento": "...", "confianza_nivel": 5, "confianza_razonamiento": "...", "dominio": "...", "categoria": "...", "subcategoria": "...", "principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": null, "origen": null, "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR (Contexto Web Incluido):
    {context_json_str}
    """
    
    content_payload = [{"type": "text", "text": prompt}]
    for b64 in imagenes_b64:
        content_payload.append({"type": "image_url", "image_url": {"url": b64}})
        
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.1
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            usage = result.get('usage', {})
            content = result['choices'][0]['message']['content']
            if not content:
                refusal = result['choices'][0]['message'].get('refusal')
                reasoning = result['choices'][0]['message'].get('reasoning')
                print(f"    [Aviso] Modelo {model} no retornó content. Refusal: {refusal} | Reasoning: {reasoning}")
                return None, usage
                
            if content.startswith("```json"): content = content[7:]
            if content.endswith("```"): content = content[:-3]
            return json.loads(content.strip()), usage
    except Exception as e:
        print(f"    Error {model}: {e}")
        return None, {}

def main():
    print("INICIANDO FASE 2: Inferencia de Gemini 2.5 Flash y Consolidación de Reporte")
    
    input_path = "scratch/scraping_multimodal_results.json"
    if not os.path.exists(input_path):
        print(f"Error: No se encontró el archivo {input_path}.")
        return
        
    with open(input_path, "r", encoding="utf-8") as f:
        lote_scraping = json.load(f)
        
    taxonomias_str = obtener_taxonomias_estrictas()
    
    model_id_flash = "google/gemini-2.5-flash"
    
    precios = {
        "gemini_2_5_flash": {"in": 0.30 / 1e6, "out": 2.50 / 1e6},
        "gemini_2_5_pro": {"in": 1.25 / 1e6, "out": 10.00 / 1e6},
        "gemini_3_1_pro": {"in": 2.00 / 1e6, "out": 12.00 / 1e6}
    }
    
    resultados_finales = {}
    
    for item in lote_scraping:
        ean = item["ean"]
        desc = item["descripcion"]
        fuentes_web = item["fuentes_web"]
        imagenes_b64 = item["imagenes_b64"]
        
        print(f"\nProcesando EAN {ean} - {desc} (Fuentes: {len(fuentes_web)}, Imágenes: {len(imagenes_b64)})")
        
        # Estructura limpia para enviar a la IA
        context_block = [{
            "registro": {"codbarras": ean, "descripcion_original": desc},
            "fuentes_web": fuentes_web
        }]
        
        # Obtener datos de la copia de seguridad de Pro
        backup_item = PRO_RESULTS_BACKUP.get(ean, {"descripcion": desc})
        
        res_ean = {
            "descripcion": desc,
            "gemini_2_5_pro": backup_item.get("gemini_2_5_pro"),
            "gemini_3_1_pro": backup_item.get("gemini_3_1_pro")
        }
        
        # Llamar a Gemini 2.5 Flash
        print(f"  Evaluando con gemini_2_5_flash...")
        res_txt, usage = llamar_openrouter_multimodal(json.dumps(context_block, indent=2), taxonomias_str, model_id_flash, imagenes_b64)
        
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        
        costo_flash = (prompt_tokens * precios["gemini_2_5_flash"]["in"]) + (completion_tokens * precios["gemini_2_5_flash"]["out"])
        
        if res_txt and len(res_txt) > 0:
            atrib = res_txt[0].get('atributos_nuevos_consolidados', {})
            score = calcular_score_calidad(atrib)
            atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
            res_ean["gemini_2_5_flash"] = {
                "atrib": atrib,
                "score": score,
                "tokens_in": prompt_tokens,
                "tokens_out": completion_tokens,
                "costo": costo_flash
            }
            print(f"    [Flash Éxito] Score: {score} | Confianza: {atrib.get('confianza_nivel')} | Costo: ${costo_flash:.6f}")
        else:
            res_ean["gemini_2_5_flash"] = {
                "atrib": None,
                "score": 0,
                "tokens_in": prompt_tokens,
                "tokens_out": completion_tokens,
                "costo": costo_flash,
                "error": True
            }
            print(f"    [Flash Fallo/Rechazo] Costo: ${costo_flash:.6f}")
            
        # Extrapolar costos para los modelos Pro ya que usan exactamente el mismo prompt y contexto
        # Para pro_2_5
        if res_ean["gemini_2_5_pro"]:
            # Usar los mismos prompt_tokens y aproximar completion_tokens
            tokens_in_pro = prompt_tokens
            tokens_out_pro = completion_tokens  # aproximación muy cercana
            costo_pro_25 = (tokens_in_pro * precios["gemini_2_5_pro"]["in"]) + (tokens_out_pro * precios["gemini_2_5_pro"]["out"])
            res_ean["gemini_2_5_pro"]["tokens_in"] = tokens_in_pro
            res_ean["gemini_2_5_pro"]["tokens_out"] = tokens_out_pro
            res_ean["gemini_2_5_pro"]["costo"] = costo_pro_25
            
        # Para pro_3_1
        if res_ean["gemini_3_1_pro"]:
            tokens_in_pro = prompt_tokens
            tokens_out_pro = completion_tokens
            costo_pro_31 = (tokens_in_pro * precios["gemini_3_1_pro"]["in"]) + (tokens_out_pro * precios["gemini_3_1_pro"]["out"])
            res_ean["gemini_3_1_pro"]["tokens_in"] = tokens_in_pro
            res_ean["gemini_3_1_pro"]["tokens_out"] = tokens_out_pro
            res_ean["gemini_3_1_pro"]["costo"] = costo_pro_31
            
        resultados_finales[ean] = res_ean

    # Guardar reporte comparativo consolidado
    with open("scratch/resultados_comparativa_multimodal.json", "w", encoding="utf-8") as f:
        json.dump(resultados_finales, f, indent=2, ensure_ascii=False)

    print("\n--- RESULTADOS FINALES: COMPARATIVA DE LOS 3 MODELOS ---")
    for ean, res in resultados_finales.items():
        print(f"\nEAN: {ean} - {res['descripcion']}")
        for model_key in ["gemini_2_5_flash", "gemini_2_5_pro", "gemini_3_1_pro"]:
            m_res = res.get(model_key)
            if m_res and m_res.get('atrib'):
                at = m_res['atrib']
                print(f"  {model_key}: Score {m_res['score']}, Confianza Nivel {at.get('confianza_nivel')} (Costo: ${m_res.get('costo', 0.0):.6f})")
            else:
                cost = m_res.get('costo', 0.0) if m_res else 0.0
                print(f"  {model_key}: NULL / Rechazado o Error (Costo: ${cost:.6f})")

if __name__ == "__main__":
    main()
