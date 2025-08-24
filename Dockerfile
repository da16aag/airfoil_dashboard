# Start from Ubuntu with OpenFOAM already installed
FROM 3x3cut0r/streamlit:1.45.1 AS streamlit_builder

FROM dicehub/openfoam:12

USER root

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev \
    paraview \
    xvfb \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*


COPY --from=streamlit_builder /venv/lib/python3.11/site-packages/ /venv/lib/python3.11/site-packages/

# Set work directory inside container
WORKDIR /Airfoil_App

# Copy only dependency files first (better caching for rebuilds)
COPY requirements_dev.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements_dev.txt
RUN pip install --no-cache-dir imageio[ffmpeg]
# Copy the rest of the code
COPY . .

# Switch to your source directory
WORKDIR /Airfoil_App/src

# Expose Streamlit default port
EXPOSE 8501

# Configure Streamlit for Docker
RUN mkdir -p ~/.streamlit
RUN echo "\
[server]\n\
headless = true\n\
enableCORS = false\n\
port = 8501\n\
" > ~/.streamlit/config.toml


ENTRYPOINT ["/bin/bash", "-c", "source /home/openfoam/OpenFOAM-12/etc/bashrc && exec bash"]

# Comment out or remove these lines to prevent Streamlit from starting automatically
# ENTRYPOINT ["streamlit", "run", "streamlit_interface.py"]
# CMD ["--server.port=8501", "--server.address=0.0.0.0"]
