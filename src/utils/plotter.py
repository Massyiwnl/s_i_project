import pandas as pd
import matplotlib.pyplot as plt
import os


def create_visual_table(csv_path, output_png_path):
    """
    Legge un file CSV e genera una tabella grafica salvata come PNG.

    Args:
        csv_path: percorso del file CSV di input.
        output_png_path: percorso del file PNG di output.
    """
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.axis('off')

    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#4c72b0')
        elif row > 0:
            cell.set_facecolor('#f2f2f2' if row % 2 == 0 else 'white')

    dir_path = os.path.dirname(output_png_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    plt.savefig(output_png_path, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"Tabella visiva salvata in: {output_png_path}")


# FIX: la versione originale chiamava create_visual_table() a livello di modulo
# (ultima riga del file, non protetta da __main__). Questo causava l'esecuzione
# immediata della funzione ad ogni import del modulo, sollevando FileNotFoundError
# se il CSV non esisteva ancora (cioe' prima di eseguire almeno una simulazione).
# L'errore veniva catturato silenziosamente dall'except Exception in main.py,
# bloccando l'intera sezione di analisi senza avvisi espliciti.
if __name__ == '__main__':
    create_visual_table(
        'outputs/logs/run_A_seed42_agents.csv',
        'outputs/logs/run_A_seed42_table.png'
    )