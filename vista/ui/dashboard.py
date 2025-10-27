from flask import Flask, render_template_string
import sqlite3

app = Flask(__name__)

DB_PATH = "vista_memory.db"

def get_projects():
    with sqlite3.connect(DB_PATH) as conn:
        projects = conn.execute("SELECT DISTINCT project_id FROM artifacts ORDER BY project_id").fetchall()
        return [p[0] for p in projects]

def get_artifacts(project_id):
    with sqlite3.connect(DB_PATH) as conn:
        artifacts = conn.execute("SELECT kind, artifact_id, created_at FROM artifacts WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
        return artifacts

@app.route("/")
def index():
    projects = get_projects()
    project_data = []
    for project in projects:
        artifacts = get_artifacts(project)
        project_data.append({"id": project, "artifacts": artifacts})

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VISTA V-Loop Dashboard</title>
        <style>
            body { font-family: sans-serif; }
            h1, h2 { color: #333; }
            .project { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
            .artifact { margin-left: 20px; }
        </style>
    </head>
    <body>
        <h1>VISTA V-Loop Dashboard</h1>
        {% for project in project_data %}
            <div class="project">
                <h2>Project: {{ project.id }}</h2>
                {% for artifact in project.artifacts %}
                    <div class="artifact">
                        <p><b>{{ artifact[0] }}</b> ({{ artifact[1] }})</p>
                    </div>
                {% endfor %}
            </div>
        {% endfor %}
    </body>
    </html>
    """
    return render_template_string(template, project_data=project_data)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
