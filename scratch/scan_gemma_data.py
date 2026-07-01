import os
import json
import glob
import pandas as pd

gemma_files = []

# Scan JSON files
json_files = glob.glob("**/*.json", recursive=True)
for f in json_files:
    if "node_modules" in f or ".git" in f or ".gemini" in f:
        continue
    try:
        with open(f, "r", encoding="utf-8") as fp:
            content = fp.read()
            if "gemma" in content.lower():
                gemma_files.append(f)
    except Exception:
        pass

# Scan Excel files
excel_files = glob.glob("**/*.xlsx", recursive=True)
for f in excel_files:
    if "node_modules" in f or ".git" in f or ".gemini" in f:
        continue
    try:
        # Load sheets and look for "gemma"
        xls = pd.ExcelFile(f)
        found = False
        for sheet in xls.sheet_names:
            df = pd.read_excel(f, sheet_name=sheet)
            # check if "gemma" is in columns or any cell
            col_match = any("gemma" in str(col).lower() for col in df.columns)
            cell_match = df.astype(str).apply(lambda x: x.str.contains("gemma", case=False)).any().any()
            if col_match or cell_match:
                found = True
                break
        if found:
            gemma_files.append(f)
    except Exception:
        pass

print("GEMMA_FILES_FOUND:")
for gf in gemma_files:
    print(gf)
