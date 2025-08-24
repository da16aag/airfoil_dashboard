import numpy as np
import trimesh
import os

def create_airfoil_stl(input_dat_file, output_stl_file, chord_length=1.0, thickness=0.001):
    """
    Converts 2D airfoil coordinates into a 3D STL mesh using trimesh.
    This version includes improved pre-processing of 2D coordinates to prevent
    degenerate triangles in the resulting 3D mesh.

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
        # Load airfoil coordinates from the .dat file
        # skiprows=0 assumes no header line; adjust if your file has one.
        data = np.loadtxt(input_dat_file, skiprows=0)
        x_coords = data[:, 0]
        y_coords = data[:, 1]

        # Scale the coordinates to the desired chord length
        x_coords *= chord_length
        y_coords *= chord_length

        # Create an array of 2D points (x, y)
        points_2d = np.vstack((x_coords, y_coords)).T

        # --- Start: Robust 2D Point Cleaning and Loop Closure ---
        # Define a small tolerance for identifying very close points.
        # This tolerance is relative to the chord length to ensure scalability.
        tolerance = 1e-7 * chord_length

        # Filter out points that are too close to the previous point.
        # This prevents extremely short segments that can lead to degenerate triangles.
        filtered_points = [points_2d[0]] # Start with the first point
        for i in range(1, len(points_2d)):
            # If the distance between the current point and the last filtered point
            # is greater than the tolerance, add the current point to the filtered list.
            if np.linalg.norm(points_2d[i] - filtered_points[-1]) > tolerance:
                filtered_points.append(points_2d[i])
        points_2d = np.array(filtered_points) # Update points_2d with the filtered list

        # Ensure the loop is perfectly closed at the trailing edge.
        # If the first and last points are already very close (within tolerance),
        # force the last point to be exactly identical to the first.
        # This avoids a tiny, problematic segment at the closure point.
        if np.isclose(points_2d[0], points_2d[-1], atol=tolerance).all():
            points_2d[-1] = points_2d[0]
        else:
            # If they are not close, append the first point to explicitly close the loop.
            points_2d = np.append(points_2d, [points_2d[0]], axis=0)

        # Remove the last point if it's a duplicate of the first point after closing.
        # trimesh.path.polygons.Polygon expects a non-redundant sequence of boundary points.
        if len(points_2d) > 1 and np.array_equal(points_2d[0], points_2d[-1]):
            points_2d = points_2d[:-1]
        # --- End: Robust 2D Point Cleaning and Loop Closure ---

        # Create a 2D polygon object from the cleaned and closed points.
        # trimesh.path.polygons.Polygon will internally triangulate this 2D shape.
        airfoil_polygon = trimesh.path.polygons.Polygon(points_2d)

        # Extrude the 2D polygon into a 3D mesh with the specified thickness.
        # This function handles the creation of the top/bottom cap faces (from the 2D triangulation)
        # and the side faces connecting them.
        airfoil_mesh = trimesh.creation.extrude_polygon(
            airfoil_polygon,
            height=thickness
        )

        # Assign a name to the mesh metadata (useful for some applications)
        airfoil_mesh.metadata['name'] = 'airfoil'

        # Export the generated 3D mesh to an STL file
        airfoil_mesh.export(output_stl_file)
        print(f"STL file '{output_stl_file}' created successfully.")

    except FileNotFoundError:
        print(f"Error: Input file '{input_dat_file}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    input_file      = "airfoil_coordinates.txt"
    output_file     = "airfoil.stl"
    desired_chord   = 1.0 # meters
    airfoil_thic    = 0.001 # meters (2D simulation)
    create_airfoil_stl(input_file, output_file, desired_chord, airfoil_thic)
