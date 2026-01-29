# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import glob
import re
import sys
import codecs

# ==================== User Configuration ====================

# 1. Calculation Range
# Now you can freely include 49, e.g., from 45 to 55
START_MOL = 49
END_MOL   = 64

# 2. Base Molecule Index (Mathematical Base Index for atom offset calculation)
# Keep 49 unchanged, as your atom increment logic is based on this position
BASE_MOL_IDX = 49

# 3. Atom Increment (Mol 50 = Mol 49 + 173)
ATOMS_PER_MOL = 173

# 4. Template Filenames (New Configuration)
# Please rename your template files to the following names before running, or modify here to match your filenames
# This prevents conflict with actual calculation filenames like mol49_GACA.inp
TEMPLATE_GACA_NAME = "template_GACA.inp"  # Previously mol49_GACA.inp
TEMPLATE_GACB_NAME = "template_GACB.inp"  # Previously mol49_GACB.inp
TEMPLATE_HAB_NAME  = "template_coupling.inp" # Previously A_B_coupling.inp

# 5. CP2K Run Command & Resources
# Set number of threads (cores) per CP2K instance.
# Use 16 if you want to run 2 instances on a 32-core machine.
OMP_NUM_THREADS = 32

# The command now exports the thread limit before running
CP2K_CMD_TEMPLATE = "export OMP_NUM_THREADS={threads} && cp2k.ssmp -i {inp} | tee {out}"

# ==================== Core Logic ====================

def get_file_pattern(pattern):
    """Find a file matching the pattern in current directory."""
    files = glob.glob(pattern)
    return files[0] if files else None

def read_file_safe(filepath):
    """
    Robust file reading function.
    Tries multiple encodings to handle files with Chinese characters (GBK/UTF-8).
    """
    if not os.path.exists(filepath):
        print(f"    [Error] File not found: {filepath}")
        return None

    # List of encodings to try. 
    encodings_to_try = ['utf-8', 'gb18030', 'latin-1']

    for enc in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    # If all fail, read with ignore errors
    print(f"    [Warning] Could not decode {filepath} with standard encodings. Ignoring errors.")
    with open(filepath, 'r', errors='ignore') as f:
        return f.read()

def extract_strength(output_file):
    """Extract the last 'Strength of constraint' from output file."""
    content = read_file_safe(output_file)
    if content is None:
        return None

    last_strength = None
    # Regex to match: Strength of constraint : -0.08735...
    regex = re.compile(r"Strength of constraint\s*:\s*([-+]?\d*\.\d+)")

    for line in content.splitlines():
        match = regex.search(line)
        if match:
            last_strength = match.group(1)
    
    if last_strength:
        print(f"    [Success] Found Strength: {last_strength}")
        return last_strength
    else:
        print(f"    [Warning] Strength not found in {output_file}")
        return None

def is_calc_finished(filepath):
    """
    Check if the calculation finished successfully by looking for CP2K's footer.
    """
    if not os.path.exists(filepath):
        return False
    
    content = read_file_safe(filepath)
    if content and "PROGRAM ENDED AT" in content:
        return True
    return False

def update_mm_index(content, atom_offset):
    """Recursively increase MM_INDEX atom numbers."""
    if atom_offset == 0:
        return content

    def replace_func(match):
        return str(int(match.group(0)) + atom_offset)

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if "MM_INDEX" in line:
            # Regex \b\d+\b matches whole numbers only
            line = re.sub(r'\b\d+\b', replace_func, line)
        new_lines.append(line)
    return '\n'.join(new_lines)

def generate_input(template_file, new_file, proj_name, xyz_file, atom_offset, 
                   wfn_replace_map=None, strength_map=None):
    """
    Generate new input file from template.
    Handles PROJECT, XYZ, MM_INDEX, WFN paths, and Strength injection.
    """
    content = read_file_safe(template_file)
    if content is None:
        return False

    # 1. Modify PROJECT
    content = re.sub(r"PROJECT\s+.*", f"PROJECT {proj_name}", content)

    # 2. Modify XYZ filename (if COORD_FILE_NAME exists)
    if xyz_file:
        content = re.sub(r"COORD_FILE_NAME\s+.*", f"COORD_FILE_NAME {xyz_file}", content)

    # 3. Update MM_INDEX
    content = update_mm_index(content, atom_offset)

    # 4. (For Coupling) Force replace WFN paths
    if wfn_replace_map:
        # Try replacing GACA WFN path
        if 'GACA' in wfn_replace_map:
            content = re.sub(r"WFN_RESTART_FILE_NAME\s+.*GACA.*", 
                             f"WFN_RESTART_FILE_NAME {wfn_replace_map['GACA']}", content, flags=re.IGNORECASE)
        
        # Try replacing GACB WFN path
        if 'GACB' in wfn_replace_map:
            content = re.sub(r"WFN_RESTART_FILE_NAME\s+.*GACB.*", 
                             f"WFN_RESTART_FILE_NAME {wfn_replace_map['GACB']}", content, flags=re.IGNORECASE)

    # 5. (For Coupling) Inject Strength
    if strength_map:
        parts = content.split("&FORCE_EVAL")
        # Structure assumption: [0]Header -> [1]Mixed -> [2]GACA -> [3]GACB
        if len(parts) >= 4:
            # Inject GACA Strength
            if 'GACA' in strength_map and strength_map['GACA']:
                parts[2] = re.sub(r"STRENGTH\s+[\-\d\.]+", f"STRENGTH {strength_map['GACA']}", parts[2])
            
            # Inject GACB Strength
            if 'GACB' in strength_map and strength_map['GACB']:
                parts[3] = re.sub(r"STRENGTH\s+[\-\d\.]+", f"STRENGTH {strength_map['GACB']}", parts[3])
            
            content = "&FORCE_EVAL".join(parts)
        else:
            print("[Warning] FORCE_EVAL structure mismatch, Strength injection might fail.")

    # Save with UTF-8 encoding to prevent future issues
    with open(new_file, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def run_cp2k(inp_file, out_file):
    """Run CP2K command."""
    # Pass the thread count to the command template
    cmd = CP2K_CMD_TEMPLATE.format(inp=inp_file, out=out_file, threads=OMP_NUM_THREADS)
    print(f"    [Running] {cmd}")
    try:
        # shell=True allows pipe usage and executing the export command
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        print(f"    [Error] Calculation failed for {inp_file}")

def main():
    work_dir = os.getcwd()
    print(f"[Init] Working Directory: {work_dir}")

    # Use the User Configured template names
    # Priority: Explicit configuration -> Fallback check
    tpl_gaca = get_file_pattern(TEMPLATE_GACA_NAME)
    tpl_gacb = get_file_pattern(TEMPLATE_GACB_NAME)
    tpl_hab  = get_file_pattern(TEMPLATE_HAB_NAME)
    
    current_xyz = get_file_pattern("*.xyz")

    # Validate templates exist
    if not tpl_gaca or not os.path.exists(tpl_gaca):
        print(f"[Error] Template GACA not found: '{TEMPLATE_GACA_NAME}'")
        print(f"Please rename your old 'mol49_GACA.inp' to '{TEMPLATE_GACA_NAME}'")
        return
        
    if not tpl_hab or not os.path.exists(tpl_hab):
        print(f"[Error] Template Coupling not found: '{TEMPLATE_HAB_NAME}'")
        return
    
    # If GACB template is missing, assume it might be the same as GACA or warn
    if not tpl_gacb:
        print(f"[Warning] Template GACB '{TEMPLATE_GACB_NAME}' not found. Using GACA template.")
        tpl_gacb = tpl_gaca

    print(f"[Init] Using Templates:\n  - GACA: {tpl_gaca}\n  - GACB: {tpl_gacb}\n  - XYZ : {current_xyz}")

    for i in range(START_MOL, END_MOL + 1):
        print(f"\n{'='*40}\nProcessing Molecule {i}\n{'='*40}")
        
        # This formula calculates the atom offset based on the reference (49)
        # But it does not depend on the FILE named mol49.
        offset = (i - BASE_MOL_IDX) * ATOMS_PER_MOL
        
        # Define filenames
        proj_gaca = f"mol{i}_GACA"
        inp_gaca  = f"{proj_gaca}.inp"
        out_gaca  = f"{proj_gaca}.out"
        wfn_gaca  = f"{proj_gaca}-RESTART.wfn" # Auto-generated name by CP2K

        proj_gacb = f"mol{i}_GACB"
        inp_gacb  = f"{proj_gacb}.inp"
        out_gacb  = f"{proj_gacb}.out"
        wfn_gacb  = f"{proj_gacb}-RESTART.wfn"

        proj_hab  = f"mol{i}_AB_coupling"
        inp_hab   = f"{proj_hab}.inp"
        out_hab   = f"{proj_hab}.out"

        # --- 1. GACA ---
        print("--- Step 1: GACA ---")
        if is_calc_finished(out_gaca):
            print(f"    [Skip] {out_gaca} already finished successfully.")
        else:
            if os.path.exists(out_gaca):
                print(f"    [Info] Found incomplete {out_gaca}, re-running...")
            # Use the explicit template variable
            generate_input(tpl_gaca, inp_gaca, proj_gaca, current_xyz, offset)
            run_cp2k(inp_gaca, out_gaca)
        strength_gaca = extract_strength(out_gaca)

        # --- 2. GACB ---
        print("--- Step 2: GACB ---")
        if is_calc_finished(out_gacb):
            print(f"    [Skip] {out_gacb} already finished successfully.")
        else:
            if os.path.exists(out_gacb):
                print(f"    [Info] Found incomplete {out_gacb}, re-running...")
            # Use the explicit template variable
            generate_input(tpl_gacb, inp_gacb, proj_gacb, current_xyz, offset)
            run_cp2k(inp_gacb, out_gacb)
        strength_gacb = extract_strength(out_gacb)

        # --- 3. Coupling ---
        print("--- Step 3: Coupling ---")
        if not strength_gaca or not strength_gacb:
            print("[Error] Missing Strength, skipping coupling.")
            continue
        
        # Check if WFN exists
        if not os.path.exists(wfn_gaca) or not os.path.exists(wfn_gacb):
            print(f"[Error] WFN missing: {wfn_gaca} or {wfn_gacb}")
            continue

        if is_calc_finished(out_hab):
             print(f"    [Skip] {out_hab} already finished successfully.")
        else:
            # Use the explicit template variable
            generate_input(tpl_hab, inp_hab, proj_hab, current_xyz, offset,
                           wfn_replace_map={'GACA': wfn_gaca, 'GACB': wfn_gacb},
                           strength_map={'GACA': strength_gaca, 'GACB': strength_gacb})
            run_cp2k(inp_hab, out_hab)
        
        print(f"[DONE] Molecule {i} finished.")

if __name__ == "__main__":
    main()
