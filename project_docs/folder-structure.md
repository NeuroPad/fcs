---

**Recommended FastAPI Project Folder Structure (Best Practices)**

```
memduo/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── patients.py
│   │   │   │   ├── sessions.py
│   │   │   │   ├── chats.py
│   │   │   │   ├── diagnoses.py
│   │   │   │   ├── assessments.py
│   │   │   │   └── roles.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── __init__.py
│   ├── crud(can be /
│   │   ├── user.py
│   │   ├── patient.py
│   │   ├── session.py
│   │   ├── chat.py
│   │   ├── diagnosis.py
│   │   ├── assessment.py
│   │   ├── role.py
│   │   └── __init__.py
│   ├── models/
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── patient.py
│   │   ├── session.py
│   │   ├── chat.py
│   │   ├── diagnosis.py
│   │   ├── assessment.py
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── patient.py
│   │   ├── session.py
│   │   ├── chat.py
│   │   ├── diagnosis.py
│   │   ├── assessment.py
│   │   └── __init__.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   ├── main.py
│   └── __init__.py
├── alembic/ (optional for migrations)
├── .env
├── requirements.txt
└── README.md
```

---