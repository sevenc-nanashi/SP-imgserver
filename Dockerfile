FROM python:3.9

# -- Installations -----------------------------------------------------------
COPY requirements.txt .
RUN pip install -r requirements.txt

# -- Startup ------------------------------------------------------------------
COPY . .
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app"]
