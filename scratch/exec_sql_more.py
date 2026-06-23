import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

queries = [
    # BUKA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BUKA' WHERE codbarras IN ('0021241259262', '0675696259942', '0675696259973', '0675696260023', '0675696260030', '0675696260061', '0675696260078', '0675696260085', '0675696260115', '0675696260122', '0675696260139', '0675696260146', '0675696260153', '0675696260184', '0675696260191', '0675696260214', '0675696260597') AND fabricante_Des IS NULL;",
    # PHARMALAB
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'PHARMALAB' WHERE codbarras IN ('0677144727287', '0677144727331', '0677144727379') AND fabricante_Des IS NULL;",
    # LATTAN MEDIC
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'LATTAN MEDIC' WHERE codbarras IN ('0000020000264', '0720524031075', '0720524031105', '0720524031129', '0720524031198', '0720524031228', '0756029628274', '0756029628342') AND fabricante_Des IS NULL;",
    # FAHD
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'FAHD' WHERE codbarras IN ('0721688177326', '0736372795625', '0736372795632', '0736372795656', '0736372795762') AND fabricante_Des IS NULL;",
    # KMPLUS
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'KMPLUS' WHERE codbarras IN ('0724373570631', '07301700649586', '0730170648961', '0730170649012', '0730170649043', '0730170649098', '0730170649173', '0730170649227', '0730170649241', '0730170649258', '0730170649265', '0730170649326', '0730170649425', '0730170649470', '0730170649487', '0730170649517', '0730170649548', '0730170649562', '0730170649579', '0730170649586', '0730170649593', '073017064970') AND fabricante_Des IS NULL;",
    # ARTE MEDICO
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ARTE MEDICO' WHERE codbarras IN ('0000000072410', '0000000093491', '0731946648536', '0731946648635', '08906051293052', '08906051293076', '0890605129309', '08906051293090') AND fabricante_Des IS NULL;",
    # GLOBAL MEDIC
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'GLOBAL MEDIC' WHERE codbarras IN ('0736372230096', '0736372230157', '0736372230232', '0736372230249', '0736372827241', '0736372827388', '0736372827425', '0745604632867', '0764451895294', '0764451895386', '0764451895423', '0764451895447', '0764451895478', '0764451895508') AND fabricante_Des IS NULL;",
    # H&M
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'H&M' WHERE codbarras IN ('0632627843366', '0632627843397', '0632627843403', '0632627843410', '0632627843427', '0632627843458', '0632627843465', '0632627843472', '0632627843496', '0632627843502', '0632627843519', '0632627843526', '0632627843533', '0632627843557', '0632627843564', '0632627843571', '0632627843588', '0632627843595', '0632627843601', '0736372692108', '0736372692153', '0736372692184', '0736372692191', '0736372692207', '0736372692214', '0736372692238', '0736372692245', '0736372692269', '0736372692306', '0736372722294', '0736372722317', '0736372722324', '0736372722331', '0736372722348', '0736372722355', '0736372722379', '0736372722386', '0736372722416', '0736372722423', '0736372722461', '0736372722492', '0736372722508', '0736372722515', '0736372722553', '0736372722584', '0793969044320', '0793969044337', '0793969044344', '0793969044351', '0793969044368', '0793969044375', '0793969044382', '0793969044399', '0793969044405', '0793969044412', '0793969785162') AND fabricante_Des IS NULL;",
    # BIOSANO
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BIOSANO' WHERE codbarras IN ('000000000130', '0780006114023') AND fabricante_Des IS NULL;",
    # DROTAFARMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'DROTAFARMA' WHERE codbarras IN ('0000000104098', '001004002941515') AND fabricante_Des IS NULL;",
    # ZAKIMED
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ZAKIMED' WHERE codbarras IN ('0000000107839', '0000000163750', '0000000163774') AND fabricante_Des IS NULL;",
    # ALFA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ALFA' WHERE codbarras = '0000000195911' AND fabricante_Des IS NULL;",
    # RTM
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'RTM' WHERE codbarras = '0000000206815' AND fabricante_Des IS NULL;",
    # FARMAGENIK
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'FARMAGENIK' WHERE codbarras = '0000025526479' AND fabricante_Des IS NULL;",
    # MEDICAL CARE
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'MEDICAL CARE' WHERE codbarras = '0614143659027' AND fabricante_Des IS NULL;",
    # EL MORRO
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'EL MORRO' WHERE codbarras = '0652931975645' AND fabricante_Des IS NULL;",
    # SNC PHARMA
    "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'SNC PHARMA' WHERE codbarras IN ('0788070698616', '0788070698623', '0788364681331') AND fabricante_Des IS NULL;"
]

try:
    for q in queries:
        cursor.execute(q)
    print("Ejecucion exitosa de Fase 1 para 200 items mas.")
except Exception as e:
    print("Error:", e)
conn.close()
