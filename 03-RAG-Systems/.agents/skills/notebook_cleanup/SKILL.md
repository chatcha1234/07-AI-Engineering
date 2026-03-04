---
name: notebook_cleanup
description: ดูแลและจัดการไฟล์ Jupyter Notebook (.ipynb) เช่น การล้าง Output ให้อยู่ในสถานะที่สะอาดก่อนการ Commit เข้า Git เพื่อป้องกันไฟล์บวมและ conflict
---

# Notebook Cleanup and Management Skill

## 🎯 จุดประสงค์ (Purpose)

เนื่องจากโปรเจกต์มีการใช้งาน Jupyter Notebook ขนาดไฟล์ `.ipynb` มักจะใหญ่ขึ้นจากพิกเซลรูปภาพหรือ Text Output ซึ่งยากต่อการจัดการใน Version Control ระบบจึงต้องช่วยดูแลส่วนนี้

## ⚡ เงื่อนไขการทำงาน (Triggers)

1. เมื่อผู้ใช้ทำงานกับ Notebook เสร็จและเตรียมจะ Commit โค้ด
2. เมื่อระบบตรวจจับว่าไฟล์ `.ipynb` มีขนาดใหญ่ผิดปกติ
3. เมื่อผู้ใช้ต้องการ "clean notebook"

## 🛠️ ขั้นตอนปฏิบัติ (Actions)

1. หากต้องใช้อัตโนมัติ: แนะนำให้ติดตั้งเครื่องมือ `nbstripout` หรือรันเช็คเอาต์ Output ของ Jupyter
2. หากไม่มีเครื่องมือ ให้เสนอสคริปต์สั้นๆ ในการล้าง Output ออกจากไฟล์ `.ipynb`
3. เตือนผู้ใช้ให้ระมัดระวังเกี่ยวกับข้อมูลส่วนตัว (เช่น API Keys: `OPENAI_API_KEY`) ที่อาจเผลอปริ้นท์ทิ้งไว้ใน Output ของ Notebook ก่อนที่จะเผยแพร่
