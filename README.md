# Decision Support System for Supplier Selection: A Comprehensive Approach

A GTMA-based (Graph Theory and Matrix Approach) Decision Support System for sustainable
supplier selection under interdependent criteria. This repository contains the full
implementation used in the accompanying paper, including data, computation, and
visualization modules.

## Paper
Shah Md Tasrifur Rahim, Shahed Mahmud —
*Decision Support System for Supplier Selection: A Comprehensive Approach*

## What this does
The system evaluates suppliers across four criteria groups (Conventional, Environmental,
Circular Economy, Resilience) using expert-assigned performance scores and interdependency
values, computes category-level GTMA indices via the Ryser permanent, and combines them into
a final Supplier Performance Index (SPI) for ranking.

## File overview
| File | Purpose |
|---|---|
| `main.py` | Entry point — run this to launch the software |
| `criteria.py` | Defines the supplier selection criteria list (Conventional, Environmental, Circular Economy, Resilience) |
| `matrix_builder.py` | Builds the SMP (category-level) and FSM (final synthesis) matrices |
| `relations.py` | Generates the interdependency relationships, including deriving lower-triangle values from upper-triangle inputs |
| `ryser.py` | Computes the matrix permanent using the Ryser algorithm |
| `supplier_manager.py` | Manages supplier data and performance scores |
| `gui.py` | User interface components |
| `dashboard.py` | Generates the visual dashboard / decision-support outputs |

## How to run
```bash
pip install -r requirements.txt
python main.py
```

## Status
Data files and full result tables (matching the tables/figures in the paper) will be added
to `data/` and `results/` folders.

## License
MIT License — see [LICENSE](LICENSE)
