import json

with open("scratch/batch_100.json", "r") as f:
    data = json.load(f)

for item in data:
    print(f"{item['EAN']}|{item['Desc']}|A:{item['Act']}|C:{item['Con']}|F:{item['Form']}|M:{item['Marca']}|Fa:{item['Fab']}")
