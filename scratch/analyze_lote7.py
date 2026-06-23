import collections
import re

def analyze_lote7():
    with open('scratch/compact_400_7.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    manufacturers = collections.Counter()
    
    for line in lines:
        if '|' not in line: continue
        parts = line.strip().split('|')
        desc_concat = parts[1]
        
        # Split by pipe to get individual descriptions
        descs = desc_concat.split(' | ')
        for desc in descs:
            desc = desc.strip()
            # Often the manufacturer is the last word or in parentheses at the end
            match = re.search(r'\b([A-Z&]+)\s*\)?$', desc)
            if match:
                word = match.group(1)
                # Ignore common non-manufacturer words at the end
                if word not in ['TAB', 'CAP', 'COMP', 'REC', 'MG', 'ML', 'GR', 'SUSP', 'JBE', 'AMP', 'CREMA', 'GEL', 'UNG', 'OFT', 'VAG', 'ORAL', 'TABLETAS', 'MCG', 'CAPSULAS']:
                    manufacturers[word] += 1
            
            # also check parentheses anywhere
            parens = re.findall(r'\(([A-Z&\s\.\-]+)\)', desc)
            for p in parens:
                manufacturers[p.strip()] += 1

    print("Most common potential manufacturers/brands in Lote 7:")
    for k, v in manufacturers.most_common(50):
        if v > 2 and len(k) > 2:
            print(f"{k}: {v}")

if __name__ == "__main__":
    analyze_lote7()
