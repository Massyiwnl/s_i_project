import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# FIX: rimossi EMPTY e WALL che erano importati ma mai usati nel renderer.
# La colormap gestisce i valori numerici della griglia direttamente.
from src.config import WAREHOUSE, ENTRANCE, EXIT
from src.config import NUM_OBJECTS, BATTERY_INITIAL


class Renderer:
    def __init__(self, env):
        self.env = env
        plt.ion()

        self.fig, (self.ax_map, self.ax_bat) = plt.subplots(
            1, 2,
            figsize=(12, 8),
            gridspec_kw={'width_ratios': [3, 1]}
        )

        self.pause_time = 0.05
        self.paused = False

        # FIX: flag per uscita pulita.
        # La versione originale usava sys.exit(0) su ESC, che terminava
        # il processo Python istantaneamente senza tornare al loop di main.py,
        # impedendo l'esecuzione di logger.dump e la perdita di tutti i dati.
        self.should_quit = False

        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)

        self.cmap = mcolors.ListedColormap(['white', '#404040', '#4a90d9', '#2ecc71', '#e74c3c'])
        self.bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
        self.norm = mcolors.BoundaryNorm(self.bounds, self.cmap.N)

        self.agent_colors = ['#ff00ff', '#00ffff', '#0000ff', '#800080', '#8b4513']

    def on_key_press(self, event):
        """Gestisce gli input da tastiera per controllare la simulazione."""
        if event.key == ' ':
            self.paused = not self.paused
            stato = "IN PAUSA" if self.paused else "RIPRESA"
            print(f"\n*** Simulazione {stato} ***")

        elif event.key == 'up':
            self.pause_time = max(0.001, self.pause_time / 1.5)
            print(f"Velocita' aumentata (pausa: {self.pause_time:.3f}s)")

        elif event.key == 'down':
            self.pause_time = min(2.0, self.pause_time * 1.5)
            print(f"Velocita' diminuita (pausa: {self.pause_time:.3f}s)")

        elif event.key == 'escape':
            # FIX: imposta il flag invece di chiamare sys.exit(0).
            # main.py controlla should_quit dopo ogni draw() e usa break
            # per uscire dal loop in modo pulito, garantendo logger.dump.
            print("\n*** Uscita richiesta — salvataggio log in corso... ***")
            self.should_quit = True

    def draw(self, agents, tick):
        self.ax_map.clear()
        self.ax_bat.clear()

        # === 1. MAPPA ===
        self.ax_map.imshow(self.env.grid, cmap=self.cmap, norm=self.norm)

        for r, c in self.env._objects_truth:
            self.ax_map.plot(c, r, 'o', color='orange', markersize=8, markeredgecolor='black')

        for agent in agents:
            color_idx = (agent.id - 1) % len(self.agent_colors)
            marker_shape = 's' if agent.carrying else 'o'
            self.ax_map.plot(
                agent.pos[1], agent.pos[0],
                marker=marker_shape,
                color=self.agent_colors[color_idx],
                markersize=10, markeredgecolor='black'
            )
            self.ax_map.text(
                agent.pos[1], agent.pos[0], str(agent.id),
                color='white', ha='center', va='center',
                fontsize=8, fontweight='bold'
            )

        self.ax_map.set_title(
            f"Tick: {tick} | Oggetti: {self.env.delivered}/{NUM_OBJECTS} | "
            f"Pausa: [Spazio] | Esci: [Esc]"
        )
        self.ax_map.set_xticks(range(self.env.n))
        self.ax_map.set_yticks(range(self.env.n))
        self.ax_map.set_xticklabels([])
        self.ax_map.set_yticklabels([])
        self.ax_map.grid(color='gray', linestyle=':', linewidth=0.5)

        # === 2. BATTERIE ===
        sorted_agents = sorted(agents, key=lambda a: a.id)
        agent_ids = [str(a.id) for a in sorted_agents]
        batteries = [max(0, a.battery) for a in sorted_agents]
        bar_colors = [self.agent_colors[(a.id - 1) % len(self.agent_colors)] for a in sorted_agents]

        bars = self.ax_bat.bar(agent_ids, batteries, color=bar_colors, edgecolor='black')
        self.ax_bat.set_title("Stato Batteria\nVelocita': [↑] [↓]")
        self.ax_bat.set_xlabel("ID Agente")
        self.ax_bat.set_ylabel("Energia")
        self.ax_bat.set_ylim(0, BATTERY_INITIAL)

        for bar, battery in zip(bars, batteries):
            height = bar.get_height()
            self.ax_bat.text(
                bar.get_x() + bar.get_width() / 2., height + 5,
                f'{int(battery)}', ha='center', va='bottom', fontsize=8
            )

        # === 3. TIMING E PAUSA ===
        # FIX: try/except attorno a plt.pause per gestire la chiusura della
        # finestra con il pulsante X. Senza questo, plt.pause nel tick
        # successivo solleva TclError (o simile, backend-dipendente) causando
        # un crash non gestito che impedisce il salvataggio del log.
        try:
            plt.pause(self.pause_time)
            while self.paused:
                plt.pause(0.1)
        except Exception:
            # La finestra e' stata chiusa: segnala uscita pulita
            self.should_quit = True