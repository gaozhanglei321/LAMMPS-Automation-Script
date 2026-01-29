import sys
import re

# =================================================================
# --- User Configuration ---
# =================================================================
INPUT_PDB_FILE = '25_test2025.pdb'
OUTPUT_PDB_FILE = '25_test2025_processed.pdb'
MOL2_TEMPLATE = 'center1.mol2'

# Auto-detect is enabled by default.
# If detection fails, it will fall back to these manual values (optional).
MANUAL_NUM_OLIGOMERS = 64
MANUAL_NUM_IONS = 48
MANUAL_NUM_WATERS = 1624


# =================================================================

def load_atom_names_from_mol2(mol2_file):
    """
    Extract atom names and element types from mol2 file.
    Corrected parsing logic for GAFF atom types (e.g., cc, ss, h4).
    """
    atom_info = []
    reading_atoms = False
    try:
        with open(mol2_file, 'r') as f:
            for line in f:
                if line.startswith("@<TRIPOS>ATOM"):
                    reading_atoms = True
                    continue
                if line.startswith("@<TRIPOS>BOND"):
                    break

                if reading_atoms:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        name = parts[1]
                        atom_type = parts[5].lower()

                        # --- Improved logic for converting GAFF types to element symbols ---
                        if atom_type.startswith('cl'):
                            element_guess = 'Cl'
                        elif atom_type.startswith('br'):
                            element_guess = 'Br'
                        elif atom_type.startswith('na'):
                            element_guess = 'Na'
                        elif atom_type.startswith('mg'):
                            element_guess = 'Mg'
                        elif atom_type.startswith('fe'):
                            element_guess = 'Fe'
                        else:
                            element_guess = atom_type[0].upper()

                        atom_info.append((name, element_guess))
    except FileNotFoundError:
        print(f"[ERROR] Template file '{mol2_file}' not found!")
        sys.exit(1)
    return atom_info


def get_pdb_element(line):
    """
    Extract element from PDB line.
    """
    # 1. Try reading Element column (76-78)
    if len(line) >= 78:
        elem = line[76:78].strip()
        if elem: return elem.capitalize()

    # 2. Fallback to extracting from atom name (12-16)
    name = line[12:16].strip()
    elem = re.sub(r'[^A-Za-z]', '', name)
    if elem.upper().startswith('CL'): return 'Cl'
    if elem.upper().startswith('BR'): return 'Br'
    if elem.startswith('H'): return 'H'

    return elem.capitalize()


def auto_detect_counts(atom_lines, atoms_per_olig):
    """
    Automatically detect the number of Oligomers, Ions, and Waters based on patterns.
    Integrated from user's original script logic.
    """
    print("--- Starting Auto-Detection ---")

    ION_NAMES = {"CL-", "CL", "NA", "NA+", "K", "K+", "MG", "MG2+"}
    WATER_RES_NAMES = {"WAT", "HOH", "SOL", "TIP3", "TP3"}
    WATER_ATOM_NAMES = {"O", "OW", "OH2"}
    atoms_per_wat = 3  # Standard TIP3P

    if len(atom_lines) < atoms_per_olig:
        print(f"Error: Total atoms ({len(atom_lines)}) < one oligomer ({atoms_per_olig}).")
        return 0, 0, 0

    # 1. Scan Oligomers
    # Pattern: The atom names of the first oligomer
    pattern_names = [line[12:16].strip() for line in atom_lines[:atoms_per_olig]]

    current_index = 0
    num_olig = 0
    while current_index + atoms_per_olig <= len(atom_lines):
        matches = True
        for j in range(atoms_per_olig):
            line = atom_lines[current_index + j]
            name = line[12:16].strip()
            if name != pattern_names[j]:
                matches = False
                break

        if matches:
            num_olig += 1
            current_index += atoms_per_olig
        else:
            break

    print(f"  Detected Oligomers: {num_olig}")

    # 2. Scan Ions
    num_ion = 0
    ion_scan_index = current_index

    while ion_scan_index < len(atom_lines):
        line = atom_lines[ion_scan_index]
        res_name = line[17:20].strip().upper()
        atom_name = line[12:16].strip().upper()

        is_ion = (res_name in ION_NAMES or atom_name in ION_NAMES)
        is_water = (res_name in WATER_RES_NAMES) or (atom_name in WATER_ATOM_NAMES)

        if is_ion:
            num_ion += 1
            ion_scan_index += 1
        elif is_water:
            break  # Hit water, stop ion scan
        else:
            # Hit something else (unknown), stop
            break

    print(f"  Detected Ions:      {num_ion}")

    # 3. Scan Waters
    water_start_index = ion_scan_index
    num_wat = 0
    k = water_start_index
    water_pattern = ["O", "H", "H"]  # Element based pattern

    while k + atoms_per_wat <= len(atom_lines):
        matches = True
        for j in range(atoms_per_wat):
            line = atom_lines[k + j]
            elem = get_pdb_element(line)  # Use robust helper
            # Simple check: O, H, H
            target = water_pattern[j]
            # Fuzzy match for H
            if target == "H" and elem == "H":
                pass
            elif target == "O" and elem == "O":
                pass
            else:
                matches = False
                break

        if matches:
            num_wat += 1
            k += atoms_per_wat
        else:
            break

    print(f"  Detected Waters:    {num_wat}")
    print("-------------------------------")

    return num_olig, num_ion, num_wat


def process_pdb(input_pdb, output_pdb, mol2_template):
    print(f"Processing '{input_pdb}' using template '{mol2_template}'...")

    # 1. Load Template Info
    oligomer_info = load_atom_names_from_mol2(mol2_template)
    atoms_per_oligomer = len(oligomer_info)
    print(f"Template loaded: {atoms_per_oligomer} atoms per oligomer.")

    # 2. Read All Lines
    try:
        with open(input_pdb, 'r') as f:
            all_lines = f.readlines()
    except FileNotFoundError:
        print(f"[ERROR] Input file '{input_pdb}' not found.")
        sys.exit(1)

    # Separate Header and Atom lines
    header_lines = []
    atom_lines = []
    for line in all_lines:
        if line.startswith(("ATOM", "HETATM")):
            atom_lines.append(line)
        elif line.startswith(("CRYST1", "REMARK", "COMPND", "HEADER", "TITLE", "AUTHOR")):
            header_lines.append(line)

    # 3. Auto-Detect Counts
    num_oligomers, num_ions, num_waters = auto_detect_counts(atom_lines, atoms_per_oligomer)

    if num_oligomers == 0 and num_ions == 0 and num_waters == 0:
        print("[WARNING] Auto-detection failed or found nothing. Falling back to manual config.")
        num_oligomers = MANUAL_NUM_OLIGOMERS
        num_ions = MANUAL_NUM_IONS
        num_waters = MANUAL_NUM_WATERS

    # 4. Prepare for Processing
    # File handle for extracting the first molecule template
    extract_filename = "extracted_oligomer.pdb"
    f_extract = open(extract_filename, 'w')
    extracting = True
    print(f"Preparing to extract the first oligomer to '{extract_filename}'...")

    ion_resname = "Cl-"
    ion_atomname = "Cl-"
    water_resname = "WAT"
    water_atom_names = ["O", "H1", "H2"]
    water_elements = ["O", "H", "H"]

    # 5. Main Processing Loop (Writing)
    with open(output_pdb, 'w') as fout:
        # Write Headers
        for h in header_lines: fout.write(h)

        atom_counter = 0
        residue_counter = 0

        current_mol_type = "oligomer"
        mol_idx = 0
        atom_in_mol_idx = 0

        current_residue_lines = []

        # Iterate through ATOM lines only
        for line_num, line in enumerate(atom_lines, 1):

            # --- Stop if we have processed all detected molecules ---
            if current_mol_type == "done":
                break

            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
            except ValueError:
                print(f"[ERROR] Invalid coordinates at atom line {line_num}.")
                sys.exit(1)

            pdb_element = get_pdb_element(line)

            # --- Logic ---
            if current_mol_type == "oligomer":
                res_name = "MOL"
                target_name, target_element = oligomer_info[atom_in_mol_idx]

                # Check Mismatch
                if pdb_element != target_element:
                    if not (pdb_element == target_element):  # Strict check
                        print(f"\n[CRITICAL ERROR] Atom Mismatch (Oligomer) at line {line_num}!")
                        print(f"  Expected: {target_name} ({target_element})")
                        print(f"  Found: {pdb_element}")
                        sys.exit(1)

                # Extraction Logic
                if extracting:
                    f_extract.write(
                        f"ATOM  {atom_in_mol_idx + 1:5d} {pdb_element:^4s} MOL     1    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00\n")

                atom_name = target_name
                atom_in_mol_idx += 1

                atom_counter += 1
                # Buffer write
                if atom_in_mol_idx == atoms_per_oligomer:
                    residue_counter += 1
                    current_residue_lines.append(
                        f"ATOM  {atom_counter:5d} {atom_name:^4s} {res_name:3s} {residue_counter:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00\n")
                    current_residue_lines.append("TER\n")

                    for l in current_residue_lines: fout.write(l)
                    current_residue_lines = []

                    if extracting:
                        f_extract.close()
                        extracting = False
                        print(f"-> Successfully extracted '{extract_filename}'. Use this for Antechamber!")

                    mol_idx += 1
                    atom_in_mol_idx = 0
                    if mol_idx == num_oligomers:
                        current_mol_type = "ion" if num_ions > 0 else "water" if num_waters > 0 else "done"
                        mol_idx = 0
                else:
                    current_residue_lines.append(
                        f"ATOM  {atom_counter:5d} {atom_name:^4s} {res_name:3s} {residue_counter + 1:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00\n")

            elif current_mol_type == "ion":
                res_name = ion_resname
                atom_name = ion_atomname

                if pdb_element != "Cl":
                    print(f"\n[CRITICAL ERROR] Ion Mismatch at line {line_num}. Expected Cl, found {pdb_element}.")
                    sys.exit(1)

                atom_counter += 1
                residue_counter += 1
                fout.write(
                    f"ATOM  {atom_counter:5d} {atom_name:^4s} {res_name:3s} {residue_counter:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00\n")
                fout.write("TER\n")

                mol_idx += 1
                if mol_idx == num_ions:
                    current_mol_type = "water" if num_waters > 0 else "done"
                    mol_idx = 0
                    atom_in_mol_idx = 0

            elif current_mol_type == "water":
                res_name = water_resname
                atom_name = water_atom_names[atom_in_mol_idx]
                target_element = water_elements[atom_in_mol_idx]

                if pdb_element != target_element:
                    print(
                        f"\n[CRITICAL ERROR] Water Mismatch at line {line_num}. Expected {target_element}, found {pdb_element}.")
                    print("Possible missing atom in previous water molecule.")
                    sys.exit(1)

                atom_in_mol_idx += 1
                atom_counter += 1

                if atom_in_mol_idx == 3:
                    residue_counter += 1
                    current_residue_lines.append(
                        f"ATOM  {atom_counter:5d} {atom_name:^4s} {res_name:3s} {residue_counter:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00\n")
                    current_residue_lines.append("TER\n")

                    for l in current_residue_lines: fout.write(l)
                    current_residue_lines = []

                    mol_idx += 1
                    atom_in_mol_idx = 0
                    if mol_idx == num_waters:
                        current_mol_type = "done"
                else:
                    current_residue_lines.append(
                        f"ATOM  {atom_counter:5d} {atom_name:^4s} {res_name:3s} {residue_counter + 1:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00\n")

        # End of loop
        if current_residue_lines:
            print(f"[WARNING] Unwritten incomplete residue lines found at end of file. Discarding.")

        fout.write("END\n")
        print(f"Processing complete. Generated file: {output_pdb}")
        print(f"Total residues: {residue_counter}")


if __name__ == "__main__":
    process_pdb(INPUT_PDB_FILE, OUTPUT_PDB_FILE, MOL2_TEMPLATE)