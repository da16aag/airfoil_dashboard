import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import os
from streamlit_stl import stl_from_text


from cfd_runner import (
    run_openfoam_meshing,
    run_openfoam_simulation,
    )

from old_airfoil_to_stl import create_airfoil_stl

from utils_old import (
    convert_pixel_to_custom,
    convert_custom_to_pixel,
    interpolate_airfoil_and_close,
    check_airfoil_overlap,
    vtk_to_png_surface_wireframe,
    generate_vtk_animations,
    play_video_on_streamlit,
)

from components import (
        create_grid_image,
    )
from history_manager import (
    initialize_session_state,
    add_to_history,
    undo_action,
    redo_action,
    clear_all_points,
)

# Set the page configuration for a wider layout
st.set_page_config(layout="centered", page_title="2D Airfoil OpenFoam Simulation")

# --- Initialize session state for storing points and history ---
initialize_session_state()

# --- Title and Description ---
st.title("2D Airfoil OpenFoam Simulation")
st.markdown(
    """
    Click anywhere on the image below to define custom points. Coordinates will be transformed to a custom X and Y range,
    stored, displayed, and a spline will be drawn directly on the canvas.
    Once you have enough points, an interpolated airfoil shape will be generated and plotted below!
    The interpolated airfoil will be used to create the geometry (stl) that will be used for the simulation
    """
)

# --- Sidebar Controls for Canvas Properties and Custom Ranges ---
st.sidebar.header("Custom Coordinate Ranges")

x_min = st.sidebar.number_input("X Min", value=0.0, step=0.1, format="%.2f", help="Minimum value for the X-axis.")
x_max = st.sidebar.number_input("X Max", value=1.0, step=0.1, format="%.2f", help="Maximum value for the X-axis.")
if x_min >= x_max:
    st.sidebar.warning("X Max must be greater than X Min.")
    x_max = x_min + 0.1

y_min = st.sidebar.number_input("Y Min", value=-0.5, step=0.1, format="%.2f", help="Minimum value for the Y-axis.")
y_max = st.sidebar.number_input("Y Max", value=0.5, step=0.1, format="%.2f", help="Maximum value for the Y-axis.")
if y_min >= y_max:
    st.sidebar.warning("Y Max must be greater than Y Min.")
    y_max = y_min + 0.1

st.sidebar.markdown("---")
st.sidebar.header("Grid Steps")

x_grid_step = st.sidebar.number_input("X Grid Step", min_value=0.01, max_value=1.0, value=0.05, step=0.01, format="%.2f", help="Interval between grid lines on the X-axis in custom units.")
y_grid_step = st.sidebar.number_input("Y Grid Step", min_value=0.01, max_value=1.0, value=0.05, step=0.01, format="%.2f", help="Interval between grid lines on the Y-axis in custom units.")

st.sidebar.markdown("---")
st.sidebar.header("Airfoil Interpolation Settings")
num_points_interp = st.sidebar.slider("Interpolated Points", min_value=100, max_value=1000, value=500, step=50, help="Number of points for the interpolated airfoil curve.")
smoothness_interp = st.sidebar.number_input("Smoothness (s)", min_value=0.0, max_value=1.0, value=0.0001, step=0.0001, format="%.4f", help="Smoothing factor for the B-spline. Higher values mean more smoothing.")

# --- Display the image and capture coordinates ---
st.subheader("Clickable Area")
st.write(f"X-axis from **{x_min}** to **{x_max}**, Y-axis from **{y_min}** to **{y_max}**.")

canvas_width = 600
canvas_height = 600

current_image = create_grid_image(
    canvas_width, canvas_height,
    x_min, x_max, y_min, y_max,
    x_grid_step, y_grid_step,
    st.session_state.points,
    convert_custom_to_pixel # Pass the function as an argument
)

# Use the canvas_key_counter to force re-render/reset of the image coordinates component


# Use the canvas_key_counter to force re-render/reset of the image coordinates component
value = streamlit_image_coordinates(
    current_image,
    key=f"canvas_clicks_{st.session_state.canvas_key_counter}" # Unique key
)

# --- Process and Display Coordinates ---
st.subheader("Clicked Coordinates:")
# Only add points if not suppressed
if value and not st.session_state.suppress_point_add:
    clicked_custom_x, clicked_custom_y = convert_pixel_to_custom(
        value['x'], value['y'], canvas_width, canvas_height,
        x_min, x_max, y_min, y_max
    )

    current_click_tuple = (clicked_custom_x, clicked_custom_y)

    # Check if this click is genuinely new and hasn't been processed yet in this rerun
    if st.session_state.last_click_processed != current_click_tuple:

        st.session_state.points.append({'x': clicked_custom_x, 'y': clicked_custom_y})
        st.session_state.last_click_processed = current_click_tuple
        add_to_history() # Add new state to history
        st.session_state.file_saved = False # Reset file_saved flag if new points are added
        st.rerun() # Rerun to update the image with the new point
elif not value: # If there's no current 'value' from the component, clear last_click_processed.
    st.session_state.last_click_processed = None

if st.session_state.points:
    for i, point in enumerate(st.session_state.points):
        st.write(f"Point {i+1}: X: **{point['x']:.2f}**, Y: **{point['y']:.2f}**")
else:
    st.info("Click on the canvas above to start collecting coordinates.")

st.markdown(
    """
    ---
    <small>Coordinates displayed are in the custom range you defined.</small>
    """,
    unsafe_allow_html=True
)

# --- Undo/Redo/Clear Buttons ---
st.markdown("---")
st.subheader("Drawing Controls")
col1, col2, col3, col4 = st.columns(4) # Added a column for the save button

with col1:
    if st.button("⏪ Undo", help="Go back to the previous step."):
        undo_action()
        st.rerun()

with col2:
    if st.button("⏩ Redo", help="Go forward to the next step."):
        redo_action()
        st.rerun()

with col3:
    if st.button("🗑️ Clear All Points", help="Removes all collected points and spline."):
        clear_all_points()
        st.rerun()

## Interpolated Airfoil Plot

st.markdown("---")
st.subheader("Interpolated Airfoil Plot")

if len(st.session_state.points) >= 4:
    x_coords_input = np.array([p['x'] for p in st.session_state.points])
    y_coords_input = np.array([p['y'] for p in st.session_state.points])

    # Generate interpolated points for display and potential saving
    try:
        x_interp, y_interp = interpolate_airfoil_and_close(
            x_coords_input, y_coords_input,
            num_points=num_points_interp,
            smoothness=smoothness_interp
        )

        st.session_state.overlap_detected, st.session_state.overlap_message = check_airfoil_overlap(x_interp, y_interp)

        if st.session_state.overlap_detected:
            st.error(f"Airfoil Overlap Detected: {st.session_state.overlap_message} Please adjust your points.")
        else:

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(x_coords_input, y_coords_input, 'ro', label='Original Points')
            ax.plot(x_interp, y_interp, 'b-', label='Interpolated Closed Airfoil Shape')
            ax.set_xlabel('X Coordinate')
            ax.set_ylabel('Y Coordinate')
            ax.set_title('Interpolated Airfoil Shape')
            ax.set_aspect('equal', adjustable='box') # Maintain aspect ratio
            ax.grid(True)
            ax.legend()
            st.pyplot(fig)

            # Prepare the data content as a string for saving
            output_data_string = ""
            for i in range(len(x_interp)):
                output_data_string += f"{x_interp[i]:.6f}\t{y_interp[i]:.6f}\n"

            with col4: # Put save button in the new column
                save_disabled = st.session_state.overlap_detected or st.session_state.file_saved
                if st.button("💾 Save Coordinates", help="Save the interpolated airfoil coordinates to a text file."):
                    file_name =os.path.join("airfoil_coordinates.txt")
                    try:
                        with open(file_name, "w") as f:
                            f.write(output_data_string)
                        st.success(f"Airfoil coordinates saved to **{file_name}**")
                        st.session_state.file_saved = True # Set flag after saving
                        st.session_state.suppress_point_add = True # Suppress further clicks after saving
                        st.session_state.last_click_processed = None # Clear any stale click when entering save mode
                        st.session_state.canvas_key_counter += 1 # Force reset of image coordinates component value
                        st.rerun() # Rerun to show success message and disable drawing
                    except IOError as e:
                        st.error(f"Error saving file: {e}")
                # This 'elif' block is for displaying the info message when file_saved is True
                elif st.session_state.file_saved:
                    st.info("File saved. Clear, Undo, or Redo to enable drawing again.")

    except Exception as e:
        st.error(f"Error generating interpolated airfoil plot: {e}. Try adjusting smoothness or adding more points.")
else:
    st.warning("Please click at least **4** points on the canvas to generate a smooth interpolated airfoil plot.")
    # Ensure suppress_point_add is False if not enough points to plot/save
    if len(st.session_state.points) < 4 and st.session_state.file_saved:
        st.session_state.file_saved = False # Reset if points drop below threshold after a save
        st.session_state.suppress_point_add = False # Allow drawing again
        st.session_state.last_click_processed = None # Clear stale click if re-enabling drawing


# --- STL generation ---
FIXED_STL_THICKNESS = 0.1
FIXED_CHORD_LENGTH = 1.0

if st.session_state.file_saved:
    if st.button("⚙️ Generate STL File", help="Create a 3D STL model from the interpolated airfoil."):
        with st.spinner("Generating 3D STL model..."):
            input_file      = "airfoil_coordinates.txt"
            output_directory = "./cfd/Mesh/constant/triSurface"
            os.makedirs(output_directory, exist_ok=True)
            output_filename = "airfoil.stl"
            output_file     = os.path.join(output_directory, output_filename)
            generated_path =  create_airfoil_stl(input_file, output_file, FIXED_CHORD_LENGTH, FIXED_STL_THICKNESS)
            if generated_path:
                st.success(f"3D STL file generated successfully at **{generated_path}**!")
                st.session_state.stl_generated = True # Set flag
                # Clean up the temporary coordinate file
                #st.rerun()
            else:
                st.error("Failed to generate STL file.")


    if st.session_state.stl_generated: # Display STL viewer if generated
                    st.subheader("3D Airfoil Model Preview")
                    st.markdown(
                            """
                            Zoom In/Out to be able to display the preview
                            """
                    )
                    stl_output_path = os.path.join("cfd/Mesh/constant/triSurface", "airfoil.stl")
                    if os.path.exists(stl_output_path):
                        try:
                            with open(stl_output_path, "rb") as f:
                                stl_data = f.read()
                            # Display the STL using streamlit_stl.stl_from_text
                            stl_from_text(stl_data, height=400, width=600) # Removed 'key' as streamlit-stl might not support it
                            st.download_button(
                                label="Download 3D STL File",
                                data=stl_data,
                                file_name="airfoil_geometry.stl",
                                mime="application/octet-stream"
                            )
                        except Exception as e:
                            st.error(f"Error loading or displaying STL: {e}")
                    else:
                        st.warning("STL file not found for preview.")
    # --- Mesh & Simulation Results---
    if st.session_state.stl_generated:
        if st.button("⚙️ Generate Mesh File", help="Create a Mesh from the airfoil stl file."):
            with st.spinner("Generating Mesh...this may take a while."):
                try:
                    mesh =  run_openfoam_meshing("./cfd")
                    print(mesh)
                    if mesh:
                        st.success(f"Mesh was generated successfully")
                        st.session_state.meshing = True # Set flag
                    else:
                        st.error("Failed to generate the mesh file, check the terminal for details.")
                        st.session_state.meshing = False
                except Exception as e:
                    st.error(f"An error occurred during meshing: {e}")
                    st.session_state.meshing = False
        if st.session_state.meshing:
                        st.subheader("Airfoil Mesh Preview")
                        vtk_path = "cfd/Mesh/VTK/Mesh_0.vtk"
                        if os.path.exists(vtk_path):
                            try:
                                vtk_to_png_surface_wireframe(vtk_path)
                                # Assuming vtk_to_png_surface_wireframe saves to "mesh_preview.png"
                                st.image("cfd/Mesh/VTK/Mesh_0_wireframe.png", caption="Generated Airfoil Mesh")
                            except Exception as e:
                                st.error(f"Error displaying mesh preview: {e}")
                        else:
                            st.warning("VTK mesh file not found for preview. Meshing might have failed or not completed properly.")

        if st.session_state.meshing:
            if st.button("⚙️ Run Simulation", help="Create Velocity vector and Pressure contour scences using the generated mesh and obtain the coefficient of Lift and coefficient of Drag."):
                with st.spinner("Running the simulation...this may take a while longer."):
                    try:
                        solution_run =  run_openfoam_simulation("./cfd")
                        print(solution_run)
                        if solution_run:
                            st.success(f"Solutions were generated successfully")
                            st.session_state.running = True # Set flag
                        else:
                            st.error("Failed to solve, check the terminal for details.")
                            st.session_state.running = False
                    except Exception as e:
                        st.error(f"An error occurred during solution run: {e}")
                        st.session_state.running = False
            if st.session_state.running:
                st.subheader("Airfoil Pressure & Velocity scences")
                with st.spinner("Rendering Results...this may take a while longer."):
                    try:
                        vtk_directory = './cfd/Run/VTK/'
                        output_directory = './cfd/Run/animations/'
                        fields_to_visualize = ['U', 'p']
                        generate_vtk_animations(vtk_dir=vtk_directory, output_dir=output_directory, fields=fields_to_visualize)
                        video_path = "./cfd/Run/animations/p_contour.mp4"
                        play_video_on_streamlit(video_path,"Pressure Contour" )
                        video_path = "./cfd/Run/animations/U_contour.mp4"
                        play_video_on_streamlit(video_path,"Velocity vector" )
                    except Exception as e:
                        st.error(f"Error displaying mesh preview: {e}")
