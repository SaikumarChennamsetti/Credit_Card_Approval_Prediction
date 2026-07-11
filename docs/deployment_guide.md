# Deployment Guide

This guide provides instructions for deploying and running the Credit Card Approval Prediction System locally, inside Docker containers, and on production cloud servers.

---

## 1. Local Machine Setup

### Prerequisites
* **Python**: Python 3.13 (recommended) or 3.11+
* **Git**: To clone the repository files.

### Step-by-Step Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/Credit-Card-Approval-System.git
   cd Credit-Card-Approval-System
   ```

2. **Create a Virtual Environment**:
   * **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependency Libraries**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a file named `.env` in the root of the project:
   ```env
   FLASK_ENV=development
   DATABASE_URL=sqlite:///db/database.db
   RANDOM_SEED=42
   TEST_SIZE=0.2
   LOG_LEVEL=INFO
   ```

5. **Train the ML Models**:
   Run the training script to generate candidate model binaries and preprocessors:
   ```bash
   python ml_pipeline/train.py
   ```

6. **Run Model Evaluation & Selection**:
   Select the champion model and generate performance charts:
   ```bash
   python ml_pipeline/evaluate.py
   ```

7. **Start the Flask Server**:
   ```bash
   python run.py
   ```
   Open `http://127.0.0.1:5000` in your web browser.

---

## 2. Docker & Containerized Setup

Using Docker ensures the application behaves identically on developers' machines, staging environments, and production clusters.

### Prerequisites
* **Docker Desktop** installed and running on your system.

### Build and Run with Docker
1. **Build the Docker Image**:
   ```bash
   docker build -t credit-card-app -f deploy/Dockerfile .
   ```

2. **Run the Container**:
   ```bash
   docker run -d -p 5000:5000 --name credit-card-container credit-card-app
   ```

### Deploying with Docker Compose (Recommended)
Docker Compose maps database folders, logs files, and configures environment variables automatically.

1. **Start Services**:
   ```bash
   docker compose -f deploy/docker-compose.yml up -d --build
   ```

2. **Monitor Server Logs**:
   ```bash
   docker compose -f deploy/docker-compose.yml logs -f
   ```

3. **Stop Services**:
   ```bash
   docker compose -f deploy/docker-compose.yml down
   ```

---

## 3. Production Deployment Guide

### Option A: Virtual Machines (AWS EC2, Google Compute Engine, DigitalOcean Droplet)
1. **Provision VM**: Launch a Linux instance (e.g. Ubuntu 22.04 LTS).
2. **Install Docker**: Install Docker and Docker Compose on the machine.
3. **Copy Code**: Clone the repository or copy project files to `/opt/credit-card-approval/`.
4. **Environment Setup**: Add production `.env` variables (e.g. `FLASK_ENV=production`, `SECRET_KEY=secure_long_random_string`).
5. **Run Compose**: Launch the services with Docker Compose in detached mode.
6. **Set up Reverse Proxy (Nginx)**: Configure Nginx as a reverse proxy to receive traffic on port 80/443 and forward requests to the app on port 5000:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```
7. **Install SSL (Certbot)**: Use Certbot to configure Let's Encrypt SSL certificates for HTTPS connection encryption.

### Option B: Managed Container Platforms (AWS ECS, Google Cloud Run)
Since the app is Dockerized, it can be deployed to serverless container runners:
1. **Push Image to Registry**: Push the Docker image to Amazon ECR or Google Artifact Registry.
2. **Launch Task/Service**: Define a task or service specifying environment variables (`DATABASE_URL`, `SECRET_KEY`) and expose port 5000.
3. **Persist Storage**: Mount an EFS volume (for AWS) or Cloud Storage (for GCP) if using SQLite, or link to a managed database instance (RDS PostgreSQL / Cloud SQL).

---

## 4. Troubleshooting & Solutions

### 1. Error: `Address already in use` (Port 5000)
* **Cause**: Another process or background server is running on port 5000.
* **Solution**: Change the port in `docker-compose.yml` or stop the running server.
  * *Windows*: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess -Force`
  * *Linux/macOS*: `kill -9 $(lsof -t -i:5000)`

### 2. Error: `Model assets not loaded in memory`
* **Cause**: The server started but the model joblib weights files under `models/` are missing.
* **Solution**: Ensure you run model training (`python ml_pipeline/train.py`) and evaluation (`python ml_pipeline/evaluate.py`) before starting the server.

### 3. Warning: `Database tables missing`
* **Cause**: Database tables have not initialized.
* **Solution**: The Flask app automatically compiles tables on startup via `db.create_all()` inside `app.py`. If tables fail to generate, verify write permissions on the `db/` folder.
