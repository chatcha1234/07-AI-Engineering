# 03 - RAG Systems

โปรเจกต์สำหรับศึกษาและพัฒนา Retrieval-Augmented Generation (RAG)

---

## 🛠️ Tech Stack

- **Python**: 3.12.12 (via pyenv)
- **Package Manager**: uv
- **Notebook**: ipykernel (Jupyter)

## 📦 Dependencies

```
langchain
langchain-core
langchain-community
pypdf
pymupdf
ipykernel
```

---

## 🚀 Project Setup

### 1. ติดตั้ง Python 3.12 (ถ้ายังไม่มี)

```bash
pyenv install 3.12
```

### 2. ตั้ง Python version ของโปรเจกต์

```bash
pyenv local 3.12
```

### 3. สร้าง Virtual Environment

```bash
uv venv
```

### 4. Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 5. ติดตั้ง Dependencies

```bash
uv add -r requirements.txt
```

### 6. ติดตั้ง Jupyter Kernel (สำหรับ Notebook)

```bash
uv add ipykernel
```

---

## ▶️ การใช้งาน

```bash
# Activate venv ก่อนทุกครั้ง
source .venv/bin/activate

# รัน script
python main.py
```

---

## 📁 โครงสร้างโปรเจกต์

```
03-RAG-Systems/
├── .python-version     # กำหนด Python version (3.12)
├── .venv/              # Virtual environment
├── pyproject.toml      # Project metadata
├── requirements.txt    # Dependencies
├── main.py             # Entry point
└── README.md           # ไฟล์นี้
```
