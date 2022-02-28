FROM python:3.9

# -- Installations -----------------------------------------------------------
COPY requirements.txt .
RUN pip install -r requirements.txt

# -- Startup ------------------------------------------------------------------
COPY . .
CMD ["python", "main.py"]