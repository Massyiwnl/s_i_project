import pandas as pd
import matplotlib.pyplot as plt
import os

def create_visual_table(csv_path, output_png_path):
    # Legge il file CSV
    df = pd.read_csv(csv_path)
    
    # Crea la figura grafica
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.axis('off') # Nasconde gli assi cartesiani
    
    # Crea la tabella vera e propria
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5) # Allarga le celle
    
    # Colora l'intestazione di blu e alterna i colori delle righe
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#4c72b0')
        elif row > 0:
            cell.set_facecolor('#f2f2f2' if row % 2 == 0 else 'white')
            
    # Salva la tabella come immagine
    os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
    plt.savefig(output_png_path, bbox_inches='tight', dpi=300)
    print(f"Tabella visiva salvata in: {output_png_path}")

# Esempio di utilizzo:
create_visual_table('outputs/logs/run_A_seed42_agents.csv', 'outputs/logs/run_A_seed42_table.png')