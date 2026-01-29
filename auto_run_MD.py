import os
import sys

# --- Core Settings ---

# 1. Template file name (The name of the gaff_loop_25.in file on your canvas)
template_file = "gaff_loop_25.in"

# 2. Simulation settings
data_file_prefix = "test"
num_iterations = 2000  # 2000 iterations * 20 ps/iter = 40,000 ps = 40 ns
lammps_command = "mpiexec -np 32 lmp_mpi" # Your command to run LAMMPS

# 3. Placeholders in template (To ensure we replace the correct lines)
read_data_tag = "read_data"
log_tag = "log"
dump_tag = "trajectory_strj"  # Ensure the dump line contains this unique keyword
write_data_tag = "write_data"

# --- Automation Script ---

print(f"--- Preparing LAMMPS loop execution ---")
print(f"Template: {template_file}")
print(f"Total Iterations: {num_iterations} (Total time: {num_iterations * 20} ps)")
print(f"Command: {lammps_command}")
print("---------------------------------------")

# 1. Read template file content
try:
    with open(template_file, 'r', encoding="utf-8") as f:
        original_lines = f.readlines()
except FileNotFoundError:
    print(f"FATAL ERROR: Template file '{template_file}' not found.")
    print("Please ensure this file is in the same directory as this Python script.")
    sys.exit(1)

# 2. Start loop (Starting from 0 to match test0.data)
for i in range(num_iterations):  # Loop 0, 1, 2, ..., 1999
    
    # Define file names for this iteration
    read_data_file = f"{data_file_prefix}{i}.data"        # i=0: test0.data
    write_data_file = f"{data_file_prefix}{i + 1}.data"    # i=0: test1.data
    lammpstrj_file = f"trajectory_strj_{i + 1}.lammpstrj" # i=0: ..._1.lammpstrj
    log_file = f"thermodata_{i + 1}.log"       # i=0: ..._1.log
    temp_input_file = f"temp_input_{i + 1}.in"   # i=0: ..._1.in
    
    # Log progress (+1 so printing starts from "Loop 1")
    print(f"\n>>> Iteration {i + 1}/{num_iterations}...") 

    # 3. Check if the input file from the previous step exists
    if not os.path.exists(read_data_file):
        print(f"ERROR: Input file {read_data_file} does not exist!")
        print("The simulation may have failed in the previous step. Stopping loop.")
        break
    
    print(f"  Reading: {read_data_file}")

    # 4. Create new temporary input file
    new_lines = []
    for line in original_lines:
        stripped_line = line.strip()

        # Update filenames based on current iteration
        if stripped_line.startswith(read_data_tag):
            line = f"read_data {read_data_file}\n"
        elif stripped_line.startswith(log_tag):
            line = f"log {log_file}\n"
        elif stripped_line.startswith("dump") and dump_tag in stripped_line:
            line = f"dump RTlmp all atom 500 {lammpstrj_file}\n"
        # Ensure write_data is updated correctly
        elif stripped_line.startswith(write_data_tag):
            line = f"write_data {write_data_file}\n"
        
        new_lines.append(line)

    # 5. Write temporary input file
    try:
        with open(temp_input_file, 'w', encoding="utf-8") as f:
            f.writelines(new_lines)
    except IOError as e:
        print(f"ERROR: Unable to write temporary file {temp_input_file}: {e}")
        break

    # 6. Run LAMMPS
    print(f"  Executing: {lammps_command} -in {temp_input_file}")
    run_command = f"{lammps_command} -in {temp_input_file}"
    
    # os.system waits for the command to finish
    exit_code = os.system(run_command)

    # 7. Check if LAMMPS ran successfully
    if exit_code != 0:
        print(f"ERROR: LAMMPS returned error code {exit_code} at iteration {i + 1}.")
        print(f"Please check the log file {log_file} and output.")
        print("Stopping loop.")
        break
    else:
        print(f"  Success: Generated {write_data_file}")

    # 8. [Cleanup] Remove the temporary input file used
    try:
        os.remove(temp_input_file)
    except OSError as e:
        print(f"  (Warning: Could not delete temporary file {temp_input_file}: {e})")

print("\n---------------------------------------")
print("Automation script execution finished.")
