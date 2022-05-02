FROM python:3.9

# -- Installations -----------------------------------------------------------
COPY requirements.txt .
RUN pip install -r requirements.txt

# -- Startup ------------------------------------------------------------------
COPY . .
EXPOSE 80
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:80", "main:app"]
