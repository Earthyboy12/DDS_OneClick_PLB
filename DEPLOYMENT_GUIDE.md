# คู่มือการติดตั้งและนำระบบขึ้นใช้งานจริง (Production Deployment Guide)
## Thai Digital Disease Surveillance (DDS) Analytical Platform

ระบบนี้ได้รับการออกแบบตามสถาปัตยกรรม **Decoupled Modern Web Architecture**:
* **Frontend (React + Vite + Tailwind CSS)**: โฮสต์บน **Vercel** เพื่อความรวดเร็วระดับ Global CDN และไม่มีข้อจำกัดขนาดไฟล์ฝั่ง UI
* **Backend (FastAPI + Pandas + SciPy + SQLite)**: รันแบบ Containerized Service บน **Render.com**, **Railway**, **Google Cloud Run** หรือ **เซิร์ฟเวอร์ On-Premise** เพื่อประมวลผลไฟล์ขนาดใหญ่ (200 MB+) ได้อย่างเต็มประสิทธิภาพโดยไม่ติด Payload Limit 4.5 MB ของ Vercel

---

## สถาปัตยกรรมการเชื่อมต่อ (Architecture Overview)

```
[ผู้ใช้งาน / Browser] 
       │
       ├── (1) โหลดหน้าเว็บ HTML/JS/CSS ───────────► [ Vercel CDN (Frontend) ]
       │
       └── (2) อัปโหลดไฟล์ 200MB+ / เรียก API ───► [ Cloud / VPS (FastAPI Backend) ]
                                                            │
                                                     [ dds_reference.sqlite ]
                                                     [ 4K Figures / Data Session ]
```

> **ข้อได้เปรียบสำคัญ**: เมื่อตั้งค่า `VITE_API_BASE_URL` ใน Vercel ให้ชี้ไปยัง Backend โดยตรง เบราว์เซอร์จะส่งไฟล์ขนาดใหญ่ (เช่น 100–200 MB) ไปยัง Backend ตรงๆ ผ่าน CORS ทำให้ **หลุดพ้นจากข้อจำกัด 4.5 MB ของ Vercel Serverless อย่างสิ้นเชิง**

---

## ขั้นตอนที่ 1: ติดตั้ง Backend (เลือก 1 ช่องทางที่สะดวก)

### ช่องทาง A: นำขึ้น Render.com (ฟรี หรือ ค่าบริการต่ำ แนะนำอย่างยิ่ง ⭐)
1. สมัครใช้งาน [Render.com](https://render.com/) และเชื่อมต่อกับ GitHub Repository ของคุณ
2. กด **New +** ➔ เลือก **Web Service**
3. เลือก Repository ของโครงการนี้
4. ตั้งค่าดังนี้:
   * **Name**: `dds-surveillance-api`
   * **Root Directory**: `backend`
   * **Runtime**: `Docker` (ระบบจะตรวจพบ `backend/Dockerfile` อัตโนมัติ)
   * **Instance Type**: `Free` หรือ `Starter`
   * **Environment Variables**:
     * `MAX_UPLOAD_SIZE_MB`: `200` (หรือขนาดที่ต้องการ)
5. กด **Create Web Service**
6. เมื่อ Deploy สำเร็จ คุณจะได้รับ URL เช่น `https://dds-surveillance-api.onrender.com`

---

### ช่องทาง B: นำขึ้น Railway.app
1. สมัครใช้งาน [Railway.app](https://railway.app/)
2. กด **New Project** ➔ **Deploy from GitHub repo**
3. ไปที่แท็บ **Settings** ของ Service ➔ กำหนด **Root Directory** เป็น `/backend`
4. Railway จะ Build ผ่าน `Dockerfile` และจัดสรรพอร์ต `$PORT` ให้อัตโนมัติ
5. ไปที่แท็บ **Networking** ➔ กด **Generate Domain** จะได้ URL เช่น `https://xxx.up.railway.app`

---

### ช่องทาง C: รันบนเซิร์ฟเวอร์หน่วยงาน / On-Premise ด้วย Docker Compose
หากมีเซิร์ฟเวอร์ภายในหน่วยงาน (Linux/Windows Server ที่มี Docker):
```bash
# โคลนโปรเจกต์และสั่งรันทั้ง Frontend + Backend ในคำสั่งเดียว
docker compose up -d --build
```
* หน้าเว็บ Frontend เข้าใช้งานได้ที่: `http://<SERVER_IP>:3000`
* Backend API จะรันอยู่ที่: `http://<SERVER_IP>:8000`

---

## ขั้นตอนที่ 2: นำ Frontend ขึ้น Vercel

1. เข้าสู่ระบบ [Vercel Dashboard](https://vercel.com/)
2. กด **Add New...** ➔ **Project** ➔ เลือก GitHub Repository ของโครงการนี้
3. ในหน้า **Configure Project**:
   * **Framework Preset**: `Vite`
   * **Root Directory**: คลิก `Edit` แล้วเลือกโฟลเดอร์ `frontend`
   * **Build and Output Settings**:
     * Build Command: `npm run build`
     * Output Directory: `dist`
4. **Environment Variables** (สำคัญมาก):
   * Key: `VITE_API_BASE_URL`
   * Value: URL ของ Backend ที่ได้จากขั้นตอนที่ 1 (เช่น `https://dds-surveillance-api.onrender.com`)
5. กด **Deploy** ➔ ภายใน 1–2 นาที หน้าเว็บจะพร้อมใช้งานที่ URL เช่น `https://your-dds-project.vercel.app`

---

## การปรับแต่งขนาดการอัปโหลด (Upload Limit Configuration)

* **ค่าเริ่มต้นปัจจุบัน**: ตั้งไว้ที่ **200 MB**
* หากต้องการปรับเป็น 500 MB หรือขนาดอื่นในอนาคต:
  * ใน Backend: เพียงเปลี่ยน Environment Variable `MAX_UPLOAD_SIZE_MB=500`
  * ฝั่ง Frontend จะอ่านขนาดที่อนุญาตจาก Backend ผ่าน API `/api/import/schema` โดยอัตโนมัติ ไม่ต้องแก้โค้ดใหม่
