import os

# Create templates directory if not exists
os.makedirs('evaluations/templates/evaluations', exist_ok=True)

with open('evaluations/templates/evaluations/base.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GradeMaster</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">GradeMaster</a>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/admin">Admin Panel</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''')

with open('evaluations/templates/evaluations/index.html', 'w') as f:
    f.write('''{% extends "evaluations/base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-12 text-center">
        <h1 class="display-4">Welcome to GradeMaster</h1>
        <p class="lead">Manage your courses, students, and rubric evaluations.</p>
        <hr class="my-4">
        <p>Use the Admin Panel to configure your rubrics and manage grades.</p>
        <a class="btn btn-primary btn-lg" href="/admin" role="button">Go to Admin Panel</a>
    </div>
</div>
{% endblock %}''')

print("Templates created.")
