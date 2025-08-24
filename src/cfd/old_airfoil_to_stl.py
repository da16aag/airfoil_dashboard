import numpy as np
import trimesh
import os
import traceback

def create_airfoil_stl(input_dat_file, output_stl_file, chord_length=1.0, thickness=0.001):
    """
    Converts 2D airfoil coordinates into a 3D STL mesh using trimesh.
    Args:
        input_dat_file (str): Path to the airfoil .dat file.
                              Assumes a format with x and y coordinates separated by spaces,
                              starting from the trailing edge, going over the upper surface
                              to the leading edge, and then over the lower surface back to
                              the trailing edge.
        output_stl_file (str): Path where the STL file will be saved.
        chord_length (float): Desired chord length for the airfoil. The input .dat
                              file is typically normalized to a chord of 1.
        thickness (float): The thickness of the 3D airfoil in the Z-direction.
                           This creates a 2D-like body for 2D simulations in OpenFOAM
                           (by setting appropriate boundary conditions).
    """
    try:

        # Load airfoil coordinates
        data = np.loadtxt(input_dat_file, skiprows=0) # Skiprows=1 to skip header line if present
        x_coords = data[:, 0]
        y_coords = data[:, 1]

        # Scale the coordinates to the desired chord length
        x_coords *= chord_length
        y_coords *= chord_length

        # Create 2D points for the polygon
        points_2d = np.vstack((x_coords, y_coords)).T

        # Close the loop if not already closed (trailing edge points might be slightly off)
        if not np.isclose(points_2d[0], points_2d[-1]).all():
            points_2d = np.append(points_2d, [points_2d[0]], axis=0)

        # Create a 2D polygon (cross-section)
        airfoil_polygon = trimesh.load_path(points_2d)

        # Extrude the 2D polygon into a 3D mesh
        # This creates a solid body with the specified thickness
        airfoil_mesh = airfoil_polygon.extrude(thickness)

        airfoil_mesh.apply_translation([0, 0, -thickness/2])
        airfoil_mesh.metadata['name'] = 'airfoil'
        airfoil_mesh.export(output_stl_file)
        print(f"STL file '{output_stl_file}' created successfully.")
        return [1]

    except FileNotFoundError:
        print(f"Error: Input file '{input_dat_file}' not found.")
        return [0]
    except Exception as e:
        print(f"An error occurred: {e}")
        return [0]
if __name__ == "__main__":
    input_file      = "airfoil_coordinates.txt"
    output_directory = "./cfd/Mesh/constant/triSurface"
    output_filename = "airfoil.stl"
    output_file     = os.path.join(output_directory, output_filename)

    desired_chord   = 1.0 # meters
    airfoil_thic    = 0.1 # meters (for 2D simulation extrusion)
    create_airfoil_stl(input_file, output_file, desired_chord, airfoil_thic)
