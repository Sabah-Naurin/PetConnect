# 🐾 PetConnect

**PetConnect** is an AI-powered hub designed to bridge the gap between pet owners, spotters, and rescuers. By combining real-time location activity with state-of-the-art Computer Vision, PetConnect helps reunite lost pets and facilitates life-saving rescues and adoptions.

---

## ✨ Key Features

*   **🧠 ML-Powered Matching:** Uses DINOv2 vision models to find similarities between lost pet reports and new sightings automatically.
*   **📍 Location-Based Feed:** Stay updated with pet activity specifically in your registered neighborhood.
*   **🏥 Medical Fund Management:** Verified rescuers can request community funding for medical treatments, integrated with payment verification.
*   **verified Rescue Workflow:** Official custody tracking ensures transparency from the moment a pet is spotted to when it is safely rescued.
*   **🏡 Adoption Portal:** Seamless transition from rescue to finding a forever home.
*   **🔔 Intelligent Notifications:** Real-time updates for matches, claim status, and donation verifications.

---

## 🚀 Quick Setup

### 1. Clone the repository
```bash
git clone https://github.com/Sabah-Naurin/PetConnect.git
cd PetConnect
```

### 2. Set up a Virtual Environment (Recommended)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize the Database
```bash
python manage.py migrate
```

### 5. Create an Administrator
```bash
python manage.py createsuperuser
```

### 6. Start the Application
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` to see it in action!

---

## 🛠️ Technology Stack
- **Backend:** Django (Python)
- **AI/ML:** PyTorch, Hugging Face Transformers (DINOv2)
- **Frontend:** Vanilla CSS, JavaScript, Django Templates
- **Database:** SQLite (default for development)

---

## 👥 Roles & Permissions
- **Pet Owner:** Can post lost reports, claim matches, and finalize adoptions.
- **Spotter:** Can report sightings of pets without taking formal custody.
- **Custodian/Rescuer:** Verified users who take physical custody of pets and manage their medical/rescue progress.
- **Admin:** Manages medical fund approvals, claim verifications, and site-wide monitoring.

---

*Made with ❤️ for animals everywhere.*
