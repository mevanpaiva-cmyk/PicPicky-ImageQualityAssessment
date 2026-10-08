# 📸 PicPicky — Image Quality Assessment & Photographer Profiling

PicPicky is a web application that analyzes uploaded photos for technical and aesthetic quality, detects duplicates, builds a profiling system for photographers, and ensures complete image privacy through end-to-end encryption.

Built as a Final Year Project (BCA) — Backend & ML pipeline by [Mary Evangelin Paiva & M Bushra Fathima](https://github.com/bushrafathima26)

---

## 🚀 Features

- **Blur Detection** — Flags out-of-focus images using Laplacian variance analysis
- **Duplicate Detection** — Identifies near-duplicate images using perceptual hashing (pHash)
- **Technical Quality Analysis** — Evaluates sharpness, exposure accuracy, noise control, saturation balance, and contrast quality
- **Aesthetic Scoring** — Rates images using the CLIP-IQA deep learning model
- **Explainability** — Generates human-readable verdicts, strengths, issues, and improvement suggestions per image
- **Photographer Profiling** — Tracks submission quality over time and builds a profile score with skill level (Beginner → Expert)
- **Best Album Curation** — Auto-selects top images with technical score > 80 and aesthetic score > 0.6
- **Image Privacy (Encryption)** — Images are AES-encrypted before upload; only the authenticated owner can decrypt and view them
- **Cloudinary Integration** — Encrypted blobs stored as raw files; never viewable from the Cloudinary dashboard
- **User Authentication** — Register/login with JWT-based session management and bcrypt password hashing
- **Password Reset** — Secure time-limited token sent via email for password recovery
- **Admin Dashboard** — System-level overview of users, uploads, alerts, and activity

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | MongoDB Atlas |
| Image Storage | Cloudinary (encrypted raw blobs) |
| ML Models | PyTorch, CLIP-IQA |
| Image Processing | OpenCV, Pillow, pillow-heif |
| Duplicate Detection | imagehash (pHash) |
| Encryption | Python cryptography (Fernet / AES) |
| Auth | JWT, bcrypt |
| Frontend | HTML, Tailwind CSS, JavaScript |

---

## 📁 Project Structure
PicPicky/
│
├── main.py                  # FastAPI app entry point
├── config.py                # Environment & configuration
├── database.py              # Database connection setup
├── requirements.txt         # Python dependencies
├── test.py                  # Testing script
├── README.md                # Project documentation
│
├── models/
│   └── user.py              # User schema/model
│
├── routes/
│   ├── auth.py              # Authentication (login/register/password reset)
│   ├── upload.py            # Image upload, processing, decrypt & serve routes
│   └── admin.py             # Admin-related endpoints
│
├── services/
│   ├── blur_detection.py        # Blur detection (Laplacian variance)
│   ├── duplicate_detection.py   # Duplicate detection (pHash)
│   ├── technical_quality.py     # 5-metric technical quality analysis
│   ├── clipiqa_scorer.py        # Aesthetic scoring (CLIP-IQA)
│   ├── explainability.py        # Human-readable score explanations
│   └── encryption.py            # AES image encryption & decryption (Fernet)
│
├── frontend/
│   ├── home.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── upload.html
│   ├── analysis.html
│   ├── profile.html
│   ├── best-album.html
│   ├── sidebar.html
│   ├── admin.html
│   ├── admin-auth.js
│   ├── admin-functions.js
│   ├── forgot_pass.html
│   └── reset-password.html
│
├── venv/                    # Virtual environment (ignored in Git)
└── .env                     # Environment variables (ignored in Git)

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/bushrafathima26/PicPicky.git
cd PicPicky
```

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# or
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the root directory:

```env
MONGODB_URI=your_mongodb_atlas_connection_string
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
SECRET_KEY=your_jwt_secret_key
EMAIL_USER=your_email_for_password_reset
EMAIL_PASS=your_email_password
```

### 5. Run the application
```bash
uvicorn main:app --reload
```
The app will be available at `http://localhost:8000`

---

## 🧠 ML Pipeline Overview
Image Upload
│
▼
Format Validation & Compression (JPEG, PNG, HEIC/HEIF → JPEG, max 10MB)
│
▼
Blur Detection ──► Laplacian variance → is_blurry flag
│
▼
Duplicate Check ──► pHash Hamming distance ≤ 5 → is_duplicate flag
│
▼
Technical Quality Analysis
(Sharpness · Exposure · Noise · Saturation · Contrast → technical_score)
│
▼
Aesthetic Scoring (CLIP-IQA → aesthetic_score 0.0–1.0)
│
▼
Explainability (Verdict · Strengths · Issues · Suggestions)
│
▼
AES Encryption (Fernet) → Upload to Cloudinary as raw encrypted blob
│
▼
Store metadata + scores in MongoDB

---

## 🔒 Privacy & Security

- **Passwords** — hashed with bcrypt before storage; never stored in plain text
- **Sessions** — JWT tokens with 30-minute expiry
- **Image Encryption** — each user gets a unique AES key (Fernet) generated at registration and stored in MongoDB. Images are encrypted server-side after ML analysis and before Cloudinary upload
- **Decryption** — only the authenticated owner can request their images via `/image/{image_id}`, which decrypts and streams the image back securely
- **Admin cannot view images** — Cloudinary dashboard only shows unreadable encrypted blobs

---

## 👩‍💻 Author

**Mary Evangelin Paiva**
**Bushra Fathima**  
BCA Final Year — Bengaluru  
[GitHub](https://github.com/bushrafathima26)

---

## 📄 License

This project is for academic purposes only.