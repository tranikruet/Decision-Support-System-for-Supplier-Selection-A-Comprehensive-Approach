import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
import numpy as np


class Dashboard:
    
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent)
        
        
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        
        self.ranking_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ranking_frame, text="Rankings")
        
        
        self.heatmap_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.heatmap_frame, text="Performance Heatmap")
        
        
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="Statistics")
        
        # Tab 4: Comparison
        self.comparison_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.comparison_frame, text="Comparison")
        
        # Tab 5: Radar Chart
        self.radar_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.radar_frame, text="Radar Chart")
        
        self.results = {}
        self.supplier_details = {}
    
    def update_results(self, results, supplier_details=None):
        self.results = results
        self.supplier_details = supplier_details or {}
        self._draw_all_charts()
    
    def _draw_all_charts(self):
        self._draw_ranking_chart()
        self._draw_heatmap()
        self._draw_statistics()
        self._draw_comparison()
        self._draw_radar_chart()
    
    def _draw_ranking_chart(self):
        for widget in self.ranking_frame.winfo_children():
            widget.destroy()
        
        if not self.results:
            tk.Label(self.ranking_frame, text="No results to display").pack(pady=20)
            return
        
        
        sorted_results = sorted(self.results.items(), key=lambda x: x[1], reverse=True)
        names = [r[0] for r in sorted_results]
        scores = [r[1] for r in sorted_results]
        
        
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)

        def _fmt_score(x: float) -> str:
            return f"{x:.2e}" if abs(x) >= 1e6 else f"{x:.2f}"
        
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(names)))
        bars = ax.barh(names, scores, color=colors)
        
        ax.set_xlabel("GTMA Final Score", fontsize=11, fontweight="bold")
        ax.set_title("Supplier Ranking", fontsize=12, fontweight="bold")
        ax.invert_yaxis()

        # Large scores: show axis in scientific notation
        try:
            ax.ticklabel_format(axis='x', style='sci', scilimits=(0, 0))
        except Exception:
            pass
        
        
        for i, (bar, score) in enumerate(zip(bars, scores)):
            ax.text(score, bar.get_y() + bar.get_height()/2, 
                   f" {_fmt_score(score)}", va="center", fontweight="bold")
        
        fig.tight_layout()
        
        
        canvas = FigureCanvasTkAgg(fig, master=self.ranking_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def _draw_heatmap(self):
        
        
        for widget in self.heatmap_frame.winfo_children():
            widget.destroy()
        
        if not self.supplier_details or not self.results:
            tk.Label(self.heatmap_frame, text="No detailed data to display").pack(pady=20)
            return
        
        
        sorted_suppliers = sorted(self.results.items(), key=lambda x: x[1], reverse=True)
        supplier_names = [s[0] for s in sorted_suppliers]
        
        
        # Use a stable criteria order so labels match score columns
        criteria_order = None
        for supplier_name in supplier_names:
            details = self.supplier_details.get(supplier_name) or {}
            crits = details.get('criteria') or []
            if crits:
                criteria_order = list(crits)
                break

        if not criteria_order:
            tk.Label(self.heatmap_frame, text="No scoring data available").pack(pady=20)
            return

        data_matrix = []
        
        for supplier_name in supplier_names:
            if supplier_name in self.supplier_details:
                details = self.supplier_details[supplier_name]
                criteria = details.get('criteria', [])
                scores = details.get('scores', [])

                row_map = dict(zip(criteria, scores))
                data_matrix.append([row_map.get(c, 0.0) for c in criteria_order])
        
        if not data_matrix:
            tk.Label(self.heatmap_frame, text="No scoring data available").pack(pady=20)
            return
        
        # Normalize per-column (per category) so all categories are visible
        data_arr = np.array(data_matrix, dtype=float)
        col_max = np.max(data_arr, axis=0)
        col_max[col_max == 0] = 1.0  # avoid division by zero
        normalized = data_arr / col_max
        
        fig = Figure(figsize=(12, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        im = ax.imshow(normalized, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)

        # Annotate cells with original values
        for i in range(len(supplier_names)):
            for j in range(len(criteria_order)):
                val = data_arr[i, j]
                txt = f"{val:.2e}" if abs(val) >= 1e6 else f"{val:.2f}"
                text_color = "white" if normalized[i, j] > 0.6 else "black"
                ax.text(j, i, txt, ha="center", va="center", fontsize=7, color=text_color)

        ax.set_xticks(range(len(criteria_order)))
        ax.set_xticklabels([c[:15] + "..." if len(c) > 15 else c for c in criteria_order],
                   rotation=45, ha="right", fontsize=9)
        ax.set_yticks(range(len(supplier_names)))
        ax.set_yticklabels(supplier_names)
        
        ax.set_title("Supplier Performance Heatmap (Normalized per Category)", fontsize=12, fontweight="bold")
        
        
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Relative Score (within category)", fontsize=10)
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.heatmap_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def _draw_statistics(self):

        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        if not self.results:
            tk.Label(self.stats_frame, text="No results to display").pack(pady=20)
            return
        
        scores = list(self.results.values())
        
        
        def _fmt_stat(x: float) -> str:
            return f"{x:.6e}" if abs(x) >= 1e6 else f"{x:.4f}"

        stats = {
            "Total Suppliers": len(scores),
            "Highest Score": _fmt_stat(max(scores)),
            "Lowest Score": _fmt_stat(min(scores)),
            "Average Score": _fmt_stat(float(np.mean(scores))),
            "Std Deviation": _fmt_stat(float(np.std(scores))),
            "Score Range": _fmt_stat(max(scores) - min(scores)),
        }
        
        
        stats_frame = tk.Frame(self.stats_frame)
        stats_frame.pack(pady=20, padx=20)
        
        tk.Label(stats_frame, text="EVALUATION STATISTICS", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        for key, value in stats.items():
            row_frame = tk.Frame(stats_frame)
            row_frame.pack(fill="x", pady=5)
            
            tk.Label(row_frame, text=f"{key}:", font=("Arial", 10), width=20, 
                    justify="left").pack(side="left")
            tk.Label(row_frame, text=str(value), font=("Arial", 10, "bold"), 
                    fg="darkblue").pack(side="left")
        
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        ax.hist(scores, bins=min(10, len(scores)), color="skyblue", edgecolor="black", alpha=0.7)
        ax.set_xlabel("GTMA Final Score", fontsize=10)
        ax.set_ylabel("Frequency", fontsize=10)
        ax.set_title("Score Distribution", fontsize=11, fontweight="bold")
        ax.axvline(np.mean(scores), color="red", linestyle="--", linewidth=2, label="Mean")
        ax.legend()

        try:
            ax.ticklabel_format(axis='x', style='sci', scilimits=(0, 0))
        except Exception:
            pass
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.stats_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)
    
    def _draw_comparison(self):
        
        for widget in self.comparison_frame.winfo_children():
            widget.destroy()
        
        if not self.supplier_details or not self.results:
            tk.Label(self.comparison_frame, text="No data for comparison").pack(pady=20)
            return
        
        
        sorted_suppliers = sorted(self.results.items(), key=lambda x: x[1], reverse=True)[:3]
        
        comparison_data = {}
        criteria_order = None
        
        for supplier_name, _ in sorted_suppliers:
            if supplier_name in self.supplier_details:
                details = self.supplier_details[supplier_name]
                criteria = details.get('criteria', [])
                scores = details.get('scores', [])
                
                comparison_data[supplier_name] = dict(zip(criteria, scores))
                if criteria and criteria_order is None:
                    criteria_order = list(criteria)
        
        if not comparison_data:
            tk.Label(self.comparison_frame, text="Insufficient data for comparison").pack(pady=20)
            return
        
        if not criteria_order:
            tk.Label(self.comparison_frame, text="Insufficient data for comparison").pack(pady=20)
            return

        criteria_list = criteria_order[:8]
        
        # Normalize per-category: find the max score across all suppliers for each category
        cat_max = {}
        for c in criteria_list:
            max_val = max(abs(comparison_data[s].get(c, 0)) for s in comparison_data)
            cat_max[c] = max_val if max_val > 0 else 1.0
        
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        x = np.arange(len(criteria_list))
        width = 0.25
        
        colors_list = ["#ff7f0e", "#2ca02c", "#d62728"]
        
        for idx, (supplier_name, _) in enumerate(sorted_suppliers):
            if supplier_name in comparison_data:
                raw_scores = [comparison_data[supplier_name].get(c, 0) for c in criteria_list]
                norm_scores = [s / cat_max[c] * 10 for s, c in zip(raw_scores, criteria_list)]
                bars = ax.bar(x + idx * width, norm_scores, width, label=supplier_name, 
                      color=colors_list[idx % len(colors_list)], alpha=0.8)
                # Annotate with original values
                for bar, raw in zip(bars, raw_scores):
                    txt = f"{raw:.1e}" if abs(raw) >= 1e6 else f"{raw:.1f}"
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                           txt, ha="center", va="bottom", fontsize=6, rotation=90)
        
        ax.set_xlabel("Category", fontsize=10, fontweight="bold")
        ax.set_ylabel("Normalized Score (0-10)", fontsize=10, fontweight="bold")
        ax.set_title("Top Suppliers Comparison (Normalized per Category)", fontsize=12, fontweight="bold")
        ax.set_xticks(x + width)
        ax.set_xticklabels([c[:12] + "..." if len(c) > 12 else c for c in criteria_list], 
                           rotation=45, ha="right", fontsize=9)
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(0, 12)  # Leave room for annotations
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.comparison_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def _draw_radar_chart(self):
        
        for widget in self.radar_frame.winfo_children():
            widget.destroy()
        
        if not self.supplier_details or not self.results:
            tk.Label(self.radar_frame, text="No data for radar chart").pack(pady=20)
            return
        
        # Show top 3 suppliers on the radar chart
        sorted_suppliers = sorted(self.results.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Gather criteria from the first valid supplier
        criteria = None
        for supplier_name, _ in sorted_suppliers:
            if supplier_name in self.supplier_details:
                details = self.supplier_details[supplier_name]
                crits = details.get('criteria', [])
                if crits:
                    criteria = list(crits)
                    break
        
        if not criteria:
            tk.Label(self.radar_frame, text="No criteria scores available").pack(pady=20)
            return
        
        # Normalize per-category across all suppliers so each axis is 0-10
        all_scores = {}  # supplier -> [scores]
        for supplier_name, _ in sorted_suppliers:
            if supplier_name in self.supplier_details:
                details = self.supplier_details[supplier_name]
                s_criteria = details.get('criteria', [])
                s_scores = details.get('scores', [])
                score_map = dict(zip(s_criteria, s_scores))
                all_scores[supplier_name] = [score_map.get(c, 0.0) for c in criteria]
        
        if not all_scores:
            tk.Label(self.radar_frame, text="Insufficient data for radar chart").pack(pady=20)
            return
        
        # Per-category max for normalization
        num_criteria = len(criteria)
        cat_max = []
        for j in range(num_criteria):
            mx = max(abs(all_scores[s][j]) for s in all_scores)
            cat_max.append(mx if mx > 0 else 1.0)
        
        fig = Figure(figsize=(8, 8), dpi=100)
        ax = fig.add_subplot(111, projection='polar')
        
        angles = np.linspace(0, 2 * np.pi, num_criteria, endpoint=False).tolist()
        angles_plot = angles + angles[:1]
        
        colors = ['#e74c3c', '#2ca02c', '#3498db']
        
        for idx, (supplier_name, _) in enumerate(sorted_suppliers):
            if supplier_name not in all_scores:
                continue
            raw = all_scores[supplier_name]
            normalized = [raw[j] / cat_max[j] * 10 for j in range(num_criteria)]
            normalized_plot = normalized + normalized[:1]
            
            color = colors[idx % len(colors)]
            ax.plot(angles_plot, normalized_plot, 'o-', linewidth=2, color=color, label=supplier_name)
            ax.fill(angles_plot, normalized_plot, alpha=0.1, color=color)
        
        ax.set_xticks(angles)
        ax.set_xticklabels([c[:15] + "..." if len(c) > 15 else c for c in criteria], fontsize=9)
        ax.set_ylim(0, 10)
        ax.set_ylabel("Relative Score (0-10)", fontsize=9)
        ax.set_title("Radar Chart: Top Suppliers\n(Normalized Category Profile)", 
                    fontsize=11, fontweight="bold", pad=20)
        ax.grid(True)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.radar_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def clear_view(self):
        
        self.results = {}
        self.supplier_details = {}
        
        # Clear all tabs
        for frame in [self.ranking_frame, self.heatmap_frame, self.stats_frame, self.comparison_frame, self.radar_frame]:
            for widget in frame.winfo_children():
                widget.destroy()
    
    def get_frame(self):
        
        return self.frame
