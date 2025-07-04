# Airflow Bidding Dashboard

React-based dashboard for viewing Japanese government procurement/bidding data.

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The app will run on http://localhost:3000 and proxy API requests to http://localhost:8000

## Features

- **Dashboard Overview**: Statistics cards, charts, and recent bidding cases
- **Search & Filter**: Full-text search and filtering by organization, prefecture, industry, and price range
- **Case Details**: Detailed view of individual bidding cases with similar case recommendations
- **Responsive Design**: Mobile-friendly interface using Tailwind CSS

## Tech Stack

- React 18 with TypeScript
- React Router for navigation
- React Query for data fetching and caching
- Chart.js for data visualization
- Tailwind CSS for styling
- Axios for API communication

## API Integration

The app expects the backend API to be running on port 8000 with the following endpoints:

- `GET /api/v1/bidding/cases` - List cases with pagination and filters
- `GET /api/v1/bidding/cases/:id` - Get single case details
- `GET /api/v1/bidding/stats` - Get statistics
- `GET /api/v1/bidding/search` - Search cases
- `GET /api/v1/bidding/cases/:id/similar` - Get similar cases