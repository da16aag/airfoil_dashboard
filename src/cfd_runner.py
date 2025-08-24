import os
import subprocess


def run_openfoam_meshing(case_path: str):
    """
    Runs the OpenFOAM meshing process (blockMesh, surfaceFeatureExtract, snappyHexMesh).
    """
    print(f"Starting OpenFOAM meshing in {case_path}...")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))

        mesh_allrun_absolute_path = os.path.join(script_dir, case_path, "Mesh", "Allrun")

        process_cwd = os.path.join(script_dir, case_path, "Mesh")

        if not os.path.exists(mesh_allrun_absolute_path):
            raise FileNotFoundError(f"Allrun script not found at {mesh_allrun_absolute_path}")

        try:
            subprocess.run(["chmod", "+x", mesh_allrun_absolute_path], check=True, capture_output=True, text=True)
            print(f"DEBUG: Successfully made {mesh_allrun_absolute_path} executable.")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to make {mesh_allrun_absolute_path} executable: {e.stderr}")
            raise RuntimeError(f"Failed to set executable permissions for Allrun: {e.stderr}")

        process = subprocess.run(
            [mesh_allrun_absolute_path],
            cwd=process_cwd,
            capture_output=True,
            text=True,
            check=True
        )

        print("OpenFOAM meshing completed successfully.")
        print("STDOUT:\n", process.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Meshing failed with return code {e.returncode}")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")
        raise RuntimeError(f"OpenFOAM meshing failed: {e.stderr}")
    except FileNotFoundError as e:
        print(f"Error during OpenFOAM meshing: {e}")
        # Re-raise to be caught by Streamlit's error handling if preferred, or handle gracefully
        raise
    except Exception as e:
        print(f"Error during OpenFOAM meshing: {e}")
        return False

def run_openfoam_simulation(case_path: str):
    """
    Runs the main OpenFOAM simulation (e.g., simpleFoam).
    """
    print(f"Starting OpenFOAM simulation in {case_path}...")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))

        run_allrun_absolute_path = os.path.join(script_dir, case_path, "Run", "Allrun")

        process_cwd = os.path.join(script_dir, case_path, "Run")

        if not os.path.exists(run_allrun_absolute_path):
            raise FileNotFoundError(f"Allrun script not found at {run_allrun_absolute_path}")

        # Make sure the script is executable
        subprocess.run(["chmod", "+x", run_allrun_absolute_path], check=True)

        process = subprocess.run(
            [run_allrun_absolute_path],
            cwd=process_cwd,
            capture_output=True,
            text=True,
            check=True
        )

        if process.returncode != 0:
            print(f"Simulation failed with errors:\n{process.stderr}")
            raise RuntimeError(f"OpenFOAM simulation failed: {process.stderr}")
        print("OpenFOAM simulation completed successfully.")
        print("STDOUT:\n", process.stdout)
        return True
    except Exception as e:
        print(f"Error during OpenFOAM simulation: {e}")
        return False


