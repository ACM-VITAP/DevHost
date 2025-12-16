<h1 align="center">DevHost 🚀</h1>

<p align="center">
A full-stack web platform to host, manage, and evaluate hackathons with ease.
</p>

<hr>

<h2>📌 Overview</h2>
<p>
This platform is designed to streamline hackathon management by providing a clean
admin interface for event and problem creation, and an intuitive participant interface
for viewing problems, submitting solutions, and tracking rankings.
</p>

<hr>

<h2>✨ Features</h2>

<h3>👨‍💼 Admin Features</h3>
<ul>
    <li>Create and manage hackathon events</li>
    <li>Add, edit, and delete problem statements</li>
    <li>Enforce submission constraints (file size limits)</li>
    <li>Evaluate submissions with marks and remarks</li>
    <li>Generate rankings automatically</li>
</ul>

<h3>👩‍💻 Participant Features</h3>
<ul>
    <li>Secure registration and login</li>
    <li>Browse active hackathon events</li>
    <li>View problem statements in a tabular format</li>
    <li>Submit solutions online</li>
    <li>View scores and leaderboard rankings</li>
    <li>Update personal profile information</li>
</ul>

<hr>

<h2>🛠️ Tech Stack</h2>

<ul>
    <li><strong>Frontend:</strong> HTML5, CSS3, Jinja2</li>
    <li><strong>Backend:</strong> Python (Flask), Werkzeug</li>
    <li><strong>Database:</strong> MongoDB (MongoDB Atlas)</li>
    <li><strong>Deployment:</strong> Render, Gunicorn</li>
</ul>

<hr>

<h2>📂 Project Structure</h2>

<pre>
├── app.py
├── requirements.txt
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── home.html
│   ├── events.html
│   ├── problems.html
│   ├── admin.html
│   ├── admin_problems.html
│   ├── evaluation.html
│   ├── profile.html
│   └── rankings.html
├── static/
│   ├── home.css
│   ├── events.css
│   ├── problems.css
│   ├── profile.css
│   └── admin.css
├── uploads/
└── README.md
</pre>

<hr>

<h2>⚙️ Setup Instructions</h2>

<h3>1️⃣ Clone the Repository</h3>
<pre>
git clone https://github.com/your-username/hackathon-platform.git
cd hackathon-platform
</pre>

<h3>2️⃣ Create Virtual Environment</h3>
<pre>
python -m venv venv
venv\Scripts\activate   (Windows)
source venv/bin/activate (macOS/Linux)
</pre>

<h3>3️⃣ Install Dependencies</h3>
<pre>
pip install -r requirements.txt
</pre>

<h3>4️⃣ Configure MongoDB</h3>
<p>
Update the <code>MONGO_URI</code> in <code>app.py</code> with your MongoDB Atlas connection string.
</p>

<h3>5️⃣ Run the Application</h3>
<pre>
python app.py
</pre>

<hr>

<h2>🚀 Deployment (Render)</h2>
<ul>
    <li>Create a new <strong>Web Service</strong> on Render</li>
    <li>Build Command:
        <pre>pip install -r requirements.txt</pre>
    </li>
    <li>Start Command:
        <pre>gunicorn app:app</pre>
    </li>
    <li>Service name determines the deployment URL</li>
</ul>

<hr>

<h2>📊 Ranking System</h2>
<p>
Each submission is evaluated by the admin. Scores are aggregated per participant,
and rankings are generated automatically based on total marks using MongoDB aggregation.
</p>

<hr>

<h2>🔒 Security</h2>
<ul>
    <li>Passwords are securely hashed</li>
    <li>Role-based access control (Admin / Participant)</li>
    <li>Protected routes using Flask decorators</li>
</ul>

<hr>

<h2>⚠️ Important Notes</h2>
<ul>
    <li>Uploaded files stored locally are temporary on Render</li>
    <li>MongoDB data is persistent and safe</li>
    <li>Sessions reset on server restart</li>
</ul>

<hr>

<h2>📌 Future Enhancements</h2>
<ul>
    <li>Cloud-based file storage</li>
    <li>Submission deadline enforcement</li>
    <li>Event-wise leaderboards</li>
    <li>Search and filter functionality</li>
    <li>Email notifications</li>
</ul>

<hr>

<h2>👤 Author</h2>
<p>
<strong>Charan</strong><br>
Student | Full-Stack Developer
</p>

<hr>

<p align="center">
Built with passion for hackathons and full-stack development 💻🔥
</p>
