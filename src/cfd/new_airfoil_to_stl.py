import numpy as np
import trimesh
import os

# Optional: import pygalmesh if you want to remesh directly after STL export
import pygalmesh

def create_airfoil_stl(input_dat_file, output_stl_file, chord_length=1.0, thickness=0.001, remesh=True):
    """
    Converts 2D airfoil coordinates into a 3D STL mesh using trimesh,
    then remeshes the STL using pygalmesh for better triangle quality.
    """
    try:
        # Load airfoil coordinates
        data = np.loadtxt(input_dat_file, skiprows=0)
        x_coords = data[:, 0]
        y_coords = data[:, 1]

        # Scale coordinates
        x_coords *= chord_length
        y_coords *= chord_length
        points_2d = np.vstack((x_coords, y_coords)).T

        # Close loop if necessary
        if not np.isclose(points_2d[0], points_2d[-1]).all():
            points_2d = np.append(points_2d, [points_2d[0]], axis=0)

        # Remove duplicate/near-duplicate points to avoid degenerate triangles
        def clean_points(points, tol=1e-6):
            cleaned = [points[0]]
            for pt in points[1:]:
                if np.linalg.norm(pt - cleaned[-1]) > tol:
                    cleaned.append(pt)
            if np.linalg.norm(cleaned[0] - cleaned[-1]) < tol:
                cleaned[-1] = cleaned[0]
            return np.array(cleaned)
        points_2d = clean_points(points_2d)

        # Create a 2D polygon and extrude
        airfoil_polygon = trimesh.load_path(points_2d)
        airfoil_mesh = airfoil_polygon.extrude(thickness)
        airfoil_mesh.metadata['name'] = 'airfoil'
        airfoil_mesh.export(output_stl_file)
        print(f"STL file '{output_stl_file}' created successfully.")

        # === Surface remeshing with pygalmesh ===
        if remesh:
            # Output file names
            base, ext = os.path.splitext(output_stl_file)
            remeshed_file = base + '_remeshed.stl'
            print("Remeshing surface with pygalmesh for improved triangle quality ...")
            mesh = pygalmesh.remesh_surface(
                output_stl_file,
                max_edge_size_at_feature_edges=0.02,    # <-- adjust as needed
                min_facet_angle=25,                     # <-- recommended minimum angle
                max_radius_surface_delaunay_ball=0.1,   # <-- adjust as needed
                max_facet_distance=0.001,               # <-- controls fidelity to surface
                verbose=True
            )
            mesh.write(remeshed_file)
            print(f"Remeshed STL file created: '{remeshed_file}'")

    except FileNotFoundError:
        print(f"Error: Input file '{input_dat_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    input_file      = "airfoil_coordinates.txt"
    output_file     = "airfoil.stl"
    desired_chord   = 1.0
    airfoil_thic    = 0.001
    create_airfoil_stl(input_file, output_file, desired_chord, airfoil_thic)

