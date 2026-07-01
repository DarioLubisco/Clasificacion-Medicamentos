import sys

def clean_markdown(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        if line.startswith('| Atributo |'):
            new_lines.append('| Atributo | DeepSeek Pro | DeepSeek Flash |\n')
        elif line.startswith('|---|'):
            new_lines.append('|---|---|---|\n')
        elif line.startswith('| **'):
            # It's a data row.
            # Format: | **attr** | gemma_val | d_pro_val | d_flash_val |
            parts = line.split('|')
            if len(parts) >= 6:
                # parts[0] is empty (before first |)
                # parts[1] is **attr**
                # parts[2] is gemma_val
                # parts[3] is d_pro_val
                # parts[4] is d_flash_val
                # parts[5] is empty (after last |)
                attr = parts[1]
                pro = parts[3]
                flash = parts[4]
                new_lines.append(f'|{attr}|{pro}|{flash}|\n')
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    clean_markdown(sys.argv[1])
