import os
import pyvista as pv
import imageio
import numpy as np

# # Set up paths
# vtk_dir = './VTK/'
# output_dir = './animations/'
# frame_dir = os.path.join(output_dir, 'frames')
# os.makedirs(frame_dir, exist_ok=True)
#
# # List of fields to visualize (must match field names in VTK files)
# fields = ['U', 'p']  # Add more as needed
#
# # Find all VTK files matching your case naming pattern
# vtk_files = sorted([f for f in os.listdir(vtk_dir)
#                     if f.startswith('Run_') and f.endswith('.vtk')])
#
# if not vtk_files:
#     raise RuntimeError(f"No VTK files found in {vtk_dir} matching 'Run_*.vtk'")
#
# print(f"Found {len(vtk_files)} VTK files.")

# def plot_and_save(vtk_file, output_name, scalar_field):
#     mesh = pv.read(os.path.join(vtk_dir, vtk_file))
#     print(f"Processing {vtk_file}, available fields: {mesh.array_names}")
#     if scalar_field not in mesh.array_names:
#         raise ValueError(f"Field '{scalar_field}' not found in {vtk_file}. Available fields: {mesh.array_names}")
#     if mesh.n_points > 2:
#         slice_mesh = mesh.slice(normal='z')
#     else:
#         slice_mesh = mesh
#     plotter = pv.Plotter(off_screen=True, window_size=[1920, 1088])
#     plotter.add_mesh(slice_mesh, scalars=scalar_field, cmap='jet')
#     plotter.add_scalar_bar(title=scalar_field)
#     plotter.view_xy()
#     if scalar_field == 'U':
#         U_array = mesh ["U"]
#         if U_array.shape[1] == 3:
#             mesh["vectors"] = U_array
#             glyphs = mesh.glyph(orient='vectors', scale=True,factor=0.05)
#             plotter.add_mesh(glyphs, cmap='jet',show_scalar_bar=False)
#
#
#
#
#
#
#     corner1 = (-0.1, -0.1)
#     corner2 = (4, 0.1)
#     xmin = min(corner1[0], corner2[0])
#     xmax = max(corner1[0], corner2[0])
#     ymin = min(corner1[1], corner2[1])
#     ymax = max(corner1[1], corner2[1])
#     zmin, zmax = 0, 0  # For 2D plane or small thickness if you want
#     bounds = [xmin, xmax, ymin, ymax, zmin, zmax]
#     plotter.reset_camera(bounds=bounds)
#     plotter.camera.zoom(1.7)
#     plotter.show()
#     plotter.screenshot(os.path.join(frame_dir, output_name))
#     plotter.close()
#
#
# # Loop over each field to visualize
# for field in fields:
#     # Generate frames for each timestep and field
#     for i, vtk_file in enumerate(vtk_files):
#         filename = f'{field}_frame_{i:04d}.png'
#         try:
#             plot_and_save(vtk_file, filename, field)
#         except ValueError as e:
#             print(e)
#             break  # Skip this field if not present
#
#     # Create animation for this field
#     png_files = sorted([f for f in os.listdir(frame_dir) if f.startswith(field + '_frame_') and f.endswith('.png')])
#     if not png_files:
#         print(f"No frames generated for field '{field}'. Skipping video creation.")
#         continue
#     images = []
#     for png in png_files:
#         img_path = os.path.join(frame_dir, png)
#         images.append(imageio.imread(img_path))
#     video_path = os.path.join(output_dir, f'{field}_contour.mp4')
#     imageio.mimsave(video_path, images, fps=10)
#     print(f"Animation saved to {video_path}")
#
def generate_vtk_animations(vtk_dir='./VTK/', output_dir='./animations/', fields=['U', 'p']):
    """
    Generates animations from VTK files, visualizing specified scalar fields
    and optionally vector fields (for 'U').

    Args:
        vtk_dir (str): Directory containing VTK files.
        output_dir (str): Directory to save animation frames and final videos.
        fields (list): List of scalar field names to visualize (e.g., ['U', 'p']).
                       For 'U', if it's a 3-component vector, glyphs will be added.
    """

    frame_dir = os.path.join(output_dir, 'frames')
    os.makedirs(frame_dir, exist_ok=True)

    vtk_files = sorted([f for f in os.listdir(vtk_dir)
                         if f.startswith('Run_') and f.endswith('.vtk')])

    if not vtk_files:
        raise RuntimeError(f"No VTK files found in {vtk_dir} matching 'Run_*.vtk'")

    print(f"Found {len(vtk_files)} VTK files.")

    def plot_and_save(vtk_file, output_name, scalar_field):
        mesh = pv.read(os.path.join(vtk_dir, vtk_file))
        print(f"Processing {vtk_file}, available fields: {mesh.array_names}")

        if scalar_field not in mesh.array_names:
            raise ValueError(f"Field '{scalar_field}' not found in {vtk_file}. Available fields: {mesh.array_names}")

        # Handle 2D slicing for 3D meshes or use mesh directly for 2D
        if mesh.n_points > 2 :  # Check if it's a 3D mesh
            slice_mesh = mesh.slice(normal='z')
        else:
            slice_mesh = mesh

        plotter = pv.Plotter(off_screen=True, window_size=[1920, 1088])
        plotter.add_mesh(slice_mesh, scalars=scalar_field, cmap='jet')
        plotter.add_scalar_bar(title=scalar_field)
        plotter.view_xy()

        if scalar_field == 'U':
            U_array = mesh["U"]
            if U_array.ndim == 2 and U_array.shape[1] == 3:  # Check if it's a 3D vector field
                mesh["vectors"] = U_array
                glyphs = mesh.glyph(orient='vectors', scale=True, factor=0.05)
                plotter.add_mesh(glyphs, cmap='jet', show_scalar_bar=False)

        # Define custom camera bounds
        corner1 = (-0.1, -0.1)
        corner2 = (4, 0.1)
        xmin = min(corner1[0], corner2[0])
        xmax = max(corner1[0], corner2[0])
        ymin = min(corner1[1], corner2[1])
        ymax = max(corner1[1], corner2[1])
        zmin, zmax = 0, 0  # For 2D plane or small thickness
        bounds = [xmin, xmax, ymin, ymax, zmin, zmax]

        plotter.reset_camera(bounds=bounds)
        plotter.camera.zoom(1.7)
        plotter.show()  # This might not be needed for off_screen=True, but doesn't hurt.
        plotter.screenshot(os.path.join(frame_dir, output_name))
        plotter.close()

    for field in fields:
        for i, vtk_file in enumerate(vtk_files):
            filename = f'{field}_frame_{i:04d}.png'
            try:
                plot_and_save(vtk_file, filename, field)
            except ValueError as e:
                print(e)
                break

        png_files = sorted([f for f in os.listdir(frame_dir) if f.startswith(field + '_frame_') and f.endswith('.png')])
        if not png_files:
            print(f"No frames generated for field '{field}'. Skipping video creation.")
            continue

        images = []
        for png in png_files:
            img_path = os.path.join(frame_dir, png)
            images.append(imageio.imread(img_path))

        video_path = os.path.join(output_dir, f'{field}_contour.mp4')
        imageio.mimsave(video_path, images, fps=10)
        print(f"Animation saved to {video_path}")

if __name__ == "__main__":
    # Set up paths for VTK files and output animations
    vtk_directory = './VTK/'
    output_directory = './animations/'

    # Define the fields you want to visualize from your VTK files
    # 'U' typically represents velocity (a vector field), 'p' for pressure (scalar).
    fields_to_visualize = ['U', 'p']  # Add or remove fields as per your VTK data

    # Call the main function to start the animation generation process
    generate_vtk_animations(vtk_dir=vtk_directory, output_dir=output_directory, fields=fields_to_visualize)

