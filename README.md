# Automation Scripts for MD Simulations and Electronic Coupling Calculations

This repository contains the automation scripts and input templates used in the research paper: **"[Insert Your Paper Title Here]"**. 

The code provided here automates two key stages of the computational workflow:
1.  **Iterative MD Simulations:** Automating LAMMPS runs to generate trajectories.
2.  **Electronic Coupling Calculations:** Automating the preparation and execution of input files (e.g., for CP2K/Gaussian) to calculate electronic coupling elements ($V_{ab}$) for electron transfer rates.

## 📂 Repository Structure

### 1. MD Simulation (`/01_MD_Simulation`)
Automates iterative Molecular Dynamics simulations using LAMMPS.

* `auto_run_md.py`: The main Python driver script. It iteratively updates input files, runs simulations, and manages data inheritance between steps.
* `gaff_loop_25.in`: The base LAMMPS input template containing placeholders (e.g., `read_data`, `write_data`) that are dynamically populated by the script.

### 2. Electronic Coupling (`/02_Electronic_Coupling`)
Automates the calculation of electronic coupling values for charge transfer analysis (e.g., based on Marcus Theory).

* `auto_run_coupling.py`: Script to batch-process configurations and generate specific input files from templates.
* `template_GACA.inp` & `template_GACB.inp`: Input templates corresponding to the isolated states/fragments (State A and State B).
* `template_coupling.inp`: Input template for the final coupling calculation step.

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.x**
* **LAMMPS** (compiled with MPI support) for MD simulations.
* **[Insert QM Software Name, e.g., CP2K / Gaussian]** for electronic coupling calculations.
