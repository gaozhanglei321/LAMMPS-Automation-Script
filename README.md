# Automation Scripts for MD Simulations and QM/MM CDFT Calculations

This repository contains the Python automation scripts and input templates used for the computational workflows described in the research paper:

> **[Insert Your Paper Title Here]** > *[Optional: Authors, Journal, Year]*

The code provided here automates three key stages of the research:
1.  **Iterative MD Simulations:** Managing long-time scale LAMMPS trajectories.
2.  **Structure Processing:** Handling PDB/Mol2 file formats for system setup.
3.  **Electronic Coupling (Vab) Calculations:** Automating QM/MM CDFT workflows (e.g., State A/B optimization and coupling analysis).

---

## 📂 File Description

### 1. MD Simulation
* **`auto_run_MD.py`** The main driver script for iterative Molecular Dynamics simulations. It automates the execution of LAMMPS by updating input files step-by-step (e.g., managing `read_data` and `write_data` for 2000+ iterations).

### 2. QM/MM & CDFT Calculations
Scripts and templates for calculating reorganization energy and electron transfer rates using Constrained DFT (CDFT).

* **`auto_run_QMMM_CDFT.py`** Automates the preparation and execution of Quantum Mechanics/Molecular Mechanics (QM/MM) calculations. It handles the workflow for constrained states.
* **`template_GACA.inp`** & **`template_GACB.inp`** Input templates for the geometry optimization or single-point energy calculations of **State A** and **State B** (donor/acceptor states).
* **`template_coupling.inp`** The input template used for the final electronic coupling ($V_{ab}$) calculation based on the overlap of the diabatic states.

### 3. Data Processing
* **`pdb_mol2_process.py`** A utility script for processing molecular structure files. It handles format conversions or extracts specific coordinates from `.pdb` or `.mol2` files required for the simulation setup.

---

## 🚀 Usage

### Prerequisites
* **Python 3.x**
* **LAMMPS** (compiled with MPI support)
* **[Insert QM Software Name, e.g., CP2K / Gaussian]** for CDFT calculations.

### Running the Scripts

#### Molecular Dynamics Loop
To start the automated MD loop:
```bash
python auto_run_MD.py
