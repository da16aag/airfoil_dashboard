import numpy as np
from scipy.interpolate import splprep, splev
import streamlit as st
from shapely.geometry import LineString, Polygon
import pyvista as pv
pv.start_xvfb()
import os
import imageio

def convert_pixel_to_custom(px, py, cw, ch, x_min_val, x_max_val, y_min_val, y_max_val):
    """Converts pixel coordinates to custom coordinates."""
    custom_x = x_min_val + (px / cw) * (x_max_val - x_min_val)
    custom_y = y_min_val + (1 - py / ch) * (y_max_val - y_min_val) # Y-axis usually inverted in pixels
    return custom_x, custom_y

def convert_custom_to_pixel(cx, cy, cw, ch, x_min_val, x_max_val, y_min_val, y_max_val):
    """Converts custom coordinates to pixel coordinates for drawing on PIL image."""
    x_range = x_max_val - x_min_val
    y_range = y_max_val - y_min_val

    # Avoid division by zero if ranges are zero
    px = int(((cx - x_min_val) / x_range) * cw) if x_range != 0 else 0
    py = int(ch - ((cy - y_min_val) / y_range) * ch) if y_range != 0 else 0 # Y-axis usually inverted in pixels
    return px, py

def interpolate_airfoil_and_close(x, y, num_points=500, smoothness=0.0001):
    """
    Interpolates airfoil points using a B-spline and then explicitly closes the curve.

    Args:
        x (np.array): X coordinates of the original points.
        y (np.array): Y coordinates of the original points.
        num_points (int): Number of points for the interpolated curve.
        smoothness (float): Smoothing factor for the spline.
                            Higher values mean more smoothing.

    Returns:
        tuple: (x_interp_closed, y_interp_closed) interpolated coordinates of the closed curve.
    """
    if len(x) < 4: # Need at least 4 points for a cubic spline (k=3)
        st.warning("Not enough points for a smooth spline. Need at least 4 points for cubic spline. Plotting direct lines instead.")
        return np.array(x), np.array(y) # Return original points if not enough for spline

    # Fit the B-spline to the original set of points.
    # The degree k must be <= m-1 where m is the number of data points.
    # For a cubic spline, k=3. Ensure k does not exceed number of points - 1.
    k_val = min(3, len(x) - 1)

    if k_val < 1: # Cannot create a spline with less than 2 points for k=1, or 4 for k=3
        st.warning(f"Not enough points ({len(x)}) for a B-spline of degree {k_val}. Plotting direct lines.")
        return np.array(x), np.array(y)

    tck, u = splprep([x, y], s=smoothness, k=k_val)

    # Generate new parameter values to create a high-resolution curve
    u_new = np.linspace(u.min(), u.max(), num_points)
    x_interp, y_interp = splev(u_new, tck)

    # Explicitly close the loop by appending the first interpolated point
    x_interp_closed = np.append(x_interp, x_interp[0])
    y_interp_closed = np.append(y_interp, y_interp[0])

    return x_interp_closed, y_interp_closed

def check_airfoil_overlap(interpolated_x, interpolated_y):
    """
    Checks if the interpolated airfoil curve self-intersects.

    Args:
        interpolated_x (np.ndarray): X coordinates of the interpolated curve.
        interpolated_y (np.ndarray): Y coordinates of the interpolated curve.

    Returns:
        tuple: (bool, str) - True if overlap detected, False otherwise.
                           - A descriptive message.
    """
    if len(interpolated_x) < 3:
        return False, "Not enough points for overlap check." # Cannot form a polygon

    # Convert coordinates to a list of (x, y) tuples
    coords = list(zip(interpolated_x, interpolated_y))

    try:
        # Create a LineString from the points
        line = LineString(coords)

        # A simple check for LineString self-intersection
        if not line.is_simple:
            return True, "The interpolated curve self-intersects (crosses itself)."

        # More robust check by attempting to create a Polygon.
        # A non-valid polygon indicates self-intersection, rings not closed, etc.
        # `is_valid` checks for topological correctness.
        polygon = Polygon(coords)
        if not polygon.is_valid:
            return True, "The interpolated curve forms an invalid polygon (likely self-intersecting or malformed)."

        # Check for zero area, which might happen if points are collinear or duplicate
        if polygon.area == 0:
            return True, "The airfoil has zero area (points are collinear or degenerate)."

        return False, "No overlap detected. The airfoil shape is valid."

    except Exception as e:
        # Catch potential errors from Shapely for very degenerate cases
        return True, f"An error occurred during overlap check: {e}"


def vtk_to_png_surface_wireframe(vtk_file_path, output_image_path=None,
                              line_color='black', line_width=1,
                              mesh_color='lightgray',
                              bounds_margin=0.02,
                              z_tolerance=1e-3,
                              window_size=(1600, 1200)):
    """
    Renders a zoomed-in 2D orthographic image of the airfoil geometry from a 3D mesh.

    Parameters:
        vtk_file_path (str): Path to the VTK mesh file.
        output_image_path (str): Output image file path. If None, autogenerated.
        line_color (str): Color of wireframe edges.
        line_width (float): Width of mesh edges.
        mesh_color (str): Fill color of the mesh.
        bounds_margin (float): Extra margin added around airfoil bounds (relative).
        z_tolerance (float): How flat in Z to consider the airfoil region.
        window_size (tuple): Size of the image (width, height).

    Returns:
        str: Path to saved PNG image.
    """

    # Load mesh
    mesh = pv.read(vtk_file_path)

    # Extract the nearly-flat 2D slice where airfoil lies (assumes in XY plane)
    z_vals = mesh.points[:, 2]
    flat_mask = (z_vals >= z_vals.min() - z_tolerance) & (z_vals <= z_vals.min() + z_tolerance)
    flat_mesh = mesh.extract_points(flat_mask, adjacent_cells=True)

    if flat_mesh.n_points == 0:
        raise ValueError("No nearly-2D region found — check z_tolerance or mesh orientation.")

    # Expand bounds a bit to give margin in the plot
    bounds = list(flat_mesh.bounds)  # (xmin, xmax, ymin, ymax, zmin, zmax)
    x_margin = (bounds[1] - bounds[0]) * bounds_margin
    y_margin = (bounds[3] - bounds[2]) * bounds_margin
    cropped = flat_mesh.clip_box([  # crop tightly around airfoil
        bounds[0] - x_margin, bounds[1] + x_margin,
        bounds[2] - y_margin, bounds[3] + y_margin,
        bounds[4], bounds[5]
    ], invert=False)

    # Set up 2D orthographic plot
    plotter = pv.Plotter(off_screen=True, window_size=window_size)
    plotter.add_mesh(cropped, color=mesh_color, show_edges=True,
                     edge_color=line_color, line_width=line_width, lighting=False)

    plotter.view_xy()
    plotter.enable_parallel_projection()
    plotter.reset_camera()
    plotter.camera.zoom(25)
    shift_amount = 4.5
    camera = plotter.camera
    camera.position = [camera.position[0] - shift_amount, camera.position[1], camera.position[2]]
    camera.focal_point = [camera.focal_point[0] - shift_amount, camera.focal_point[1], camera.focal_point[2]]
    # Output filename
    if output_image_path is None:
        output_image_path = os.path.splitext(vtk_file_path)[0] + '_wireframe.png'

    plotter.show(screenshot=output_image_path)
    plotter.close()

    return output_image_path

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

def play_video_on_streamlit(video_path: str, title: str = None):
    """
    Plays a video file in a Streamlit application.

    Args:
        video_path (str): The absolute or relative file path to the video
                          (e.g., 'animations/U_animation.mp4').
        title (str, optional): An optional title to display above the video.
                               Defaults to None.
    """
    if not os.path.exists(video_path):
        st.error(f"Video file not found at: `{video_path}`")
        return

    # Display an optional title if provided
    if title:
        st.subheader(title)

    try:
        # Open the video file in binary read mode ('rb')
        # Using 'with' statement ensures the file is properly closed after reading
        with open(video_path, 'rb') as video_file:
            # Read the entire video file into bytes
            video_bytes = video_file.read()
            # Use Streamlit's st.video function to display the video bytes
            st.video(video_bytes)
        st.success(f"Video loaded successfully from `{video_path}`")
    except Exception as e:
        # Catch any potential errors during file reading or Streamlit processing
        st.error(f"An error occurred while playing the video from `{video_path}`: {e}")
