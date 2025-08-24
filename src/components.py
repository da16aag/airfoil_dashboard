from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy.interpolate import splprep, splev
import streamlit as st

def create_grid_image(width, height, x_min_val, x_max_val, y_min_val, y_max_val, x_step, y_step, points_to_draw, convert_func):
    """
    Function to create the image with grid, border, clicked points, and spline.

    Args:
        width (int): Width of the image.
        height (int): Height of the image.
        x_min_val (float): Minimum custom X-coordinate.
        x_max_val (float): Maximum custom X-coordinate.
        y_min_val (float): Minimum custom Y-coordinate.
        y_max_val (float): Maximum custom Y-coordinate.
        x_step (float): Step size for X-grid lines.
        y_step (float): Step size for Y-grid lines.
        points_to_draw (list): List of dictionaries, each with 'x' and 'y' custom coordinates.
        convert_func (function): The function to convert custom coordinates to pixel coordinates.

    Returns:
        PIL.Image.Image: The generated image.
    """
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
    start_x_grid = np.floor(x_min_val / x_step) * x_step
    end_x_grid = np.ceil(x_max_val / x_step) * x_step

    current_x = start_x_grid
    while current_x <= end_x_grid:
        if x_min_val <= current_x <= x_max_val:
            px, _ = convert_func(current_x, y_min_val, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
            draw.line([(px, 0), (px, height)], fill=grid_color, width=1)
            draw.text((px + 2, 2), f"{current_x:.2f}", fill=text_color, font=font)
        current_x += x_step

    # Draw horizontal grid lines and Y-axis labels
    start_y_grid = np.floor(y_min_val / y_step) * y_step
    end_y_grid = np.ceil(y_max_val / y_step) * y_step

    current_y = start_y_grid
    while current_y <= end_y_grid:
        if y_min_val <= current_y <= y_max_val:
            _, py = convert_func(x_min_val, current_y, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
            draw.line([(0, py), (width, py)], fill=grid_color, width=1)
            draw.text((2, py + 2), f"{current_y:.2f}", fill=text_color, font=font)
        current_y += y_step

    # Draw X-axis (where Y=0)
    if y_min_val <= 0 <= y_max_val:
        _, y_axis_py = convert_func(0, 0, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
        draw.line([(0, y_axis_py), (width, y_axis_py)], fill=axis_line_color, width=2)

    # Draw Y-axis (where X=0)
    if x_min_val <= 0 <= x_max_val:
        x_axis_px, _ = convert_func(0, 0, width, height, x_min_val, x_max_val, y_min_val, y_max_val)
        draw.line([(x_axis_px, 0), (x_axis_px, height)], fill=axis_line_color, width=2)

    # Draw a thicker border around the image
    border_color = (0, 0, 0)
    border_width = 2
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=border_color, width=border_width)

    # Draw all previously clicked points as dots
    dot_radius = 5
    for point in points_to_draw:
        px, py = convert_func(point['x'], point['y'], width, height, x_min_val, x_max_val, y_min_val, y_max_val)
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
                px, py = convert_func(x_new_custom[i], y_new_custom[i], width, height, x_min_val, x_max_val, y_min_val, y_max_val)
                spline_points_pixel.append((px, py))

            if len(spline_points_pixel) > 1:
                draw.line(spline_points_pixel, fill="blue", width=2)

        except Exception as e:
            st.warning(f"Could not draw smooth spline on image (try adding more points or adjusting smoothness if plotting fails). Error: {e}")
            # Fallback to simple lines if spline fails
            if len(points_to_draw) > 1:
                line_points_pixel = []
                for p in points_to_draw:
                    px, py = convert_func(p['x'], p['y'], width, height, x_min_val, x_max_val, y_min_val, y_max_val)
                    line_points_pixel.append((px,py))
                draw.line(line_points_pixel, fill="blue", width=2)

    return image
