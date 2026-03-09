import sys
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from src.config import EMPTY, WALL, WAREHOUSE, ENTRANCE, EXIT
from src.config import NUM_OBJECTS, BATTERY_INITIAL

class Renderer:
    def __init__(self, env):
        self.env = env
        plt.ion()  # Attiva la modalità interattiva di matplotlib
        
        self.fig, (self.ax_map, self.ax_bat) = plt.subplots(
            1, 2, 
            figsize=(12, 8), 
            gridspec_kw={'width_ratios': [3, 1]} # Rapporto di larghezza 3:1
        )
        
        # --- NUOVE VARIABILI PER IL CONTROLLO DEL TEMPO E DELLA PAUSA ---
        self.pause_time = 0.05  # Velocità iniziale (secondi per tick)
        self.paused = False     # Stato di pausa
        
        # Colleghiamo l'evento di pressione dei tasti alla nostra funzione
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        # ----------------------------------------------------------------

        # Mappa colori in linea con le richieste del progetto
        self.cmap = mcolors.ListedColormap(['white', '#404040', '#4a90d9', '#2ecc71', '#e74c3c'])
        self.bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
        self.norm = mcolors.BoundaryNorm(self.bounds, self.cmap.N)
        
        # Colori distinti per i 5 agenti
        self.agent_colors = ['#ff00ff', '#00ffff', '#0000ff', '#800080', '#8b4513'] 

    def on_key_press(self, event):
        """Gestisce gli input da tastiera per controllare la simulazione."""
        if event.key == ' ':  # Barra spaziatrice per Pausa/Ripresa
            self.paused = not self.paused
            stato = "IN PAUSA" if self.paused else "RIPRESA"
            print(f"\n*** Simulazione {stato} ***")
            
        elif event.key == 'up':  # Freccia SU per accelerare
            self.pause_time = max(0.001, self.pause_time / 1.5)
            print(f"Velocità aumentata (pausa: {self.pause_time:.3f}s)")
            
        elif event.key == 'down':  # Freccia GIÙ per rallentare
            self.pause_time = min(2.0, self.pause_time * 1.5)
            print(f"Velocità diminuita (pausa: {self.pause_time:.3f}s)")
            
        elif event.key == 'escape':  # Tasto ESC per terminare tutto
            print("\n*** SIMULAZIONE TERMINATA DRASTICAMENTE DALL'UTENTE ***")
            plt.close('all') # Chiude la finestra grafica
            sys.exit(0)      # Uccide il processo Python all'istante

    def draw(self, agents, tick):
        # Puliamo entrambi i grafici ad ogni frame
        self.ax_map.clear()
        self.ax_bat.clear()
        
        # === 1. DISEGNO MAPPA (ax_map) ===
        self.ax_map.imshow(self.env.grid, cmap=self.cmap, norm=self.norm)
        
        for r, c in self.env._objects_truth:
            self.ax_map.plot(c, r, 'o', color='orange', markersize=8, markeredgecolor='black')
            
        for agent in agents:
            color_idx = (agent.id - 1) % len(self.agent_colors)
            marker_shape = 's' if agent.carrying else 'o'
            
            self.ax_map.plot(agent.pos[1], agent.pos[0], marker=marker_shape, 
                         color=self.agent_colors[color_idx], markersize=10, markeredgecolor='black')
            self.ax_map.text(agent.pos[1], agent.pos[0], str(agent.id), 
                         color='white', ha='center', va='center', fontsize=8, fontweight='bold')

        # Abbiamo aggiunto un piccolo hint nel titolo per ricordare i comandi
        self.ax_map.set_title(f"Tick: {tick} | Oggetti: {self.env.delivered}/{NUM_OBJECTS} | Pausa: [Spazio]")
        self.ax_map.set_xticks(range(self.env.n))
        self.ax_map.set_yticks(range(self.env.n))
        self.ax_map.set_xticklabels([])
        self.ax_map.set_yticklabels([])
        self.ax_map.grid(color='gray', linestyle=':', linewidth=0.5)
        
        # === 2. DISEGNO BATTERIE (ax_bat) ===
        sorted_agents = sorted(agents, key=lambda a: a.id)
        
        agent_ids = [str(a.id) for a in sorted_agents]
        batteries = [max(0, a.battery) for a in sorted_agents]
        bar_colors = [self.agent_colors[(a.id - 1) % len(self.agent_colors)] for a in sorted_agents]
        
        bars = self.ax_bat.bar(agent_ids, batteries, color=bar_colors, edgecolor='black')
        
        self.ax_bat.set_title("Stato Batteria\nVelocità: [↑] [↓]")
        self.ax_bat.set_xlabel("ID Agente")
        self.ax_bat.set_ylabel("Energia")
        self.ax_bat.set_ylim(0, BATTERY_INITIAL)
        
        for bar, battery in zip(bars, batteries):
            height = bar.get_height()
            self.ax_bat.text(bar.get_x() + bar.get_width()/2., height + 5,
                            f'{int(battery)}', ha='center', va='bottom', fontsize=8)

        # === 3. GESTIONE DEL TEMPO E DELLA PAUSA ===
        # Pausa standard dipendente dalla velocità impostata
        plt.pause(self.pause_time)
        
        # Se l'utente ha premuto Spazio, entra in un loop finché paused = True.
        # Usa plt.pause(0.1) nel loop per mantenere la finestra responsiva ai click/tasti
        while self.paused:
            plt.pause(0.1)