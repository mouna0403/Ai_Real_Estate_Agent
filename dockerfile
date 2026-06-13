FROM python:3.10-slim

# ----------------------------
# Set working directory inside container
# ----------------------------
WORKDIR /app

# ----------------------------
# Install uv package manager
# ----------------------------
RUN pip install uv

# ----------------------------
# Copy dependency files first (for Docker cache optimization)
# ----------------------------
COPY pyproject.toml uv.lock ./

# ----------------------------
# Install dependencies using uv
# ----------------------------
RUN uv pip install --system -r pyproject.toml

# ----------------------------
# Copy application source code
# ----------------------------
COPY src ./src


ENV PYTHONPATH=/app/src
# ----------------------------
# Expose Streamlit default port
# ----------------------------
ENV PORT=8080
# ----------------------------
# Run Streamlit application
# ----------------------------
#CMD ["streamlit", "run", "src/Ai_Real_Estate_Agent/main.py", "--server.port=8501", "--server.address=0.0.0.0"]



CMD ["uvicorn", "Ai_Real_Estate_Agent.main:app", "--host", "0.0.0.0", "--port", "8080"]