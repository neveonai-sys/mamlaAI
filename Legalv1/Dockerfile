# Use a Miniconda3 base image
FROM continuumio/miniconda3

WORKDIR /app

RUN mkdir draftdocs

# Set the working directory in the container
WORKDIR /app/Legalv1

# Copy the backend code to the container
COPY . .

# Step 3: Copy the requirements.txt into the container at /app
# COPY requirements.txt /app/requirements.txt

# COPY legalenv /app/legalenv

# Create the environment using a conda environment file (environment.yml)
COPY environment.yml /tmp/environment.yml

# Install dependencies from the environment.yml file
RUN conda env create -f /tmp/environment.yml

# Make sure the environment is activated
RUN echo "source activate myenv" > ~/.bashrc
ENV PATH /opt/conda/envs/myenv/bin:$PATH

# Install additional dependencies with pip if needed (e.g., Django, DRF)
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the app will run on
EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE=Legalv1.settings

# Run the Django development server
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
