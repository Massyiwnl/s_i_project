import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from src.config import NUM_OBJECTS, BATTERY_INITIAL


# Modalita' di visualizzazione feromoni, ciclate con il tasto 'F':
#   0 = nessun feromone (default)
#   1 = pheromone_explore  (dinamico — verde, anti-loop)
#   2 = pheromone_object   (dinamico — arancione, scia oggetti)
#   3 = pheromone_home     (statico  — blu, gradiente magazzino)
#   4 = pheromone_base     (statico  — viola, gradiente base spawn)
_PHEROMONE_MODES = [
    'nessuno',
    'explore (dinamico)',
    'object (dinamico)',
    'home (statico)',
    'base (statico)',
]


class Renderer:
    def __init__(self, env):
        self.env = env
        plt.ion()

        self.fig, (self.ax_map, self.ax_bat) = plt.subplots(
            1, 2,
            figsize=(14, 8),
            gridspec_kw={'width_ratios': [3, 1]}
        )

        self.pause_time = 0.05
        self.paused = False
        self.should_quit = False

        # Indice della modalita' feromone corrente (0 = spento)
        self.pheromone_mode = 0

        # Oggetto imshow del layer feromone (creato una volta, aggiornato poi)
        self._pheromone_im = None

        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)

        # Colormap griglia (celle della mappa)
        self.cmap = mcolors.ListedColormap(
            ['white', '#404040', '#4a90d9', '#2ecc71', '#e74c3c']
        )
        self.bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
        self.norm = mcolors.BoundaryNorm(self.bounds, self.cmap.N)

        # Colormaps per i feromoni — ogni tipo ha il suo gradiente
        # I valori bassi (feromone quasi evaporato) sono trasparenti/chiari;
        # i valori alti (feromone fresco/forte) sono scuri e saturi.
        self._pheromone_cmaps = {
            1: _make_alpha_cmap('#006400', '#90ee90'),  # verde scuro → verde chiaro
            2: _make_alpha_cmap('#8b2500', '#ffd27f'),  # arancione scuro → chiaro
            3: _make_alpha_cmap('#00008b', '#add8e6'),  # blu scuro → blu chiaro
            4: _make_alpha_cmap('#4b0082', '#dda0dd'),  # viola scuro → lilla chiaro
        }

        self.agent_colors = ['#ff00ff', '#00ffff', '#0000ff', '#800080', '#8b4513']

    # ── Gestione tastiera ────────────────────────────────────────────────────

    def on_key_press(self, event):
        if event.key == ' ':
            self.paused = not self.paused
            print(f"\n*** Simulazione {'IN PAUSA' if self.paused else 'RIPRESA'} ***")

        elif event.key == 'up':
            self.pause_time = max(0.001, self.pause_time / 1.5)
            print(f"Velocita' aumentata ({self.pause_time:.3f}s/tick)")

        elif event.key == 'down':
            self.pause_time = min(2.0, self.pause_time * 1.5)
            print(f"Velocita' diminuita ({self.pause_time:.3f}s/tick)")

        elif event.key == 'f':
            # Cicla tra le modalita' feromone
            self.pheromone_mode = (self.pheromone_mode + 1) % len(_PHEROMONE_MODES)
            self._pheromone_im = None  # forza la ricreazione del layer
            print(f"Feromone visualizzato: {_PHEROMONE_MODES[self.pheromone_mode]}")

        elif event.key == 'escape':
            print("\n*** Uscita richiesta — salvataggio log in corso... ***")
            self.should_quit = True

    # ── Rendering principale ─────────────────────────────────────────────────

    def draw(self, agents, tick):
        self.ax_map.clear()
        self.ax_bat.clear()
        self._pheromone_im = None  # reset ad ogni frame (ax.clear() invalida tutto)

        # === 1. GRIGLIA BASE ===
        self.ax_map.imshow(self.env.grid, cmap=self.cmap, norm=self.norm,
                           zorder=1)

        # === 2. OVERLAY FEROMONE ===
        if self.pheromone_mode > 0:
            self._draw_pheromone_overlay()

        # === 3. OGGETTI (cerchi arancioni) ===
        for r, c in self.env._objects_truth:
            self.ax_map.plot(c, r, 'o', color='orange', markersize=8,
                             markeredgecolor='black', zorder=3)

        # === 4. AGENTI ===
        for agent in agents:
            color_idx = (agent.id - 1) % len(self.agent_colors)
            marker = 's' if agent.carrying else 'o'
            self.ax_map.plot(
                agent.pos[1], agent.pos[0],
                marker=marker,
                color=self.agent_colors[color_idx],
                markersize=10, markeredgecolor='black', zorder=4
            )
            self.ax_map.text(
                agent.pos[1], agent.pos[0], str(agent.id),
                color='white', ha='center', va='center',
                fontsize=8, fontweight='bold', zorder=5
            )

        # === 5. TITOLO E ASSI ===
        mode_label = _PHEROMONE_MODES[self.pheromone_mode]
        self.ax_map.set_title(
            f"Tick: {tick} | Oggetti: {self.env.delivered}/{NUM_OBJECTS} | "
            f"Feromone [F]: {mode_label} | Pausa: [Spazio] | Esci: [Esc]",
            fontsize=9
        )
        self.ax_map.set_xticks(range(self.env.n))
        self.ax_map.set_yticks(range(self.env.n))
        self.ax_map.set_xticklabels([])
        self.ax_map.set_yticklabels([])
        self.ax_map.grid(color='gray', linestyle=':', linewidth=0.5, zorder=0)

        # === 6. GRAFICO BATTERIE ===
        sorted_agents = sorted(agents, key=lambda a: a.id)
        agent_ids  = [str(a.id) for a in sorted_agents]
        batteries  = [max(0, a.battery) for a in sorted_agents]
        bar_colors = [self.agent_colors[(a.id - 1) % len(self.agent_colors)]
                      for a in sorted_agents]

        bars = self.ax_bat.bar(agent_ids, batteries,
                               color=bar_colors, edgecolor='black')
        self.ax_bat.set_title(
            f"Batteria\n[F] feromone | [↑↓] velocita'", fontsize=9
        )
        self.ax_bat.set_xlabel("ID Agente")
        self.ax_bat.set_ylabel("Energia")
        self.ax_bat.set_ylim(0, BATTERY_INITIAL)

        for bar, batt in zip(bars, batteries):
            self.ax_bat.text(
                bar.get_x() + bar.get_width() / 2.,
                bar.get_height() + 5,
                f'{int(batt)}',
                ha='center', va='bottom', fontsize=8
            )

        # === 7. PAUSA E TIMING ===
        try:
            plt.pause(self.pause_time)
            while self.paused:
                plt.pause(0.1)
        except Exception:
            self.should_quit = True

    # ── Layer feromone ───────────────────────────────────────────────────────

    def _draw_pheromone_overlay(self):
        """
        Sovrappone alla griglia una heatmap semitrasparente del feromone
        selezionato. I valori vengono normalizzati tra 0 e 1 rispetto al
        massimo attuale sulla mappa, quindi mappati sul gradiente colore
        del tipo selezionato.

        Verde scuro = feromone intenso (appena depositato o rinforzato).
        Verde chiaro = feromone debole (quasi evaporato o lontano dalla sorgente).
        Celle a 0 = completamente trasparenti (non disturbano la lettura della mappa).
        """
        mode = self.pheromone_mode
        grid_map = {
            1: self.env.pheromone_explore,
            2: self.env.pheromone_object,
            3: self.env.pheromone_home,
            4: self.env.pheromone_base,
        }

        raw = grid_map[mode]
        data = np.array(raw, dtype=float)

        max_val = data.max()
        if max_val < 1e-9:
            # Feromone assente su tutta la mappa: niente da disegnare
            return

        # Normalizzazione 0-1 rispetto al massimo corrente
        normalized = data / max_val

        # Maschera le celle a zero: alpha = 0 → completamente trasparente
        # Questo evita che le celle senza feromone coprano la griglia
        alpha_matrix = np.where(normalized > 0.01, normalized * 0.75, 0.0)

        cmap = self._pheromone_cmaps[mode]

        # Disegna il layer feromone sopra la griglia (zorder=2, tra griglia e agenti)
        self.ax_map.imshow(
            normalized,
            cmap=cmap,
            alpha=alpha_matrix,
            vmin=0.0,
            vmax=1.0,
            interpolation='nearest',
            zorder=2
        )


# ── Utility ──────────────────────────────────────────────────────────────────

def _make_alpha_cmap(color_high: str, color_low: str):
    """
    Costruisce una colormap lineare da color_low (valori bassi, feromone debole)
    a color_high (valori alti, feromone intenso).
    La trasparenza e' gestita separatamente tramite alpha_matrix in imshow,
    quindi qui usiamo una colormap opaca standard.
    """
    return mcolors.LinearSegmentedColormap.from_list(
        'pheromone_cmap',
        [color_low, color_high],
        N=256
    )