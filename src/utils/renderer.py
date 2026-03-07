import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from src.config import EMPTY, WALL, WAREHOUSE, ENTRANCE, EXIT

class Renderer:
    def __init__(self, env):
        self.env = env
        plt.ion()  # Attiva la modalità interattiva di matplotlib
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        
        # Mappa colori in linea con le richieste del progetto
        self.cmap = mcolors.ListedColormap(['white', '#404040', '#4a90d9', '#2ecc71', '#e74c3c'])
        self.bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
        self.norm = mcolors.BoundaryNorm(self.bounds, self.cmap.N)
        
        # Colori distinti per i 5 agenti
        self.agent_colors = ['#ff00ff', '#00ffff', '#0000ff', '#800080', '#8b4513'] 

    def draw(self, agents, tick):
        self.ax.clear()
        
        # 1. Disegna la mappa statica
        self.ax.imshow(self.env.grid, cmap=self.cmap, norm=self.norm)
        
        # 2. Disegna gli oggetti (Ground Truth) come pallini arancioni
        for r, c in self.env._objects_truth:
            self.ax.plot(c, r, 'o', color='orange', markersize=8, markeredgecolor='black')
            
        # 3. Disegna gli agenti
        for agent in agents:
            color_idx = (agent.id - 1) % len(self.agent_colors)
            # Quadrato se trasporta un oggetto, Cerchio se è scarico
            marker_shape = 's' if agent.carrying else 'o'
            
            self.ax.plot(agent.pos[1], agent.pos[0], marker=marker_shape, 
                         color=self.agent_colors[color_idx], markersize=10, markeredgecolor='black')
            # Scrive l'ID dell'agente al centro
            self.ax.text(agent.pos[1], agent.pos[0], str(agent.id), 
                         color='white', ha='center', va='center', fontsize=8, fontweight='bold')

        # 4. Formattazione asse e titolo
        self.ax.set_title(f"Tick: {tick} | Oggetti Consegnati: {self.env.delivered}/{len(self.env._objects_truth) + self.env.delivered}")
        self.ax.set_xticks(range(self.env.n))
        self.ax.set_yticks(range(self.env.n))
        self.ax.set_xticklabels([])
        self.ax.set_yticklabels([])
        self.ax.grid(color='gray', linestyle=':', linewidth=0.5)
        
        # Aggiorna il frame
        plt.pause(0.01)