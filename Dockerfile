FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# gettext trae msgfmt, necesario para compilar los .po -> .mo
RUN apt-get update && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias primero (cachea mejor la capa de Docker)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . /app/

# Compilar los mensajes de traducción (los .po SI se versionan, los .mo NO)
# DJANGO_SECRET_KEY no existe en build-time (viene del .env en runtime),
# pero settings.py la exige para poder cargar. Usamos un valor dummy
# solo para este paso; no se usa realmente en compilemessages.
RUN DJANGO_SECRET_KEY=dummy-solo-para-build python manage.py compilemessages

# Usuario no-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Ajustado para el hardware limitado de una Raspberry Pi.
# Si tu Pi tiene 4+ cores y 4GB+ RAM puedes subir workers a 3.
CMD ["gunicorn", "cydonia.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "2", \
     "--timeout", "60"]
