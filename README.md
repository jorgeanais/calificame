# Cydonia (Califícame)

A Django-based web application to manage student evaluations using configurable rubrics, including both group and individual assessment criteria. Designed to be lightweight, persistent, and runnable on a Raspberry Pi using Docker.

## Features
- **Course Management:** Create courses and sections.
- **Student & Group Management:** Enroll students and organize them into groups.
- **Configurable Rubrics:** Define evaluation items, assign them as Group or Individual type, set their weights, and establish performance levels (e.g., 'MB' -> 100%).
- **Evaluations:** Grade groups and their individual members in a unified way, with detailed comments per item.
- **Docker Ready:** Includes `docker compose` configuration mapped to a persistent volume for the SQLite database.

## Environment Setup (.env)

This project uses environment variables to manage security and infrastructure settings dynamically without modifying the code base. 

1. Copy the example environment file to create your active configuration:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in the values according to your environment (Development vs. Production):

   1. Development Configuration (Local Laptop)
      ```ini
      DJANGO_SECRET_KEY=any-local-secret-key
      DJANGO_DEBUG=True
      DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
      DJANGO_TIME_ZONE=America/Santiago
      ```

   2. Production Configuration (Raspberry Pi Deployment)
      ```ini
      # Generate a secure key on your terminal using python:
      # python3 -c "import secrets; print(secrets.token_urlsafe(50))"
      DJANGO_SECRET_KEY=your-generated-secure-and-unique-key
      DJANGO_DEBUG=False
      DJANGO_ALLOWED_HOSTS=*
      DJANGO_TIME_ZONE=America/Santiago
      ```

      *Note: Always keep your .env file out of source control. It is explicitly included in .gitignore.*

## Running the Application (Docker Compose)

1. **Install Docker and Docker Compose** on your system or Raspberry Pi.

2. Clone this repository.

3. Configure your `.env` file as detailed in the section above.

4. Build and start the infrastructure in detached mode:

   ```bash
   docker compose up -d --build
   ```

5. If running in production mode (`DJANGO_DEBUG=False`), trigger the asset compilation process inside the web server container so static files can be distributed correctly:

   Bash

   ```bash
   docker compose exec web python manage.py collectstatic --noinput
   ```

6. Access the web interface at `http://<your-raspberry-ip>:8000` (or `http://localhost:8000` locally).

### First-time Setup (Admin Account)

To log into the system, initialize database structures and create your management account:

Bash

```
# Execute migrations to shape your SQLite DB tables
docker compose exec web python manage.py migrate

# Create your administrator account
docker compose exec web python manage.py createsuperuser
```

Follow the prompts, then navigate to `http://<your-raspberry-ip>:8000/admin` to log in.

## Production Maintenance & Troubleshooting Commands

### Database Backups & Restore (SQLite)

Since data is mapped to a persistent docker volume, you can safely pull or inject state copies directly:

- **Backup Database:** Copy the production DB file down to your host path:

  Bash

  ```
  docker compose cp web:/app/db_data/db.sqlite3 ./backup_db.sqlite3
  ```

- **Restore Database:** Overwrite the running state with an external backup file and restore file system security:

  Bash

  ```
  docker compose cp backup_db.sqlite3 web:/app/db_data/db.sqlite3
  docker compose exec web chmod 664 /app/db_data/db.sqlite3
  docker compose restart web
  ```

### Password Recovery

If you lose or forget an account's password, force a reset directly via the terminal interface:

```bash
docker compose exec web python manage.py changepassword <username>
```

### Docker Docker Essentials & Survival Commands

- **Inspect logs in real time:** `docker compose logs -f web`
- **Stop services safely:** `docker compose down`
- **Purge corrupted volumes or lock states:** `docker compose down -v`

## Usage Guide

1. **Log in** to the Admin Panel.
2. **Create a Course** (e.g., "Data Science 101").
3. **Add Students** and assign them to the Course.
4. **Create Groups** inside the Course and assign Students to them.
5. **Create a Rubric**.
   - Add **Rubric Levels** (e.g., MB: 100%, B: 80%).
   - Add **Rubric Items** specifying if they are GROUP or INDIVIDUAL and their weight (e.g., 0.10).
6. **Create an Evaluation** for a specific Group using the Rubric.
   - Use the inline forms to score the group items and individual items for each student.

