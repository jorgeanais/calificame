# Cydonia (Califícame)

A Django-based web application to manage student evaluations using configurable rubrics, including both group and individual assessment criteria. Designed to be lightweight, persistent, and runnable on a Raspberry Pi using Docker.

## Features
- **Course Management:** Create courses and sections.
- **Student & Group Management:** Enroll students and organize them into groups.
- **Configurable Rubrics:** Define evaluation items, assign them as Group or Individual type, set their weights, and establish performance levels (e.g., 'MB' -> 100%).
- **Evaluations:** Grade groups and their individual members in a unified way, with detailed comments per item.
- **Docker Ready:** Includes `docker-compose.yml` mapped to a persistent volume for the SQLite database.

## Running Locally / Raspberry Pi (Docker)

1. **Install Docker and Docker Compose** on your system/Raspberry Pi.
2. Clone this repository.
3. Run the following command to build and start the application in detached mode:
   ```bash
   docker-compose up -d
   ```
4. Access the web interface at `http://<your-ip>:8000`.

### First-time Setup (Admin User)
To manage courses and grades, you will use the Django Admin interface. 
Create an administrator account by running:
```bash
docker-compose exec web python manage.py createsuperuser
```
Follow the prompts, then navigate to `http://<your-ip>:8000/admin` to log in.

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

All data is stored in the `db_data` volume map, meaning it will persist even if the Raspberry Pi is restarted or the container is rebuilt.
