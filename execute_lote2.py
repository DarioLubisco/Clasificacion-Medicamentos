import os
import re

def execute_sql_chunks(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract updates
    updates = re.findall(r"UPDATE Procurement\.por_aprobacion_equivalencias SET .*?;", content)
    print(f"Total updates found: {len(updates)}")
    
    chunk_size = 100
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i+chunk_size]
        sql = "BEGIN TRANSACTION;\n" + "\n".join(chunk) + "\nCOMMIT;"
        
        # Save chunk to temp file for debugging if needed
        chunk_file = f"chunk_lote2_{i//chunk_size}.sql"
        with open(chunk_file, "w", encoding="utf-8") as cf:
            cf.write(sql)
            
        print(f"Executing chunk {i//chunk_size + 1} ({len(chunk)} updates)...")
        # In a real scenario I would use mcp_mssql-server_execute_sql
        # But since I am the agent, I will output the command for the next step.

if __name__ == "__main__":
    execute_sql_chunks("actualizacion_lote2_v10.sql")
