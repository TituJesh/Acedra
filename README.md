<div align="center">

  <h1 align="center">🎓 Acedra</h1>

  <p align="center">
    <strong>Production-ready, cloud-native Student Information & Cloud Document Management System.</strong>
  </p>

  <p align="center">
    Built with Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy 2.0, Alembic, AWS S3, and AWS Secrets Manager.
  </p>

  <p align="center">
    <a href="https://github.com/TituJesh/Acedra/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT" />
    </a>
    <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white&style=flat-square" alt="FastAPI" />
    <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white&style=flat-square" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white&style=flat-square" alt="SQLAlchemy" />
    <img src="https://img.shields.io/badge/Alembic-Migrations-8A2BE2?style=flat-square" alt="Alembic" />
    <img src="https://img.shields.io/badge/AWS%20S3-Document%20Vault-569A31?logo=amazons3&logoColor=white&style=flat-square" alt="AWS S3" />
    <img src="https://img.shields.io/badge/AWS-Secrets%20Manager-FF9900?logo=amazonwebservices&logoColor=white&style=flat-square" alt="AWS Secrets Manager" />
    <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white&style=flat-square" alt="Docker Ready" />
    <img src="https://img.shields.io/badge/API%20Docs-Swagger-85EA2D?logo=swagger&logoColor=black&style=flat-square" alt="Swagger" />
  </p>

</div>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Core Resource Modules](#core-resource-modules)
- [System Architecture](#system-architecture)
- [Database Schema (ERD)](#database-schema-erd)
- [Quickstart & Local Development](#quickstart--local-development)
  - [Prerequisites](#prerequisites)
  - [Manual Setup (Local venv)](#manual-setup-local-venv)
- [Environment Variables](#environment-variables)
- [Database Migrations (Alembic)](#database-migrations-alembic)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [API Walkthrough & cURL Examples](#api-walkthrough--curl-examples)
- [AWS Cloud Infrastructure](#aws-cloud-infrastructure)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Security](#security)
- [Production Cloud Deployment](#production-cloud-deployment)
- [Support](#support)
- [License & Author](#license--author)

---

## Overview

**Acedra** is an enterprise-grade Student Information & Cloud Document Management RESTful API backend engineered for academic institutions, universities, and departmental faculties.

The application is structured into modular, decoupled layers: a **FastAPI** asynchronous REST gateway with dependency-injected OAuth2 and RBAC authorization, **SQLAlchemy 2.0** ORM for relational persistence on **PostgreSQL 16**, **Alembic** for automated migration tracking, **Amazon S3** for secure multi-tenant document storage with short-lived presigned URLs, and **AWS Secrets Manager** for dynamic zero-trust cryptographic key management.

---

## Key Features

### REST API Surface
- Clean RESTful endpoints organized across 4 domain modules (**Auth**, **Students**, **Departments**, **Documents**).
- Automated OpenAPI 3.0 interactive documentation via **Swagger UI** (`/docs`) and **ReDoc** (`/redoc`).
- Strict schema validation and auto-generated data contracts powered by **Pydantic v2**.

### Authentication & RBAC
- Stateless **JWT (JSON Web Token)** authentication over standard OAuth2 Password Request flow (`/auth/login`).
- Cryptographic password hashing using **Bcrypt** with dynamic salting via Passlib.
- Hierarchical Role-Based Access Control enforcing strict separation between `admin` and `student` roles.
- Self-service profile resolution (`/auth/me` and `/students/me`).

### Cloud Document Vault & S3
- Secure multi-tenant file ingestion streaming directly to private **Amazon S3** buckets.
- Collision-proof file partitioning using UUIDv4 key paths (`students/{student_id}/{uuid4}_{filename}`).
- Time-limited (300 seconds) HMAC-SHA256 **presigned download URLs**, preventing direct public bucket exposure.
- Cascading deletion: deleting a document removes both S3 cloud objects and relational metadata.

### Cloud-Native Secrets Management
- Zero hardcoded production credentials.
- Dual-mode configuration engine: automatically reads local configuration in development (`ENVIRONMENT=local`) and dynamically retrieves signing secrets from **AWS Secrets Manager** (`acedra/jwt`) in production (`ENVIRONMENT=production`).

### Relational Integrity & Migrations
- Robust ACID compliance backed by **PostgreSQL 16**.
- Relational mapping with foreign key cascades and one-to-one / one-to-many relationship declarations.
- Fully reversible, version-controlled database schema migrations managed by **Alembic**.

### Observability & Audit Logging
- Structured logging pipeline tracking high-value audit events: user registrations, failed/successful logins, student profile creations, and S3 document uploads/deletions.

---

## Tech Stack

- **Backend Framework**: Python 3.12, FastAPI, Pydantic v2, Starlette
- **ASGI Web Server**: Uvicorn (worker clustering with Gunicorn for production)
- **Database & Driver**: PostgreSQL 16, Psycopg 3 (`psycopg[binary]`)
- **ORM & Migrations**: SQLAlchemy 2.0, Alembic
- **Cloud Storage & Security**: AWS S3 (`boto3`), AWS Secrets Manager
- **Authentication & Cryptography**: Python-Jose (JWT HS256), Passlib, Bcrypt, OAuth2 Password Bearer
- **DevOps & Containerization**: Docker, Docker Compose

---

## Core Resource Modules

| Module | Base Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| **Auth** | `/auth` | User registration, OAuth2 credential exchange, self identity inspection (`/me`), and admin validation | Public / Authenticated |
| **Students** | `/students` | Student profile creation, directory listing, profile updates, fuzzy search (`/search`), and self profile | Authenticated (Admin for write) |
| **Departments** | `/departments`| Academic department creation, code validation, directory lookup, and department updates | Authenticated (Admin for write) |
| **Documents** | `/documents` | S3 document upload, student file listing, presigned download link generation, and file deletion | Authenticated (Admin for upload/delete) |
| **Observability** | `/`, `/docs`, `/redoc` | Base healthcheck endpoint, interactive Swagger UI, and OpenAPI schema documentation | Public |

---

## System Architecture

```mermaid
flowchart TD
    subgraph Clients["Clients & Consumers"]
        AdminApp["Admin Dashboard / Portal"]
        StudentApp["Student Portal / Mobile"]
    end

    subgraph Gateway["Acedra API Gateway (FastAPI)"]
        AuthRouter["/auth\nAuthentication Router"]
        StudentRouter["/students\nStudent Management"]
        DeptRouter["/departments\nDepartment Registry"]
        DocRouter["/documents\nDocument Vault"]
        
        SecurityLayer["OAuth2 Bearer & RBAC Layer\n(require_admin / get_current_user)"]
        
        AuthRouter --> SecurityLayer
        StudentRouter --> SecurityLayer
        DeptRouter --> SecurityLayer
        DocRouter --> SecurityLayer
    end

    subgraph CloudServices["AWS Cloud Services"]
        SecretsManager["AWS Secrets Manager\n(Secret: acedra/jwt)"]
        S3Bucket["AWS S3 Bucket\n(students/{id}/{uuid}_{file})"]
    end

    subgraph Storage["Database Layer"]
        Postgres[(PostgreSQL 16 Engine)]
        AlembicEngine["Alembic Migrations"]
    end

    Clients -->|Bearer Token / HTTPS| Gateway
    SecurityLayer -.->|Fetch Secret in Prod| SecretsManager
    DocRouter -->|Stream Upload & Presign URL| S3Bucket
    Gateway -->|SQLAlchemy 2.0 ORM| Postgres
    AlembicEngine -->|Schema Revisions| Postgres
```

---

## Database Schema (ERD)

```mermaid
erDiagram
    USERS ||--o| STUDENTS : "1:1 owns profile"
    DEPARTMENTS ||--o{ STUDENTS : "1:N enrolls"
    STUDENTS ||--o{ DOCUMENTS : "1:N uploads"

    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string role "admin | student"
        datetime created_at
    }

    DEPARTMENTS {
        int id PK
        string name UK
        string code UK
    }

    STUDENTS {
        int id PK
        int user_id FK, UK
        string student_id UK
        string first_name
        string last_name
        string email UK
        string phone
        date date_of_birth
        string gender
        int department_id FK
        int year
        string address
    }

    DOCUMENTS {
        int id PK
        int student_id FK
        string file_name
        string file_type
        string s3_key
        datetime uploaded_at
    }
```

---

## Quickstart & Local Development

### Prerequisites

- **Python**: Version `3.11` or `3.12`
- **PostgreSQL**: Version `15+` or `16+` (local service or Docker container)
- **AWS Account & CLI**: Required for S3 uploads and production Secrets Manager (configured with `aws configure`)

---

### Manual Setup (Local venv)

#### 1. Clone the repository
```bash
git clone https://github.com/TituJesh/Acedra.git
cd Acedra
```

#### 2. Create and activate a virtual environment
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` to match your local PostgreSQL database and AWS credentials:
```ini
ENVIRONMENT=local
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/acedra
SECRET_KEY=your-32-byte-hex-secret-key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-s3-bucket-name
```

#### 5. Initialize the database & run migrations
Ensure your PostgreSQL server has the `acedra` database created (`CREATE DATABASE acedra;`), then run:
```bash
alembic upgrade head
```

#### 6. Start the development server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
The API is now running at **http://127.0.0.1:8000** (Swagger UI at **http://127.0.0.1:8000/docs**).

---

## Environment Variables

| Variable | Type | Required | Default | Description |
| :--- | :---: | :---: | :--- | :--- |
| `ENVIRONMENT` | `string` | **Yes** | `local` | Set to `local` for local key resolution or `production` for AWS Secrets Manager. |
| `DATABASE_URL` | `string` | **Yes** | — | PostgreSQL connection URI (`postgresql+psycopg://<user>:<password>@<host>:<port>/<db>`). |
| `SECRET_KEY` | `string` | **Yes** (local) | — | HMAC-SHA256 signing key used when `ENVIRONMENT=local`. |
| `AWS_REGION` | `string` | No | `ap-south-1` | AWS region hosting S3 buckets and Secrets Manager. |
| `S3_BUCKET_NAME` | `string` | **Yes** (docs) | — | Amazon S3 bucket name for student files. |

---

## Database Migrations (Alembic)

Acedra tracks all database changes using Alembic:

```bash
# Apply all pending migrations to the latest revision
alembic upgrade head

# Revert the most recent migration
alembic downgrade -1

# Generate a new migration after updating models in app/models/
alembic revision --autogenerate -m "add new column or table"

# View current migration version
alembic current
```

---

## Role-Based Access Control (RBAC)

Access is strictly controlled by role-based dependency injection:

| Route | Method | Public | Student Role | Admin Role | Action |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `/auth/register` | `POST` | ✅ | ✅ | ✅ | Register user account (`admin` or `student`) |
| `/auth/login` | `POST` | ✅ | ✅ | ✅ | Generate Bearer token |
| `/auth/me` | `GET` | ❌ | ✅ | ✅ | Retrieve current user profile |
| `/auth/admin-test` | `GET` | ❌ | ❌ | ✅ | Admin route verification |
| `/departments/` | `GET` | ❌ | ✅ | ✅ | Browse departments |
| `/departments/` | `POST` | ❌ | ❌ | ✅ | Create department |
| `/students/` | `GET` | ❌ | ✅ | ✅ | Browse all student profiles |
| `/students/` | `POST` | ❌ | ❌ | ✅ | Register new student record |
| `/students/me` | `GET` | ❌ | ✅ | ✅ | Fetch caller's student record |
| `/students/search` | `GET` | ❌ | ✅ | ✅ | Search students by ID, Name, or Email |
| `/students/{id}` | `PUT`/`DEL` | ❌ | ❌ | ✅ | Modify or delete student record |
| `/documents/upload/{id}` | `POST` | ❌ | ❌ | ✅ | Upload document to S3 |
| `/documents/student/{id}`| `GET` | ❌ | ✅ | ✅ | List documents for student |
| `/documents/{id}/download`| `GET` | ❌ | ✅ | ✅ | Generate 300s presigned download URL |
| `/documents/{id}` | `DELETE`| ❌ | ❌ | ✅ | Delete document from S3 and DB |

---

## API Walkthrough & cURL Examples

### 1. Register an Administrator
```bash
curl -X POST "http://127.0.0.1:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "admin_titu",
       "email": "admin@acedra.edu",
       "password": "SuperSecretPassword123!",
       "role": "admin"
     }'
```

### 2. Login to Obtain Bearer Token
```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin_titu&password=SuperSecretPassword123!"
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Create Department
```bash
curl -X POST "http://127.0.0.1:8000/departments/" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"name": "Computer Science", "code": "CS"}'
```

### 4. Create Student Record
```bash
curl -X POST "http://127.0.0.1:8000/students/" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 1,
       "student_id": "STU2026001",
       "first_name": "Titu",
       "last_name": "Jesh",
       "email": "titu@acedra.edu",
       "phone": "+919876543210",
       "date_of_birth": "2002-08-15",
       "gender": "Male",
       "department_id": 1,
       "year": 4,
       "address": "Bangalore, India"
     }'
```

### 5. Upload Student Document to S3
```bash
curl -X POST "http://127.0.0.1:8000/documents/upload/1" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     -F "file=@sample_transcript.pdf;type=application/pdf"
```

### 6. Get Presigned S3 Download URL (Valid for 300 seconds)
```bash
curl -X GET "http://127.0.0.1:8000/documents/1/download" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```
**Response:**
```json
{
  "file_name": "sample_transcript.pdf",
  "download_url": "https://acedra-documents.s3.ap-south-1.amazonaws.com/students/1/...?X-Amz-Signature=...",
  "expires_in": 300
}
```

---

## AWS Cloud Infrastructure

### Amazon S3 Bucket Architecture
- Buckets are configured with **Block All Public Access** enabled.
- Objects are placed using collision-free partitioned keys:
  ```text
  s3://<S3_BUCKET_NAME>/
  └── students/
      └── <student_id>/
          └── <uuid4>_<filename>
  ```

### AWS Secrets Manager
In production mode, the application retrieves the JWT signing key at startup:
```bash
aws secretsmanager create-secret \
    --name "acedra/jwt" \
    --description "Acedra JWT Secret Key" \
    --secret-string '{"SECRET_KEY":"your-cryptographically-secure-hex-string"}' \
    --region ap-south-1
```

### Least-Privilege IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AcedraS3DocumentVault",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::acedra-documents-*/*"
    },
    {
      "Sid": "AcedraSecretsAccess",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:acedra/jwt-*"
    }
  ]
}
```

---

## Testing & Quality Assurance

```bash
# Run pytest test suite
pytest -v

# Run with test coverage report
pytest --cov=app --cov-report=term-missing

# Code formatting
black app/ alembic/

# Linting with flake8
flake8 app/ --max-line-length=88
```

---

## Security

- **Zero Hardcoded Secrets**: Secrets are injected via `.env` in local development and loaded from AWS Secrets Manager in production.
- **Bcrypt Password Hashing**: Passwords are never saved in cleartext; salted hashes are generated via passlib.
- **Private Object Storage**: Amazon S3 objects are completely private; client retrieval occurs through time-bounded (300-second TTL) HMAC presigned URLs.
- **UUIDv4 Collision Shielding**: Uploaded files receive isolated UUIDv4 prefixes preventing filename collisions or overwrites.
- **SQL Parameterization**: SQLAlchemy 2.0 uses parameterized query bindings, neutralizing SQL injection vectors.
- **Payload Sanitization**: Pydantic v2 schemas enforce strict validation on emails, dates, and input lengths.

---

## Production Cloud Deployment

Acedra is designed for cloud-native deployment across containerized services:

- **Web / API Service**: Deployable as a container on **AWS ECS (Fargate)**, **AWS EC2**, **Render**, or **DigitalOcean App Platform**.
- **Managed Database**: **Amazon RDS for PostgreSQL 16** or **Neon Database**.
- **Object Storage**: **Amazon S3** bucket in the corresponding VPC region.
- **Secrets**: **AWS Secrets Manager** (`acedra/jwt`).
- **Production Command**:
  ```bash
  gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
  ```

---

## Support

If you find this project helpful, please consider giving it a star on GitHub!

<p align="left">
  <a href="https://github.com/TituJesh/Acedra">
    <img src="https://img.shields.io/github/stars/TituJesh/Acedra?style=social" alt="Star on GitHub" />
  </a>
</p>

---

## License & Author

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

Developed by **[TituJesh](https://github.com/TituJesh)**.
