---
name: python_dependency_management
description: จัดการและดูแล Dependencies ของโปรเจกต์ Python ผ่านเครื่องมือ `uv` เพื่อให้ไฟล์ `pyproject.toml` และ `requirements.txt` ซิงก์กันเสมอ
---

# Python Dependency Management Skill

## 🎯 จุดประสงค์ (Purpose)

เพื่อให้แน่ใจว่าการจัดการแพ็กเกจของโปรเจกต์มีความถูกต้อง รวดเร็ว (ด้วย `uv`) และไฟล์กำหนดเวอร์ชันต่างๆ ได้รับการอัปเดตอย่างสม่ำเสมอ หลีกเลี่ยงปัญหา environment ไม่ตรงกัน

## ⚡ เงื่อนไขการทำงาน (Triggers)

1. เมื่อผู้ใช้ขอให้ติดตั้ง ลบ หรืออัปเดตแพ็กเกจ
2. เมื่อผู้ใช้พบปัญหาเกี่ยวกับการ Import module ไม่เจอ (ModuleNotFoundError)
3. เมื่อมีการดึงโค้ดใหม่ที่มีแก้ไขอัปเดตไฟล์ dependency

## 🛠️ ขั้นตอนปฏิบัติ (Actions)

1. ติดตั้งแพ็กเกจใหม่โดยใช้คำสั่ง `uv add <package_name>` เสมอ
2. ลบแพ็กเกจด้วยคำสั่ง `uv remove <package_name>`
3. หากผู้ใช้ต้องการ freeze เวอร์ชัน ให้ใช้คำสั่ง `uv pip freeze > requirements.txt` หรือ `uv export --format requirements-txt > requirements.txt` ตามความเหมาะสม
4. หากพบปัญหาเกี่ยวกับแพ็กเกจ ให้รันคำสั่งตรวจสอบด้วย `uv pip list` หาเวอร์ชันที่ใช้อยู่
5. ตรวจสอบดูว่า Virtual Environment (.venv) มีการเรียกใช้งาน (Activate) อยู่เสมอในการรันคำสั่งที่เกี่ยวข้องกับ Python
