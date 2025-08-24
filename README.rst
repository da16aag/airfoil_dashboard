# 2D Airfoil CFD Simulator

A web-based application for designing 2D airfoil shapes and running **CFD simulations** using **OpenFOAM**. The app allows users to create airfoil shapes interactively, generate meshes, and visualize the resulting **pressure contours** and **velocity vectors**.

---

## Features

- Interactive airfoil design on an XY grid using mouse clicks.
- Automatic interpolation of points using **B-splines**.
- Mesh generation using **trimesh** and conversion to **STL** format.
- 2D incompressible fluid simulation using **OpenFOAM**.
- Visualization of:
  - Pressure contours
  - Velocity vectors
- Adjustable CFD parameters:
  - Fluid velocity
  - Mesh resolution
  - Simulation controls
- Validation against known airfoils and simple shapes (e.g., circle).
- History management and reruns via Streamlit interface.

---

## Installation

The app runs inside a **Docker container** for easy setup and reproducibility.

### Build Docker Image

```bash
docker build -t myairfoil_app:latest .
```

### Run Docker Container

```bash
docker run -p 8501:8501 --rm -it myairfoil_app:latest /bin/bash
```

### Launch the Streamlit App

Inside the container:

```bash
streamlit run streamlit_interface.py
```

The app will be available at: `http://localhost:8501`

---

## Usage

1. Open the app in your browser.
2. Click on the XY grid to design your airfoil.
3. Adjust CFD parameters as needed.
4. Generate mesh and run simulation.
5. View pressure and velocity visualizations.
6. Save or reload previous airfoil designs using the history manager.

---

## Validation

The app has been validated against:

- Standard airfoils
- Circle shapes

Simulation results show consistent **pressure** and **velocity** patterns.

---

## Dependencies

- Python 3.x  
- [Streamlit](https://streamlit.io/)  
- [OpenFOAM](https://www.openfoam.com/)  
- [trimesh](https://trimsh.org/)  
- Docker (for containerized runs)  

All other required Python packages are listed in `requirements.txt`.

---

## Notes

- Coordinates are always stored in `airfoil_coordinates.txt`.
- `old_airfoil_to_stl.py` handles conversion of coordinate points to STL format.
- `utils_old.py` contains the main calculation functions.
- CFD parameters can be adjusted via files in `cfd/Mesh` and `cfd/Run`.
- `cfd_runner.py` manages the OpenFOAM simulation.
- `components.py` contains the Streamlit UI components.
- `history_manager.py` handles reruns and session history in Streamlit.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.
