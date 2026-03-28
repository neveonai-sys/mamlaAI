# Mamla.AI - Legal Tech Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-3.2%2B-green)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18.0%2B-61DAFB)](https://reactjs.org/)

## Overview
Mamla.AI is a comprehensive legal technology platform designed to bring legal services to your fingertips. The platform connects lawyers with clients, streamlines case management, and provides AI-powered legal assistance.

## Features

### eCourts Intelligence (Active)
- eCourts v2 terminal flows for case status, cause list, caveat (staged), and court orders
- Court-order search modes: by party, case number, court number, and order date
- CAPTCHA-assisted scraping via FastAPI bridge with Django proxy APIs
- Authenticated order PDF download with session-cookie forwarding and clear 404/422 handling
- Hierarchical location cascade (state → district → complex → establishment) with session restore on back/forward navigation

### AI-Powered Legal Assistance
- AI-driven document generation and review
- Legal research assistance
- Document template management
- Automated legal drafting
- TalkDoc document chat with session-scoped retrieval and quota-aware usage
- Mamla Brain framework (domain reasoning, document QA, case companion, API-key mode)

### User Management
- Secure authentication with Supabase
- Role-based access control (Lawyers, Clients, Admins)
- Client onboarding and management
- Multi-device session management

### Case Management
- Case creation and tracking
- Document organization
- Calendar and deadline management
- Client communication portal
- Recurring legal calendar workflows with conflict checks and series-aware updates

### Search & Discovery
- Advanced legal document search
- Lawyer directory
- Case law database
- Document version control

### Mobile Responsive
- Fully responsive design
- Cross-browser compatibility
- Progressive Web App (PWA) support

## Tech Stack

### Backend
- **Framework**: Django 3.2+
- **Database**: MongoDB (Primary), PostgreSQL (via Supabase)
- **Authentication**: Supabase Auth
- **Search**: OpenSearch
- **Task Queue**: Celery with Redis
- **API**: Django REST Framework
- **Caching**: Redis
- **Storage**: Supabase Storage, AWS S3

### Frontend
- **Active frontend**: `mamlaAI_ground_zero/frontend` (React 18 + Tailwind CSS)
- **Previous frontend**: `frontend_webpack` (legacy React app kept for reference)
- **State Management**: Redux Toolkit
- **Styling**: Tailwind CSS
- **UI Components**: Headless UI, Custom Components
- **Form Handling**: React Hook Form
- **Routing**: React Router

### DevOps
- **Containerization**: Docker
- **CI/CD**: GitHub Actions
- **Monitoring**: Sentry
- **Logging**: ELK Stack

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB 4.4+
- Redis 6.0+
- Docker (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/neveonai-sys/mamlaAI.git
   cd mamlaAI
   ```

2. **Set up backend**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install Python dependencies
   pip install -r requirements.txt

   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Set up frontend**
   ```bash
   cd ../mamlaAI_ground_zero/frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local with your frontend configuration
   ```

4. **Initialize the database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run the development servers**
   ```bash
   # Backend (in project root)
   python manage.py runserver

   # Frontend (in mamlaAI_ground_zero/frontend directory)
   npm start
   ```

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
MONGODB_URI=mongodb://localhost:27017/
MONGODB_NAME=legaldb

# Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_SERVICE_ROLE=your-service-role

# AWS (if using S3)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Documentation

**Architecture, API reference, and incremental improvement plans** are in the **`docs/`** folder. Start here for a precise picture of the codebase:

- **[docs/README.md](docs/README.md)** — Index of all docs (architecture, backend, frontend, API reference, changelog).
- Use these when onboarding, refactoring, or asking an AI to continue work: they describe *what*, *how*, and *where* things happen and what changes were made.

API paths and auth are documented in **docs/04-api-reference.md**; the list there is the source of truth for current endpoints.

For eCourts architecture and terminal-flow behavior, see **docs/06-ecourts-scraper.md**.

## Project Structure

```
mamlaAI/
├── Legalv1/                  # Django backend
│   ├── users/               # User management
│   ├── ai_draft/            # AI document generation
│   ├── calendar_management/  # Calendar and scheduling
│   ├── create_drafts/        # Document creation
│   ├── search_facility/      # Search functionality
│   └── whatsapp_module/      # WhatsApp integration
│
├── mamlaAI_ground_zero/frontend/  # Active React frontend served by Nginx
│
├── frontend_webpack/         # Previous React frontend kept for reference
│   ├── public/              # Static files
│   └── src/
│       ├── components/      # Reusable UI components
│       ├── pages/           # Page components
│       ├── store/           # Redux store
│       └── services/        # API services
│
├── advocate_list/            # Lawyer directory
├── draftdocs/               # Document templates
└── docker/                  # Docker configuration
```

## API Notes

- Primary API base path: `/api/`
- Authentication model: **Supabase-only** (Bearer token and/or `access_token` cookie)
- eCourts v2 proxy paths: `/api/ecourts/v2/...`
- Full endpoint list and request contracts: `docs/04-api-reference.md`

Representative active endpoints:

- `GET /api/health/`
- `GET /api/users/check-auth/`
- `GET /api/users/entitlements/summary/`
- `POST /api/aidrafts/start_session`
- `GET/POST /api/calendar/events/`
- `POST /api/talkdoc/query/`
- `POST /api/ecourts/v2/courtorder/by-order-date/`
- `POST /api/ecourts/v2/order-court-numbers/`

## Testing

### Backend Tests
```bash
python manage.py test
```

### Frontend Tests
```bash
cd ../mamlaAI_ground_zero/frontend
npm test
```

frontend commands:
```
Development: npm start
Production: npm run start:prod or npm run build && npx serve -s dist -l 3000
```

The active production UI is built from `mamlaAI_ground_zero/frontend`. `frontend_webpack` remains in the repo as the previous UI and should only be used for historical reference or parity checks.

## Deployment

### Production
```bash
# Build active frontend
cd mamlaAI_ground_zero/frontend
npm run build

# Collect static files
python manage.py collectstatic --noinput

# Run with Gunicorn
gunicorn Legalv1.wsgi:application -w 4 -b :8000
```

### Docker
```bash
docker-compose up --build
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For support or queries, please contact neveon.ai@gmail.com or open an issue in the repository.

---

<div align="center">
  Made with ❤️ by the MamlaAi Team
</div>
