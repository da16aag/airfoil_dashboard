import streamlit as st

def initialize_session_state():
    """Initializes all necessary session state variables."""
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
    if 'suppress_point_add' not in st.session_state:
        st.session_state.suppress_point_add = False
    if 'file_saved' not in st.session_state:
        st.session_state.file_saved = False # Flag to indicate if file was just saved


    if 'stl_generated' not in st.session_state:
        st.session_state.stl_generated = False
    if 'stl_thickness' not in st.session_state: # This will be unused in the UI but remains in session state
        st.session_state.stl_thickness = 0.1
    if 'interpolated_coords' not in st.session_state:
        st.session_state.interpolated_coords = None

    if 'meshing' not in st.session_state:
        st.session_state.meshing = False
    if 'running' not in st.session_state:
        st.session_state.running = False

def add_to_history():
    """Adds the current state of points to the history."""
    if st.session_state.suppress_point_add:
        return

    if st.session_state.history_index < len(st.session_state.history) - 1:
        st.session_state.history = st.session_state.history[:st.session_state.history_index + 1]

    current_points_copy = list(st.session_state.points)
    if not st.session_state.history or current_points_copy != st.session_state.history[-1]:
        st.session_state.history.append(current_points_copy)
        st.session_state.history_index = len(st.session_state.history) - 1

def undo_action():
    """Performs an undo operation, reverting to a previous state."""
    st.session_state.file_saved = False
    st.session_state.suppress_point_add = False
    st.session_state.last_click_processed = None
    st.session_state.canvas_key_counter += 1
    st.session_state.stl_generated = False
    st.session_state.meshing = False
    st.session_state.running = False
    if st.session_state.history_index > 0:
        st.session_state.history_index -= 1
        st.session_state.points = list(st.session_state.history[st.session_state.history_index])
    else:
        st.warning("No more steps to undo.")

def redo_action():
    """Performs a redo operation, moving to a future state."""
    st.session_state.file_saved = False
    st.session_state.suppress_point_add = False
    st.session_state.last_click_processed = None
    st.session_state.canvas_key_counter += 1
    st.session_state.stl_generated = False
    st.session_state.meshing = False
    st.session_state.running = False
    if st.session_state.history_index < len(st.session_state.history) - 1:
        st.session_state.history_index += 1
        st.session_state.points = list(st.session_state.history[st.session_state.history_index])
    else:
        st.warning("No more steps to redo.")

def clear_all_points():
    """Clears all points and resets the history."""

    st.session_state.file_saved = False
    st.session_state.suppress_point_add = False
    st.session_state.last_click_processed = None
    st.session_state.points = []
    st.session_state.history = [[]]
    st.session_state.history_index = 0
    st.session_state.canvas_key_counter += 1
    st.session_state.stl_generated = False
    st.session_state.meshing = False
    st.session_state.running = False

