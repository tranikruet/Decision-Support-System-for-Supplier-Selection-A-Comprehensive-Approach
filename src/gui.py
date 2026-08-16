import customtkinter as ctk
from tkinter import messagebox
import numpy as np

from criteria import criteria_structure
from supplier_manager import add_user, get_users, clear_users
from ryser import gray_code_permanent
from relations import RelationManager
from dashboard import Dashboard

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

criteria_vars = {}
dependencies = {}
selected_criteria = []
digraph_manager = None
relation_manager = RelationManager()  
supplier_score_entries = {}
interdependency_entries = {}

# New workflow: relations are global (upper triangle); diagonals vary per supplier
supplier_category_matrix_entries = {}  # category -> {(i,j): CTkEntry}
supplier_category_criteria_order = {}  # category -> [criterion names]
final_category_entries = {}  # (i,j) -> CTkEntry for 4x4 category matrix
final_category_order = list(criteria_structure.keys())


def _format_num(val: float) -> str:
    if abs(val - round(val)) < 1e-9:
        return str(int(round(val)))
    return f"{val:.2f}"


def _safe_set_entry(entry: ctk.CTkEntry, text: str, disabled=None) -> None:
    current_state = entry.cget("state")
    if current_state == "disabled":
        entry.configure(state="normal")
    entry.delete(0, ctk.END)
    if text != "":
        entry.insert(0, text)
    if disabled is not None:
        entry.configure(state="disabled" if disabled else "normal")
    else:
        # restore previous
        entry.configure(state=current_state)


def _selected_by_category() -> dict[str, list[str]]:
    selected = {cat: [] for cat in criteria_structure.keys()}
    for category, items in criteria_structure.items():
        for crit in items:
            if crit in criteria_vars and criteria_vars[crit].get():
                selected[category].append(crit)
    return selected


def _read_upper_value(entry: ctk.CTkEntry, *, min_val: float, max_val: float, field_label: str) -> float:
    val_str = entry.get().strip()
    if val_str == "":
        raise ValueError(f"Missing value for {field_label}")
    val = float(val_str)
    if val < min_val or val > max_val:
        raise ValueError(f"{field_label} must be between {min_val} and {max_val}. Got {val}")
    return val


def _build_matrix_from_entries(
    entries: dict[tuple[int, int], ctk.CTkEntry],
    n: int,
    *,
    diagonal_range: tuple[float, float] = (1.0, 10.0),
    upper_range: tuple[float, float] = (0.0, 10.0),
    complement_base: float = 10.0,
    label_prefix: str = "",
) -> np.ndarray:
    M = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            if i == j:
                ent = entries[(i, j)]
                M[i, j] = _read_upper_value(
                    ent,
                    min_val=diagonal_range[0],
                    max_val=diagonal_range[1],
                    field_label=f"{label_prefix}diagonal ({i+1},{j+1})",
                )
            elif i < j:
                ent = entries[(i, j)]
                val = _read_upper_value(
                    ent,
                    min_val=upper_range[0],
                    max_val=upper_range[1],
                    field_label=f"{label_prefix}upper ({i+1},{j+1})",
                )
                M[i, j] = val
                M[j, i] = complement_base - val
    return M


def _format_big(val: float) -> str:
    if abs(val) < 1e6:
        return _format_num(val)
    return f"{val:.6e}"


def _validate_min_selected(selected_by_cat: dict[str, list[str]]) -> tuple[bool, str]:
    for category in final_category_order:
        if len(selected_by_cat.get(category, [])) < 3:
            return False, f"Select at least 3 criteria in: {category}"
    return True, ""


def _build_relations_from_pairwise_entries(
    entries: dict[tuple[int, int], ctk.CTkEntry],
    n: int,
    *,
    upper_range: tuple[float, float] = (0.0, 10.0),
    complement_base: float = 10.0,
    label_prefix: str = "",
) -> np.ndarray:
    """Build symmetric off-diagonal relations from upper-triangle entries.

    Diagonal is set to 0 here (caller should fill diagonal per supplier).
    Lower triangle is auto: base - upper.
    """
    R = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            ent = entries[(i, j)]
            v = _read_upper_value(
                ent,
                min_val=upper_range[0],
                max_val=upper_range[1],
                field_label=f"{label_prefix}upper ({i+1},{j+1})",
            )
            R[i, j] = v
            R[j, i] = complement_base - v
    return R

def start_gui():
    root = ctk.CTk()
    root.title("Advanced Supplier DSS")
    root.geometry("1400x780")
    root.minsize(1200, 650)

    # Configure root grid
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # Main container with a soft light-gray background
    main_container = ctk.CTkFrame(root, fg_color="#f5f6fa", corner_radius=0)
    main_container.grid(row=0, column=0, sticky="nsew")
    main_container.grid_rowconfigure(1, weight=1)
    main_container.grid_rowconfigure(2, weight=0) # Bottom bar
    # Give more real estate to the input side to reduce scrolling
    main_container.grid_columnconfigure(0, weight=3) # Sidebar
    main_container.grid_columnconfigure(1, weight=2) # Dashboard

    # ============ TOP HEADER ============
    header = ctk.CTkFrame(main_container, fg_color="#ffffff", height=70, corner_radius=0, border_width=1, border_color="#dcdde1")
    header.grid(row=0, column=0, columnspan=2, sticky="ew")
    header.grid_propagate(False)

    title_label = ctk.CTkLabel(
        header,
        text="Advanced Supplier Decision Support System (GTMA)",
        font=("Segoe UI", 20, "bold"),
        text_color="#2f3640"
    )
    title_label.pack(pady=18, padx=20, side="left")

    # ============ LEFT SIDEBAR ============
    left_sidebar = ctk.CTkFrame(main_container, fg_color="#ffffff", width=560, corner_radius=0, border_width=1, border_color="#dcdde1")
    left_sidebar.grid(row=1, column=0, sticky="nsew", padx=(0, 0), pady=0)
    left_sidebar.grid_rowconfigure(1, weight=1)
    left_sidebar.grid_propagate(False)

    sidebar_header = ctk.CTkLabel(
        left_sidebar,
        text="⚙️  CONFIGURATION",
        font=("Segoe UI", 13, "bold"),
        text_color="#7f8c8d"
    )
    sidebar_header.pack(anchor="w", padx=20, pady=(20, 10))

    tabview = ctk.CTkTabview(left_sidebar, fg_color="#ffffff", segmented_button_selected_color="#3498db")
    tabview.pack(fill="both", expand=True, padx=10, pady=10)

    criteria_tab = tabview.add("📋 Criteria")
    supplier_tab = tabview.add("👥 Suppliers")

    # ---- Criteria Tab ----
    warning_frame = ctk.CTkFrame(criteria_tab, fg_color="#fff9e6", corner_radius=8, border_width=1, border_color="#ffeaa7")
    warning_frame.pack(fill="x", padx=10, pady=10)

    warning_label = ctk.CTkLabel(
        warning_frame,
        text="⚠️  Select at least 3 criteria from each category.",
        font=("Segoe UI", 10),
        text_color="#d6a000"
    )
    warning_label.pack(pady=8, padx=10)

    criteria_scroll = ctk.CTkScrollableFrame(criteria_tab, fg_color="transparent")
    criteria_scroll.pack(fill="both", expand=True, padx=5, pady=5)

    def toggle_entry(var):
        """On criteria toggle: refresh supplier input matrices."""
        try:
            refresh_score_inputs()
        except NameError:
            # UI may still be initializing; safe to ignore.
            return

    # Generate Criteria Rows with Standardized Padding/Alignment
    for category, items in criteria_structure.items():
        cat_label = ctk.CTkLabel(
            criteria_scroll,
            text=category.upper(),
            font=("Segoe UI", 11, "bold"),
            text_color="#3498db"
        )
        cat_label.pack(anchor="w", pady=(15, 5), padx=10)

        for crit in items:
            row_container = ctk.CTkFrame(criteria_scroll, fg_color="transparent")
            row_container.pack(fill="x", pady=4, padx=10)

            var = ctk.BooleanVar()
            checkbox = ctk.CTkCheckBox(
                row_container,
                text=crit,
                variable=var,
                font=("Segoe UI", 12),
                text_color="#2f3640",
                checkbox_width=18,
                checkbox_height=18
            )
            checkbox.pack(side="left", padx=5, pady=3)

            checkbox.configure(command=lambda v=var: toggle_entry(v))
            criteria_vars[crit] = var

    # ---- Suppliers Tab ----
    supplier_scroll = ctk.CTkScrollableFrame(supplier_tab, fg_color="transparent")
    supplier_scroll.pack(fill="both", expand=True, padx=10, pady=10)

    name_label = ctk.CTkLabel(supplier_scroll, text="📦  Supplier Name", font=("Segoe UI", 11, "bold"), text_color="#2f3640")
    name_label.pack(anchor="w", pady=(10, 5), padx=5)

    supplier_entry = ctk.CTkEntry(supplier_scroll, placeholder_text="e.g. Global Logistics Inc.", font=("Segoe UI", 12), border_color="#dcdde1")
    supplier_entry.pack(fill="x", padx=5, pady=(0, 15))

    scores_frame = ctk.CTkFrame(supplier_scroll, fg_color="transparent")
    scores_frame.pack(fill="both", expand=True, padx=5, pady=10)

    def _make_pairwise_matrix(
        parent,
        labels: list[str],
        *,
        diagonal_placeholder: str = "1-10",
        upper_placeholder: str = "0-10",
        complement_base: float = 10.0,
        title: str,
    ) -> dict[tuple[int, int], ctk.CTkEntry]:
        n = len(labels)
        entries: dict[tuple[int, int], ctk.CTkEntry] = {}

        ctk.CTkLabel(parent, text=title, font=("Segoe UI", 11, "bold"), text_color="#2f3640").pack(anchor="w", pady=(10, 8), padx=5)

        if n == 0:
            ctk.CTkLabel(parent, text="(No criteria selected in this category)", font=("Segoe UI", 10, "italic"), text_color="#95a5a6").pack(anchor="w", pady=(0, 10), padx=5)
            return entries

        # Bi-directional scroll area (horizontal + vertical)
        matrix_container = ctk.CTkFrame(parent, fg_color="transparent")
        matrix_container.pack(fill="x", expand=False, padx=5, pady=(0, 10))

        canvas = ctk.CTkCanvas(matrix_container, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        x_scroll = ctk.CTkScrollbar(matrix_container, orientation="horizontal", command=canvas.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        y_scroll = ctk.CTkScrollbar(matrix_container, orientation="vertical", command=canvas.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")

        canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        matrix_container.grid_rowconfigure(0, weight=1)
        matrix_container.grid_columnconfigure(0, weight=1)

        # Give the matrix a reasonable visible height; full content is scrollable.
        visible_rows = min(max(n, 3), 8)
        canvas.configure(height=40 + visible_rows * 30)

        matrix_scroll = ctk.CTkFrame(canvas, fg_color="transparent")
        canvas_window = canvas.create_window((0, 0), window=matrix_scroll, anchor="nw")

        def _on_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Keep the inner frame height flexible
            canvas.itemconfigure(canvas_window)

        matrix_scroll.bind("<Configure>", _on_configure)

        header_frame = ctk.CTkFrame(matrix_scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(header_frame, text="to →", font=("Segoe UI", 9, "bold"), text_color="#7f8c8d", width=70).pack(side="left", padx=2)
        for lbl in labels:
            short = (lbl[:8] + "..") if len(lbl) > 10 else lbl
            ctk.CTkLabel(header_frame, text=short, font=("Segoe UI", 8, "bold"), text_color="#3498db", width=60).pack(side="left", padx=2)

        # We create the full grid to show auto-lower values.
        for i, row_lbl in enumerate(labels):
            row_frame = ctk.CTkFrame(matrix_scroll, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            from_short = (row_lbl[:8] + "..") if len(row_lbl) > 10 else row_lbl
            ctk.CTkLabel(row_frame, text=f"↓ {from_short}", font=("Segoe UI", 8, "bold"), text_color="#e74c3c", width=70).pack(side="left", padx=2)

            for j in range(n):
                if i == j:
                    ent = ctk.CTkEntry(
                        row_frame,
                        placeholder_text=diagonal_placeholder,
                        width=60,
                        height=24,
                        font=("Segoe UI", 9),
                        border_color="#27ae60",
                        fg_color="#f9f9f9",
                    )
                    ent.pack(side="left", padx=2)
                    entries[(i, j)] = ent
                elif i < j:
                    ent = ctk.CTkEntry(
                        row_frame,
                        placeholder_text=upper_placeholder,
                        width=60,
                        height=24,
                        font=("Segoe UI", 9),
                        border_color="#3498db",
                        fg_color="#f9f9f9",
                    )
                    ent.pack(side="left", padx=2)
                    entries[(i, j)] = ent
                else:
                    ent = ctk.CTkEntry(
                        row_frame,
                        placeholder_text="auto",
                        width=60,
                        height=24,
                        font=("Segoe UI", 9),
                        border_color="#95a5a6",
                        fg_color="#ecf0f1",
                        state="disabled",
                    )
                    ent.pack(side="left", padx=2)
                    entries[(i, j)] = ent

        # Bind upper triangle entries to auto-fill lower triangle.
        def bind_pair(i: int, j: int):
            upper_ent = entries[(i, j)]
            lower_ent = entries[(j, i)]

            def on_change(_event=None):
                raw = upper_ent.get().strip()
                if raw == "":
                    _safe_set_entry(lower_ent, "", disabled=True)
                    return
                try:
                    v = float(raw)
                except ValueError:
                    _safe_set_entry(lower_ent, "", disabled=True)
                    return
                comp = complement_base - v
                _safe_set_entry(lower_ent, _format_num(comp), disabled=True)

            upper_ent.bind("<KeyRelease>", on_change)

        for i in range(n):
            for j in range(i + 1, n):
                bind_pair(i, j)

        # Mouse wheel support for vertical scroll inside the matrix
        def _on_mousewheel(event):
            # Windows wheel delta is in multiples of 120
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return entries

    def refresh_score_inputs():
        global supplier_category_matrix_entries, supplier_category_criteria_order, final_category_entries

        for widget in scores_frame.winfo_children():
            widget.destroy()

        supplier_category_matrix_entries = {}
        supplier_category_criteria_order = {}
        final_category_entries = {}

        selected_by_cat = _selected_by_category()
        total_selected = sum(len(v) for v in selected_by_cat.values())
        if total_selected == 0:
            ctk.CTkLabel(scores_frame, text="(Select criteria in 📋 Criteria tab)", font=("Segoe UI", 11, "italic"), text_color="#95a5a6").pack(pady=20)
            return

        ok, msg = _validate_min_selected(selected_by_cat)
        if not ok:
            ctk.CTkLabel(scores_frame, text=msg, font=("Segoe UI", 11, "italic"), text_color="#e67e22").pack(pady=10)
            return

        ctk.CTkLabel(
            scores_frame,
            text="Enter RELATIONS once (Upper Triangle) and SUPPLIER values (Diagonal).\n"
                 "For the next supplier: change only diagonal values.\n"
                 "Lower Triangle auto-fills: 10 - upper value",
            font=("Segoe UI", 10),
            text_color="#7f8c8d",
            justify="left",
        ).pack(anchor="w", pady=(5, 10), padx=5)

        # Category matrices
        for category in final_category_order:
            crits = selected_by_cat.get(category, [])
            supplier_category_criteria_order[category] = crits
            cat_frame = ctk.CTkFrame(scores_frame, fg_color="transparent")
            cat_frame.pack(fill="x", padx=0, pady=(5, 0))
            supplier_category_matrix_entries[category] = _make_pairwise_matrix(
                cat_frame,
                labels=crits,
                title=f"{category} Matrix",
            )

        # Final 4x4 category relations matrix (diagonal auto-filled from results at add/evaluate time)
        final_frame = ctk.CTkFrame(scores_frame, fg_color="transparent")
        final_frame.pack(fill="x", padx=0, pady=(10, 5))

        ctk.CTkLabel(final_frame, text="Final 4×4 Category Matrix (Upper Triangle Only)", font=("Segoe UI", 11, "bold"), text_color="#2f3640").pack(anchor="w", pady=(10, 8), padx=5)
        ctk.CTkLabel(
            final_frame,
            text="Diagonal is auto-filled (category results). Enter only upper triangle values (0-10).",
            font=("Segoe UI", 9),
            text_color="#7f8c8d",
        ).pack(anchor="w", pady=(0, 10), padx=5)

        # Build 4x4 grid
        matrix_scroll = ctk.CTkScrollableFrame(final_frame, fg_color="transparent", orientation="horizontal")
        matrix_scroll.pack(fill="x", expand=False, padx=5, pady=(0, 10))

        header_frame = ctk.CTkFrame(matrix_scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(header_frame, text="to →", font=("Segoe UI", 9, "bold"), text_color="#7f8c8d", width=110).pack(side="left", padx=2)
        for lbl in final_category_order:
            short = (lbl.split()[0])[:10]
            ctk.CTkLabel(header_frame, text=short, font=("Segoe UI", 8, "bold"), text_color="#3498db", width=90).pack(side="left", padx=2)

        n = len(final_category_order)
        for i, row_lbl in enumerate(final_category_order):
            row_frame = ctk.CTkFrame(matrix_scroll, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            from_short = (row_lbl.split()[0])[:10]
            ctk.CTkLabel(row_frame, text=f"↓ {from_short}", font=("Segoe UI", 8, "bold"), text_color="#e74c3c", width=110).pack(side="left", padx=2)

            for j in range(n):
                if i == j:
                    ent = ctk.CTkEntry(
                        row_frame,
                        placeholder_text="auto",
                        width=90,
                        height=24,
                        font=("Segoe UI", 9),
                        border_color="#95a5a6",
                        fg_color="#ecf0f1",
                        state="disabled",
                    )
                    ent.pack(side="left", padx=2)
                    final_category_entries[(i, j)] = ent
                elif i < j:
                    ent = ctk.CTkEntry(
                        row_frame,
                        placeholder_text="0-10",
                        width=90,
                        height=24,
                        font=("Segoe UI", 9),
                        border_color="#3498db",
                        fg_color="#f9f9f9",
                    )
                    ent.pack(side="left", padx=2)
                    final_category_entries[(i, j)] = ent
                else:
                    ent = ctk.CTkEntry(
                        row_frame,
                        placeholder_text="auto",
                        width=90,
                        height=24,
                        font=("Segoe UI", 9),
                        border_color="#95a5a6",
                        fg_color="#ecf0f1",
                        state="disabled",
                    )
                    ent.pack(side="left", padx=2)
                    final_category_entries[(i, j)] = ent

        # Bind upper triangle for final matrix
        def bind_final(i: int, j: int):
            upper_ent = final_category_entries[(i, j)]
            lower_ent = final_category_entries[(j, i)]

            def on_change(_event=None):
                raw = upper_ent.get().strip()
                if raw == "":
                    _safe_set_entry(lower_ent, "", disabled=True)
                    return
                try:
                    v = float(raw)
                except ValueError:
                    _safe_set_entry(lower_ent, "", disabled=True)
                    return
                _safe_set_entry(lower_ent, _format_num(10.0 - v), disabled=True)

            upper_ent.bind("<KeyRelease>", on_change)

        for i in range(n):
            for j in range(i + 1, n):
                bind_final(i, j)

    def add_supplier():
        name = supplier_entry.get().strip()
        if not name: 
            messagebox.showerror("Error", "Enter supplier name")
            return

        selected_by_cat = _selected_by_category()
        total_selected = sum(len(v) for v in selected_by_cat.values())
        if total_selected == 0:
            messagebox.showerror("Error", "Select criteria first (📋 Criteria tab).")
            return

        ok, msg = _validate_min_selected(selected_by_cat)
        if not ok:
            messagebox.showerror("Error", msg)
            return

        if not supplier_category_matrix_entries or not final_category_entries:
            messagebox.showerror("Error", "Click 🔄 Sync Criteria first to build the matrices.")
            return

        # Ensure matrix UI matches the current selection
        for category in final_category_order:
            if supplier_category_criteria_order.get(category, []) != selected_by_cat.get(category, []):
                messagebox.showerror("Error", "Criteria selection changed. Click 🔄 Sync Criteria again.")
                return

        category_results: dict[str, float] = {}
        diagonal_values: dict[str, dict[str, float]] = {}
        try:
            for category in final_category_order:
                crits = supplier_category_criteria_order.get(category, [])
                entries = supplier_category_matrix_entries.get(category, {})
                if len(crits) == 0:
                    category_results[category] = 0.0
                    continue

                # Off-diagonals (relations) are global and reused for all suppliers.
                # Only diagonal values are supplier-specific.
                M = _build_relations_from_pairwise_entries(
                    entries,
                    len(crits),
                    upper_range=(0.0, 10.0),
                    complement_base=10.0,
                    label_prefix=f"{category}: ",
                )
                diag_map: dict[str, float] = {}
                for i, crit in enumerate(crits):
                    diag_ent = entries[(i, i)]
                    v = _read_upper_value(diag_ent, min_val=1.0, max_val=10.0, field_label=f"{category} diagonal for '{crit}'")
                    M[i, i] = v
                    diag_map[crit] = v
                diagonal_values[category] = diag_map

                category_results[category] = float(gray_code_permanent(M))

            # Fill diagonal entries in the final 4x4 UI (shows current supplier's category results)
            for i, cat in enumerate(final_category_order):
                _safe_set_entry(final_category_entries[(i, i)], _format_big(category_results.get(cat, 0.0)), disabled=True)

            # Final 4x4: relations are global; diagonal is per-supplier (category permanents)
            final_matrix = _build_relations_from_pairwise_entries(
                final_category_entries,
                4,
                upper_range=(0.0, 10.0),
                complement_base=10.0,
                label_prefix="Final Category: ",
            )
            for i, cat in enumerate(final_category_order):
                final_matrix[i, i] = category_results.get(cat, 0.0)

            final_score = float(gray_code_permanent(final_matrix))

        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        add_user(
            name,
            weights={},
            dependencies={},
            category_matrices=None,
            final_category_relations=None,
            category_scores=category_results,
            final_score=final_score,
            diagonal_values=diagonal_values,
            criteria_by_category=selected_by_cat,
        )
        supplier_entry.delete(0, ctk.END)
        refresh_supplier_list()

        # Clear ONLY diagonal entries so relations stay the same for the next supplier
        for category in final_category_order:
            crits = supplier_category_criteria_order.get(category, [])
            entries = supplier_category_matrix_entries.get(category, {})
            for i in range(len(crits)):
                ent = entries.get((i, i))
                if ent is not None:
                    _safe_set_entry(ent, "")

        cat_lines = "\n".join(
            f"{cat}: {_format_big(category_results.get(cat, 0.0))}"
            for cat in final_category_order
        )
        messagebox.showinfo("Success", f"Added {name}\n\nCategory Results:\n{cat_lines}\n\nFinal Score: {_format_big(final_score)}")

    sync_btn = ctk.CTkButton(supplier_scroll, text="🔄 Sync Criteria", command=refresh_score_inputs, fg_color="#3498db", hover_color="#2980b9")
    sync_btn.pack(fill="x", pady=5, padx=5)

    add_btn = ctk.CTkButton(supplier_scroll, text="➕ Add Supplier", command=add_supplier, fg_color="#27ae60", hover_color="#219150")
    add_btn.pack(fill="x", pady=5, padx=5)

    list_frame = ctk.CTkFrame(supplier_scroll, fg_color="#f1f2f6", corner_radius=8)
    list_frame.pack(fill="both", expand=True, padx=5, pady=15)
    
    supplier_list = ctk.CTkTextbox(list_frame, height=150, font=("Segoe UI", 11), fg_color="transparent", text_color="#2f3640")
    supplier_list.pack(fill="both", expand=True, padx=5, pady=5)
    supplier_list.configure(state="disabled")

    def refresh_supplier_list():
        supplier_list.configure(state="normal")
        supplier_list.delete("1.0", ctk.END)
        for name, data in get_users().items():
            final_score = data.get("final_score")
            cat_scores = data.get("category_scores") or {}
            if final_score is None:
                supplier_list.insert(ctk.END, f"• {name}\n")
                continue
            cat_part = " | ".join(
                f"{cat.split()[0]}:{_format_big(cat_scores.get(cat, 0.0))}"
                for cat in final_category_order
            )
            supplier_list.insert(ctk.END, f"• {name}  (Final:{_format_big(final_score)} | {cat_part})\n")
        supplier_list.configure(state="disabled")

    # ============ RIGHT PANEL: DASHBOARD ============
    dashboard_container = ctk.CTkFrame(main_container, fg_color="transparent")
    dashboard_container.grid(row=1, column=1, sticky="nsew", padx=10, pady=20)
    
    dashboard_frame = ctk.CTkFrame(dashboard_container, fg_color="#ffffff", corner_radius=12, border_width=1, border_color="#dcdde1")
    dashboard_frame.pack(fill="both", expand=True)

    dashboard = Dashboard(dashboard_frame)
    dashboard.get_frame().pack(fill="both", expand=True, padx=10, pady=10)

    # ============ BOTTOM ACTION BAR ============
    button_bar = ctk.CTkFrame(main_container, fg_color="#ffffff", height=80, corner_radius=0, border_width=1, border_color="#dcdde1")
    button_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
    button_bar.pack_propagate(False)

    def reset_system():
        """Reset the entire system to initial state."""
        global interdependency_entries, supplier_score_entries
        
        # Clear all criteria selections
        for var in criteria_vars.values():
            var.set(False)
        
        # Clear old interdependency/score entries (legacy)
        interdependency_entries.clear()
        supplier_score_entries.clear()

        # Clear new matrix UI
        for widget in scores_frame.winfo_children():
            widget.destroy()
        supplier_category_matrix_entries.clear()
        supplier_category_criteria_order.clear()
        final_category_entries.clear()
        
        # Clear supplier name entry
        supplier_entry.delete(0, ctk.END)
        
        # Clear supplier list
        refresh_supplier_list()
        
        # Reset relation manager
        relation_manager.reset_relations()
        
        # Clear all users from supplier manager
        clear_users()
        
        # Clear dashboard
        dashboard.clear_view()
        
        # Show success message
        messagebox.showinfo("Reset Complete", "System has been reset to initial state.\nReady to start a new evaluation.")

    def evaluate():
        if not get_users():
            messagebox.showwarning("Warning", "Ensure criteria are selected and suppliers are added.")
            return

        selected_by_cat = _selected_by_category()
        ok, msg = _validate_min_selected(selected_by_cat)
        if not ok:
            messagebox.showerror("Error", msg)
            return

        if not supplier_category_matrix_entries or not final_category_entries:
            messagebox.showerror("Error", "Click 🔄 Sync Criteria first to build the matrices.")
            return

        for category in final_category_order:
            if supplier_category_criteria_order.get(category, []) != selected_by_cat.get(category, []):
                messagebox.showerror("Error", "Criteria selection changed. Click 🔄 Sync Criteria again.")
                return

        # Calculate final supplier score with global relations (upper triangle) and per-supplier diagonals.
        results = {}
        details = {}
        for name, data in get_users().items():
            diagonals = data.get("diagonal_values") or {}
            criteria_saved = data.get("criteria_by_category") or {}
            # If criteria selection changed since supplier was added, skip (needs re-add)
            if any(criteria_saved.get(cat, []) != selected_by_cat.get(cat, []) for cat in final_category_order):
                continue

            category_results = {}
            for category in final_category_order:
                crits = supplier_category_criteria_order.get(category, [])
                entries = supplier_category_matrix_entries.get(category, {})
                if len(crits) == 0:
                    category_results[category] = 0.0
                    continue

                M = _build_relations_from_pairwise_entries(entries, len(crits), label_prefix=f"{category}: ")
                diag_map = diagonals.get(category, {})
                for i, crit in enumerate(crits):
                    M[i, i] = float(diag_map.get(crit, 0.0))

                category_results[category] = float(gray_code_permanent(M))

            final_matrix = _build_relations_from_pairwise_entries(final_category_entries, 4, label_prefix="Final Category: ")
            for i, category in enumerate(final_category_order):
                final_matrix[i, i] = category_results.get(category, 0.0)
            final_score = float(gray_code_permanent(final_matrix))

            # Keep stored display values in sync with latest relations
            data["final_score"] = final_score
            data["category_scores"] = category_results

            results[name] = final_score
            details[name] = {
                'criteria': final_category_order,
                'scores': [category_results.get(c, 0.0) for c in final_category_order],
            }

        dashboard.update_results(results, details)
        refresh_supplier_list()
        messagebox.showinfo("Complete", "Evaluation analysis updated.\nGTMA Index calculated successfully.")

    def _evaluate_silent():
        """Run evaluate logic without showing the final success messagebox. Returns True on success."""
        if not get_users():
            return False

        selected_by_cat = _selected_by_category()
        ok, msg = _validate_min_selected(selected_by_cat)
        if not ok:
            return False

        if not supplier_category_matrix_entries or not final_category_entries:
            return False

        for category in final_category_order:
            if supplier_category_criteria_order.get(category, []) != selected_by_cat.get(category, []):
                return False

        try:
            results = {}
            details = {}
            for name, data in get_users().items():
                diagonals = data.get("diagonal_values") or {}
                criteria_saved = data.get("criteria_by_category") or {}
                if any(criteria_saved.get(cat, []) != selected_by_cat.get(cat, []) for cat in final_category_order):
                    continue

                category_results = {}
                for category in final_category_order:
                    crits = supplier_category_criteria_order.get(category, [])
                    entries = supplier_category_matrix_entries.get(category, {})
                    if len(crits) == 0:
                        category_results[category] = 0.0
                        continue

                    M = _build_relations_from_pairwise_entries(entries, len(crits), label_prefix=f"{category}: ")
                    diag_map = diagonals.get(category, {})
                    for i, crit in enumerate(crits):
                        M[i, i] = float(diag_map.get(crit, 0.0))

                    category_results[category] = float(gray_code_permanent(M))

                final_matrix = _build_relations_from_pairwise_entries(final_category_entries, 4, label_prefix="Final Category: ")
                for i, category in enumerate(final_category_order):
                    final_matrix[i, i] = category_results.get(category, 0.0)
                final_score = float(gray_code_permanent(final_matrix))

                data["final_score"] = final_score
                data["category_scores"] = category_results

                results[name] = final_score
                details[name] = {
                    'criteria': final_category_order,
                    'scores': [category_results.get(c, 0.0) for c in final_category_order],
                }

            dashboard.update_results(results, details)
            refresh_supplier_list()
            return True
        except Exception:
            return False

    def run_sensitivity():
        """Open a sensitivity dialog to adjust all matrix values by a percentage."""
        # Check that matrices exist
        if not supplier_category_matrix_entries and not final_category_entries:
            messagebox.showwarning("Sensitivity", "No matrices built yet.\nSync criteria and add suppliers first.")
            return

        if not get_users():
            messagebox.showwarning("Sensitivity", "No suppliers added yet.\nAdd suppliers before running sensitivity.")
            return

        dialog = ctk.CTkToplevel(root)
        dialog.title("Sensitivity Analysis")
        dialog.geometry("420x480")
        dialog.resizable(False, False)
        # Position dialog near center of root
        dialog.transient(root)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        # Header
        ctk.CTkLabel(
            dialog, text="📊 Sensitivity Analysis",
            font=("Segoe UI", 16, "bold"), text_color="#2f3640"
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            dialog,
            text="Adjust all matrix values by a percentage.\n"
                 "Positive % increases values, negative % decreases.\n"
                 "Values are clamped to valid ranges after adjustment.",
            font=("Segoe UI", 10), text_color="#7f8c8d", justify="center"
        ).pack(pady=(0, 15))

        # Diagonal % input
        diag_frame = ctk.CTkFrame(dialog, fg_color="#f0fdf4", corner_radius=8, border_width=1, border_color="#86efac")
        diag_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(
            diag_frame, text="Diagonal Values (Supplier Scores)",
            font=("Segoe UI", 11, "bold"), text_color="#166534"
        ).pack(anchor="w", padx=15, pady=(10, 2))
        ctk.CTkLabel(
            diag_frame, text="Range: 1 - 10  |  e.g. 10 means +10%, -20 means -20%",
            font=("Segoe UI", 9), text_color="#7f8c8d"
        ).pack(anchor="w", padx=15, pady=(0, 5))
        diag_entry = ctk.CTkEntry(
            diag_frame, placeholder_text="Enter % (e.g. 10 or -20)",
            width=250, font=("Segoe UI", 12), border_color="#27ae60"
        )
        diag_entry.pack(padx=15, pady=(0, 12))
        # Ensure the entry actually receives keyboard focus after the dialog fully renders
        dialog.after(100, lambda: diag_entry.focus_set())

        # Off-diagonal % input
        off_frame = ctk.CTkFrame(dialog, fg_color="#eff6ff", corner_radius=8, border_width=1, border_color="#93c5fd")
        off_frame.pack(fill="x", padx=30, pady=5)
        ctk.CTkLabel(
            off_frame, text="Off-Diagonal Values (Relations / Upper Triangle)",
            font=("Segoe UI", 11, "bold"), text_color="#1e40af"
        ).pack(anchor="w", padx=15, pady=(10, 2))
        ctk.CTkLabel(
            off_frame, text="Range: 0 - 10  |  Lower triangle auto-updates (10 - upper)",
            font=("Segoe UI", 9), text_color="#7f8c8d"
        ).pack(anchor="w", padx=15, pady=(0, 5))
        off_entry = ctk.CTkEntry(
            off_frame, placeholder_text="Enter % (e.g. 10 or -20)",
            width=250, font=("Segoe UI", 12), border_color="#3498db"
        )
        off_entry.pack(padx=15, pady=(0, 12))

        # Status label for feedback
        status_label = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 10), text_color="#e74c3c")
        status_label.pack(pady=(5, 0))

        def _apply_sensitivity():
            try:
                # Parse percentages
                diag_pct_str = diag_entry.get().strip()
                off_pct_str = off_entry.get().strip()

                diag_pct = 0.0
                off_pct = 0.0

                if diag_pct_str:
                    try:
                        diag_pct = float(diag_pct_str)
                    except ValueError:
                        status_label.configure(text=f"Invalid diagonal value: '{diag_pct_str}'", text_color="#e74c3c")
                        return
                if off_pct_str:
                    try:
                        off_pct = float(off_pct_str)
                    except ValueError:
                        status_label.configure(text=f"Invalid off-diagonal value: '{off_pct_str}'", text_color="#e74c3c")
                        return

                if diag_pct == 0.0 and off_pct == 0.0:
                    status_label.configure(text="Enter at least one non-zero percentage.", text_color="#e74c3c")
                    return

                diag_factor = 1.0 + diag_pct / 100.0
                off_factor = 1.0 + off_pct / 100.0

                changes_made = 0

                # Helper to adjust a single entry value
                def _adjust_entry(entry, factor, min_val, max_val):
                    nonlocal changes_made
                    raw = entry.get().strip()
                    if raw == "":
                        return
                    try:
                        val = float(raw)
                    except ValueError:
                        return
                    new_val = val * factor
                    # Clamp to valid range
                    if new_val < min_val:
                        new_val = min_val
                    if new_val > max_val:
                        new_val = max_val
                    _safe_set_entry(entry, _format_num(new_val))
                    changes_made += 1

                # Helper to refresh lower-triangle auto-fill for a pair
                def _refresh_lower(ents, i, j, complement_base=10.0):
                    upper_ent = ents.get((i, j))
                    lower_ent = ents.get((j, i))
                    if upper_ent is None or lower_ent is None:
                        return
                    raw = upper_ent.get().strip()
                    if raw == "":
                        _safe_set_entry(lower_ent, "", disabled=True)
                        return
                    try:
                        v = float(raw)
                    except ValueError:
                        _safe_set_entry(lower_ent, "", disabled=True)
                        return
                    _safe_set_entry(lower_ent, _format_num(complement_base - v), disabled=True)

                # 1. Adjust all sub-category matrices
                for category in final_category_order:
                    cat_entries = supplier_category_matrix_entries.get(category, {})
                    crits = supplier_category_criteria_order.get(category, [])
                    n = len(crits)
                    if n == 0:
                        continue

                    # Adjust diagonals
                    if diag_pct != 0.0:
                        for i in range(n):
                            ent = cat_entries.get((i, i))
                            if ent is not None:
                                _adjust_entry(ent, diag_factor, 1.0, 10.0)

                    # Adjust upper triangle (off-diagonals)
                    if off_pct != 0.0:
                        for i in range(n):
                            for j in range(i + 1, n):
                                ent = cat_entries.get((i, j))
                                if ent is not None:
                                    _adjust_entry(ent, off_factor, 0.0, 10.0)

                    # Refresh all lower-triangle auto-fills
                    for i in range(n):
                        for j in range(i + 1, n):
                            _refresh_lower(cat_entries, i, j)

                # 2. Adjust final 4x4 category matrix (only upper triangle - diagonal is auto)
                if final_category_entries and off_pct != 0.0:
                    n = len(final_category_order)
                    for i in range(n):
                        for j in range(i + 1, n):
                            ent = final_category_entries.get((i, j))
                            if ent is not None:
                                _adjust_entry(ent, off_factor, 0.0, 10.0)

                    # Refresh lower-triangle auto-fills
                    for i in range(n):
                        for j in range(i + 1, n):
                            _refresh_lower(final_category_entries, i, j)

                # 3. Also adjust stored diagonal values for all suppliers
                if diag_pct != 0.0:
                    for s_name, s_data in get_users().items():
                        diag_vals = s_data.get("diagonal_values") or {}
                        for cat_key, diag_map in diag_vals.items():
                            for crit_key in list(diag_map.keys()):
                                old_val = diag_map[crit_key]
                                new_val = old_val * diag_factor
                                if new_val < 1.0:
                                    new_val = 1.0
                                if new_val > 10.0:
                                    new_val = 10.0
                                diag_map[crit_key] = new_val

                # Save info for the confirmation message
                saved_changes = changes_made
                saved_diag_pct = diag_pct
                saved_off_pct = off_pct

                # Close dialog first
                dialog.destroy()

                # Schedule re-evaluation after dialog is fully gone
                def _do_evaluate_and_report():
                    success = _evaluate_silent()
                    if success:
                        messagebox.showinfo(
                            "Sensitivity Applied",
                            f"Adjusted {saved_changes} matrix entries.\n"
                            f"Diagonal: {'+' if saved_diag_pct >= 0 else ''}{saved_diag_pct}%\n"
                            f"Off-diagonal: {'+' if saved_off_pct >= 0 else ''}{saved_off_pct}%\n\n"
                            "Results have been re-evaluated and dashboard updated."
                        )
                    else:
                        messagebox.showwarning(
                            "Sensitivity",
                            f"Adjusted {saved_changes} matrix entries.\n"
                            f"But re-evaluation had issues.\n"
                            "Try clicking RANK Suppliers manually."
                        )

                root.after(200, _do_evaluate_and_report)

            except Exception as e:
                messagebox.showerror("Sensitivity Error", f"An error occurred:\n{str(e)}")

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame, text="Apply and Re-evaluate",
            command=_apply_sensitivity,
            fg_color="#27ae60", hover_color="#219150",
            font=("Segoe UI", 12, "bold"), width=200, height=40
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="Cancel",
            command=dialog.destroy,
            fg_color="#95a5a6", hover_color="#7f8c8d",
            font=("Segoe UI", 12), width=100, height=40
        ).pack(side="left", padx=8)

    btn_container = ctk.CTkFrame(button_bar, fg_color="transparent")
    btn_container.pack(expand=True)

    eval_btn = ctk.CTkButton(btn_container, text="RANK Suppliers", command=evaluate, font=("Segoe UI", 13, "bold"), fg_color="#e74c3c", width=200, height=45)
    eval_btn.pack(side="left", padx=10)

    sens_btn = ctk.CTkButton(btn_container, text="Sensitivity", command=run_sensitivity, fg_color="#3498db", width=140, height=45)
    sens_btn.pack(side="left", padx=10)

    reset_btn = ctk.CTkButton(btn_container, text="Reset", command=reset_system, fg_color="#95a5a6", width=100, height=45)
    reset_btn.pack(side="left", padx=10)

    root.mainloop()

if __name__ == "__main__":
    start_gui()
