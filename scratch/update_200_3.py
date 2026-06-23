import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

updates = [
    # FARMAGENIK
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'FARMAGENIK' WHERE codbarras IN ('112244009159', '112255006185', '112255006192', '112255006208', '112255006239', '112345202237', '112345202244', '112552575773', '25526479') AND fabricante_Des IS NULL;",
    # EMIRATES GROUP
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'EMIRATES GROUP' WHERE codbarras = '123' AND fabricante_Des IS NULL;",
    # ZAKIMED
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ZAKIMED' WHERE codbarras IN ('124865423948', '1254896321544') AND fabricante_Des IS NULL;",
    # DROTAFARMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'DROTAFARMA' WHERE codbarras IN ('12565454586', '14894642', '2260000179177', '2260000193401', '2260000201656', '2260000201663', '2260000201687', '25026315', '259746262') AND fabricante_Des IS NULL;",
    # BALAXI
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BALAXI' WHERE codbarras IN ('16975714180458', '16975714183060') AND fabricante_Des IS NULL;",
    # ALESS PHARMACEUTICALS
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ALESS PHARMACEUTICALS' WHERE codbarras = '17597758001262' AND fabricante_Des IS NULL;",
    # DISTRILAB
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'DISTRILAB' WHERE codbarras IN ('17598252000010', '17598252101571', '17598252101830') AND fabricante_Des IS NULL;",
    # BIOVENEZUELA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BIOVENEZUELA' WHERE codbarras = '18904030979406' AND fabricante_Des IS NULL;",
    # TIARES
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'TIARES' WHERE codbarras IN ('18904187829326', '18904187884240', '196852522460', '196852644438', '197644273638', '198168687673', '198715024036', '198715103229', '198715171839', '198715184341', '198715202489', '198715206036', '198715246605', '198715320800', '198715553222', '198715691771', '198715871241', '198715930504', '198715945935', '198715989878', '199284125407', '199284287013', '199284627123', '199284648449', '199284724006') AND fabricante_Des IS NULL;",
    # BC GROUPMEDICAL
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BC GROUPMEDICAL' WHERE codbarras = '18907010003986' AND fabricante_Des IS NULL;",
    # BUKA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BUKA' WHERE codbarras IN ('212810862482', '212810862550', '212810862628', '212810862796', '212810862864', '675696259942', '675696259966', '675696259973', '675696259997', '675696260009', '675696260023', '675696260030', '675696260054', '675696260061', '675696260078', '675696260085', '675696260115') AND fabricante_Des IS NULL;",
    # BRIX MEDIC
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BRIX MEDIC' WHERE codbarras IN ('2260000031437', '2260000200369', '2260000200420') AND fabricante_Des IS NULL;",
    # ADN
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ADN' WHERE codbarras = '2260000074311' AND fabricante_Des IS NULL;",
    # ANGELUS
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ANGELUS' WHERE codbarras = '2260000198710' AND fabricante_Des IS NULL;",
    # FARMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'FARMA' WHERE codbarras = '301490039373' AND fabricante_Des IS NULL;",
    # MED-AID
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'MED-AID' WHERE codbarras IN ('3170472452010', '3170472453011') AND fabricante_Des IS NULL;",
    # GALDERMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'GALDERMA' WHERE codbarras IN ('3499320000765', '3499320002523') AND fabricante_Des IS NULL;",
    # MALLEN
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'MALLEN' WHERE codbarras = '3499320004794' AND fabricante_Des IS NULL;",
    # URGO
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'URGO' WHERE codbarras = '3664492000602' AND fabricante_Des IS NULL;",
    # SANOFI
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'SANOFI' WHERE codbarras IN ('3664798065145', '3664798066104', '3664798079999') AND fabricante_Des IS NULL;",
    # B BRAUN
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'B BRAUN' WHERE codbarras IN ('4030539128247', '4030539206723') AND fabricante_Des IS NULL;",
    # GRUNENTHAL
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'GRUNENTHAL' WHERE codbarras = '4032129015050' AND fabricante_Des IS NULL;",
    # BAYER
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BAYER' WHERE codbarras IN ('4057598022767', '4057598024884') AND fabricante_Des IS NULL;",
    # GEROPHARM
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'GEROPHARM' WHERE codbarras = '4607008363265' AND fabricante_Des IS NULL;",
    # INDAR
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'INDAR' WHERE codbarras = '4820014770517' AND fabricante_Des IS NULL;",
    # BIOPHARMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BIOPHARMA' WHERE codbarras = '4823091000980' AND fabricante_Des IS NULL;",
    # GSK
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'GSK' WHERE codbarras IN ('5010706008359', '5010706009271', '5010706009295', '5050278003666') AND fabricante_Des IS NULL;",
    # UNIPHARMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'UNIPHARMA' WHERE codbarras IN ('5060560910602', '5060560910732', '5060560911920') AND fabricante_Des IS NULL;",
    # BLUEPHARMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BLUEPHARMA' WHERE codbarras IN ('5189766', '5306568', '5368105') AND fabricante_Des IS NULL;",
    # GEDEON RICHTER
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'GEDEON RICHTER' WHERE codbarras IN ('5997001361887', '5997001362723') AND fabricante_Des IS NULL;",
    # KMPLUS
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'KMPLUS' WHERE codbarras IN ('6034387234820', '6035834982103', '6037096019856') AND fabricante_Des IS NULL;",
    # H&M
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'H&M' WHERE codbarras IN ('632627843366', '632627843373', '632627843380', '632627843397', '632627843403', '632627843410', '632627843427', '632627843434', '632627843441', '632627843458', '632627843465', '632627843472', '632627843496', '632627843502', '632627843519', '632627843526', '632627843533', '632627843540', '632627843557', '632627843564', '632627843571', '632627843588', '632627843595', '632627843601') AND fabricante_Des IS NULL;",
    # EL MORRO
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'EL MORRO' WHERE codbarras IN ('652931975614', '652931975638', '652931975645', '652931975652', '652931975836') AND fabricante_Des IS NULL;"
]

def update_lote3():
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    try:
        for sql in updates:
            cursor.execute(sql)
        print("Lote 3 procesado y campos de fabricante actualizados.")
        
        # Ahora marcamos los 200 como procesados (fase 1)
        codbarras_procesados = []
        with open('scratch/compact_200_3.txt', 'r') as f:
            for line in f:
                if '|' in line:
                    codbarras_procesados.append(line.split('|')[0])
                    
        if codbarras_procesados:
            placeholders = ','.join(['?'] * len(codbarras_procesados))
            sql = f"UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase1 = 1 WHERE codbarras IN ({placeholders})"
            cursor.execute(sql, codbarras_procesados)
            print(f"Marcados {len(codbarras_procesados)} registros como procesados (procesado_fase1 = 1).")
            
    except Exception as e:
        print("Error en actualizacion lote 3:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    update_lote3()
