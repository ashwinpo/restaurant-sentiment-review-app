# Bloomin' Brands Review Validation App

A web application for validating LLM-generated sentiment analysis and aspect classifications of customer reviews.

## Features

- **Dashboard**: Overview of pending reviews, validation metrics, and quick access to reviews
- **Review Validation**: Detailed review interface with sentiment and aspect editing capabilities
- **Machine Learning Comparison**: Compare current labels with machine evaluation results
- **Bloomin' Brands Styling**: Custom branding with company colors and logo
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Architecture

- **Backend**: FastAPI with Python
- **Frontend**: React with TypeScript and Vite
- **Styling**: Tailwind CSS with custom Bloomin' Brands theme
- **Data Management**: React Query for API state management
- **Deployment**: Databricks Apps compatible

## Project Structure

```
bloomin-review/
├── backend/
│   ├── app.py              # Main FastAPI application
│   ├── models.py           # Pydantic models
│   ├── mock_data.py        # Mock data for testing
│   ├── routes/
│   │   ├── v1/
│   │   │   ├── reviews.py  # Review endpoints
│   │   │   ├── metrics.py  # Metrics endpoints
│   │   │   └── healthcheck.py
│   │   └── __init__.py
│   ├── requirements.txt    # Python dependencies
│   └── venv/              # Virtual environment
├── frontend/
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── types/         # TypeScript types
│   │   └── App.tsx
│   ├── dist/              # Built frontend (committed for Databricks)
│   ├── package.json
│   └── tailwind.config.js
├── app.yaml               # Databricks Apps configuration
└── README.md
```

## Local Development

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm

### Backend Setup

1. Create and activate virtual environment:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the backend server:
```bash
uvicorn app:app --reload --port 8000
```

The backend will be available at http://localhost:8000

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

### Production Build

1. Build the frontend:
```bash
cd frontend
npm run build
```

2. Start the backend (it will serve the built frontend):
```bash
cd backend
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000
```

The complete application will be available at http://localhost:8000

## API Endpoints

### Reviews
- `GET /api/v1/reviews` - List reviews with filtering
- `GET /api/v1/reviews/{id}` - Get detailed review
- `POST /api/v1/reviews/{id}/validate` - Validate a review

### Metrics
- `GET /api/v1/metrics/overview` - Get dashboard metrics

### Health
- `GET /api/v1/healthcheck` - Health check
- `GET /api/debug/frontend` - Frontend build status

## Databricks Deployment

### Quick Deployment (Databricks Apps)

1. Ensure the frontend is built and committed:
```bash
cd frontend
npm run build
git add dist/
git commit -m "Update frontend build"
```

2. Push to your Databricks Repo

3. Deploy using Databricks Apps with the provided `app.yaml`

### Production Deployment (Databricks Asset Bundles - Recommended)

For production deployments with environment management and portability:

1. **Quick Start**: See `QUICKSTART_DAB.md` for testing the bundle
2. **Full Guide**: See `DEPLOYMENT.md` for comprehensive deployment documentation
3. **Client Setup**: See `CLIENT_CONFIG_TEMPLATE.md` for deploying to client environments

**Benefits of using DAB:**
- Environment isolation (dev/staging/prod)
- Easy configuration management
- Client-specific table configurations
- Version controlled deployments
- CI/CD integration ready

**Deploy with DAB:**
```bash
# Validate configuration
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Deploy to production
databricks bundle deploy --target prod

# Deploy to client environment
databricks bundle deploy --target client
```

## Data Schema

The application expects data matching the schema defined in `schema.md`:

- `Response_Id`: Unique identifier
- `Question_Label`: Type of question/survey
- `Question_Response`: Original customer comment
- `sentiment_analysis`: Positive/Negative/Neutral
- `Atmosphere`, `Service`, etc.: Aspect scores (0-1)
- `profane`: Boolean for profanity detection
- `rewritten_comment`: Cleaned version if profane

## Customization

### Colors
The app uses Bloomin' Brands colors defined in `tailwind.config.js`:
- Red: #D02927
- Green: #8DC63F  
- Blue: #009AD9

### Mock Data
Currently uses mock data in `backend/mock_data.py`. Replace with actual database connections for production.

## Future Enhancements

- Database integration with Databricks tables
- User authentication and authorization
- Bulk validation operations
- Advanced filtering and search
- Export capabilities
- Real-time updates via WebSockets

## License

Internal use for Bloomin' Brands.
# restaurant-sentiment-review-app
