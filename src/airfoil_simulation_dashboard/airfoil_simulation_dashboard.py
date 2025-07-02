import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy.interpolate import splprep, splev
import matplotlib.pyplot as plt

# Set the page configuration for a wider layout
st.set_page_config(layout="centered", page_title="Streamlit Ginput Dashboard")

# --- Initialize session state for storing points and history ---
if 'points' not in st.session_state:
    st.session_state.points = []
if 'history' not in st.session_state:
    st.session_state.history = [[]] # Start with an empty state in history
if 'history_index' not in st.session_state:
    st.session_state.history_index = 0
if 'last_click_processed' not in st.session_state:
    st.session_state.last_click_processed = None # To prevent re-adding same point on rerun
if 'canvas_key_counter' not in st.session_state:
    st.session_state.canvas_key_counter = 0 # For forcing canvas reset
# New flag to control point addition during history operations
if 'suppress_point_add' not in st.session_state:
    st.session_state.suppress_point_add = False

# --- Helper function to add current state to history ---
def add_to_history():
    # Only add to history if suppress_point_add is False
    if st.session_state.suppress_point_add:
        return

    # Remove any "future" states if we're not at the end of history
    if st.session_state.history_index < len(st.session_state.history) - 1:
        st.session_state.history = st.session_state.history[:st.session_state.history_index + 1]
    
    current_points_copy = list(st.session_state.points)
    # Check if the current state is different from the last saved state
    if not st.session_state.history or current_points_copy != st.session_state.history[-1]:
        st.session_state.history.append(current_points_copy)
        st.session_state.history_index = len(st.session_state.history) - 1

# --- Airfoil Interpolation Function ---
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

# --- Title and Description ---
st.title("🖱️ Custom Coordinate Ginput Dashboard")
st.markdown(
    """
    Click anywhere on the image below to define custom points. Coordinates will be transformed to a custom X and Y range,
    stored, displayed, and a spline will be drawn directly on the canvas.
    Once you have enough points, an interpolated airfoil shape will be generated and plotted below!
    """
)

# --- Sidebar Controls for Canvas Properties and Custom Ranges ---
st.sidebar.header("Canvas Settings")

canvas_width = st.sidebar.slider("Canvas Width", min_value=100, max_value=800, value=600, step=50, help="Adjust the width of the clickable canvas (in pixels).")
canvas_height = st.sidebar.slider("Canvas Height", min_value=200, max_value=800, value=600, step=50, help="Adjust the height of the clickable canvas (in pixels).")

st.sidebar.markdown("---")
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


# --- Coordinate Transformation Functions ---
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

# --- Function to create the image with grid, border, clicked points, and spline ---
def create_grid_image(width, height, x_min_val, x_max_val, y_min_val, y_max_val, x_step, y_step, points_to_draw):
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except IOError:
        font = ImageFont.load_default() # Fallback to default font

    grid_color = (200, 200, 200)
    text_color = (50, 50, 50)
    axis_line_color = (100, 100, 100) # For X and Y axes

    # Draw vertical grid lines and X-axis labels
    # Use floor and ceil to ensure grid covers the entire custom range
    start_x_grid = np.floor(x_min_val / x_step) * x_step
    end_x_grid = np.ceil(x_max_val / x_step) * x_step

    current_x = start_x_grid
    while current_x <= end_x_grid:
        if x_min_val <= current_x <= x_max_val: # Only draw within bounds
            px, _ = convert_custom_to_pixel(current_x, y_min_val, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
            draw.line([(px, 0), (px, height)], fill=grid_color, width=1)
            draw.text((px + 2, 2), f"{current_x:.2f}", fill=text_color, font=font)
        current_x += x_step

    # Draw horizontal grid lines and Y-axis labels
    start_y_grid = np.floor(y_min_val / y_step) * y_step
    end_y_grid = np.ceil(y_max_val / y_step) * y_step

    current_y = start_y_grid
    while current_y <= end_y_grid:
        if y_min_val <= current_y <= y_max_val: # Only draw within bounds
            _, py = convert_custom_to_pixel(x_min_val, current_y, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
            draw.line([(0, py), (width, py)], fill=grid_color, width=1)
            draw.text((2, py + 2), f"{current_y:.2f}", fill=text_color, font=font)
        current_y += y_step

    # Draw X-axis (where Y=0)
    if y_min_val <= 0 <= y_max_val:
        _, y_axis_py = convert_custom_to_pixel(0, 0, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
        draw.line([(0, y_axis_py), (width, y_axis_py)], fill=axis_line_color, width=2)
    
    # Draw Y-axis (where X=0)
    if x_min_val <= 0 <= x_max_val:
        x_axis_px, _ = convert_custom_to_pixel(0, 0, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
        draw.line([(x_axis_px, 0), (x_axis_px, height)], fill=axis_line_color, width=2)


    # Draw a thicker border around the image
    border_color = (0, 0, 0)
    border_width = 2
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=border_color, width=border_width)

    # Draw all previously clicked points as dots
    dot_radius = 5
    for point in points_to_draw:
        px, py = convert_custom_to_pixel(point['x'], point['y'], width, height, x_min_val, x_max_val, y_min_val, y_max_val)
        # Ensure points are drawn within image bounds
        clamped_px = max(dot_radius, min(px, width - dot_radius))
        clamped_py = max(dot_radius, min(py, height - dot_radius))
        draw.ellipse(
            (clamped_px - dot_radius, clamped_py - dot_radius,
             clamped_px + dot_radius, clamped_py + dot_radius),
            fill="red", outline="darkred"
        )

    # Draw spline if enough points are present (at least 2 for a line, generally 4 for a smooth cubic spline)
    if len(points_to_draw) >= 2:
        x_coords_custom = np.array([p['x'] for p in points_to_draw])
        y_coords_custom = np.array([p['y'] for p in points_to_draw])

        try:
            current_k = min(3, len(points_to_draw) - 1)
            if current_k >= 1: # splprep requires k >= 1
                tck, u = splprep([x_coords_custom, y_coords_custom], s=0, k=current_k)
                x_new_custom, y_new_custom = splev(np.linspace(0, 1, 500), tck)
            else: # Fallback to just drawing lines between points
                x_new_custom, y_new_custom = x_coords_custom, y_coords_custom
            
            spline_points_pixel = []
            for i in range(len(x_new_custom)):
                px, py = convert_custom_to_pixel(x_new_custom[i], y_new_custom[i], width, height, x_min_val, x_max_val, y_min_val, y_max_val)
                spline_points_pixel.append((px, py))

            if len(spline_points_pixel) > 1:
                draw.line(spline_points_pixel, fill="blue", width=2)

        except Exception as e:
            # This can happen if points are collinear or too few for chosen k
            st.warning(f"Could not draw smooth spline on image (try adding more points or adjusting smoothness if plotting fails). Error: {e}")
            # Fallback to simple lines if spline fails
            if len(points_to_draw) > 1:
                line_points_pixel = []
                for p in points_to_draw:
                    px, py = convert_custom_to_pixel(p['x'], p['y'], width, height, x_min_val, x_max_val, y_min_val, y_max_val)
                    line_points_pixel.append((px,py))
                draw.line(line_points_pixel, fill="blue", width=2)


    return image

# --- Display the image and capture coordinates ---
st.subheader("Clickable Area")
st.write(f"Canvas size: {canvas_width}x{canvas_height} pixels. X-axis from **{x_min}** to **{x_max}**, Y-axis from **{y_min}** to **{y_max}**.")

current_image = create_grid_image(
    canvas_width, canvas_height,
    x_min, x_max, y_min, y_max,
    x_grid_step, y_grid_step,
    st.session_state.points
)

# Use the canvas_key_counter to force re-render/reset of the image coordinates component
value = streamlit_image_coordinates(
    current_image,
    key=f"canvas_clicks_{st.session_state.canvas_key_counter}" # Unique key
)

# --- Process and Display Coordinates ---
st.subheader("Clicked Coordinates (in Custom Units):")
if value and not st.session_state.suppress_point_add:
    clicked_custom_x, clicked_custom_y = convert_pixel_to_custom(
        value['x'], value['y'], canvas_width, canvas_height,
        x_min, x_max, y_min, y_max
    )
    
    current_click_tuple = (clicked_custom_x, clicked_custom_y)

    # Check if this click is genuinely new and hasn't been processed yet in this rerun
    # This comparison needs to be robust against floating point inaccuracies
    if st.session_state.last_click_processed != current_click_tuple:
        
        st.session_state.points.append({'x': clicked_custom_x, 'y': clicked_custom_y})
        st.session_state.last_click_processed = current_click_tuple
        add_to_history() # Add new state to history
        st.rerun() # Rerun to update the image with the new point
else:
    # Reset last_click_processed if no value (e.g., after a clear or initial load)
    if not value:
        st.session_state.last_click_processed = None
    # Also, reset suppress_point_add once a new click would potentially happen
    # This prevents buttons from being "sticky" in suppressing new points
    st.session_state.suppress_point_add = False


if st.session_state.points:
    for i, point in enumerate(st.session_state.points):
        st.write(f"Point {i+1}: X: **{point['x']:.2f}**, Y: **{point['y']:.2f}**")
else:
    st.info("Click on the canvas above to start collecting coordinates.")

# --- Undo/Redo/Clear Buttons ---
st.markdown("---")
st.subheader("Drawing Controls")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("⏪ Undo", help="Go back to the previous step."):
        st.session_state.suppress_point_add = True # Suppress point addition for this rerun
        if st.session_state.history_index > 0:
            st.session_state.history_index -= 1
            st.session_state.points = list(st.session_state.history[st.session_state.history_index])
            st.rerun()
        else:
            st.warning("No more steps to undo.")
            st.session_state.suppress_point_add = False # Allow adding points again

with col2:
    if st.button("⏩ Redo", help="Go forward to the next step."):
        st.session_state.suppress_point_add = True # Suppress point addition for this rerun
        if st.session_state.history_index < len(st.session_state.history) - 1:
            st.session_state.history_index += 1
            st.session_state.points = list(st.session_state.history[st.session_state.history_index])
            st.rerun()
        else:
            st.warning("No more steps to redo.")
            st.session_state.suppress_point_add = False # Allow adding points again

with col3:
    if st.button("🗑️ Clear All Points", help="Removes all collected points and spline."):
        st.session_state.points = []
        st.session_state.history = [[]] # Reset history with an empty state
        st.session_state.history_index = 0
        st.session_state.last_click_processed = None # Clear last processed click
        st.session_state.canvas_key_counter += 1 # Increment key to force widget reset
        st.session_state.suppress_point_add = True # Suppress point addition for this rerun
        st.rerun()


## Interpolated Airfoil Plot

st.markdown("---")
st.subheader("Interpolated Airfoil Plot")

if len(st.session_state.points) >= 4:
    x_coords_input = np.array([p['x'] for p in st.session_state.points])
    y_coords_input = np.array([p['y'] for p in st.session_state.points])

    try:
        x_interp, y_interp = interpolate_airfoil_and_close(
            x_coords_input, y_coords_input,
            num_points=num_points_interp,
            smoothness=smoothness_interp
        )
        file_name = "airfoil_coordinates.txt"
        with open(file_name, "w") as f:
            for i in range(len(x_interp)):
                f.write(f"{x_interp[i]:.6f}\t{y_interp[i]:.6f}\n") # Use tab for separation, 6 decimal places
        st.success(f"Airfoil coordinates saved to {file_name}")

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
    except Exception as e:
        st.error(f"Error generating interpolated airfoil plot: {e}. Try adjusting smoothness or adding more points.")
else:
    st.warning("Please click at least **4** points on the canvas to generate a smooth interpolated airfoil plot.")

st.markdown(
    """
    ---
    <small>Coordinates displayed are in the custom range you defined.</small>
    """,
    unsafe_allow_html=True
)
