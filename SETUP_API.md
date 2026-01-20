# FastAPI Setup Guide - Task-4

This guide provides step-by-step instructions to set up and run the FastAPI Analytical API.

## Prerequisites Checklist

- [ ] Python 3.11+ installed and in PATH
- [ ] PostgreSQL 16+ running (via Docker or local installation)
- [ ] dbt installed and configured
- [ ] Virtual environment activated (if using one)

## Step-by-Step Setup

### 1. Activate Virtual Environment (if using one)

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Or if pip is not in PATH:**
```bash
python -m pip install -r requirements.txt
```

**Expected output**: FastAPI, Uvicorn, SQLAlchemy, and other dependencies will be installed.

### 3. Verify PostgreSQL is Running

**Option A: Using Docker Compose**
```bash
docker-compose up -d postgres
```

**Check status:**
```bash
docker-compose ps
```

**Option B: Local PostgreSQL**
Ensure PostgreSQL is running and accessible with credentials from `.env` file.

### 4. Verify Database Connection

Check that your `.env` file contains:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=medical_warehouse
POSTGRES_USER=medical_user
POSTGRES_PASSWORD=medical_pass
```

**Note**: Adjust these values to match your PostgreSQL setup.

### 5. Populate dbt Marts (if not already done)

```bash
# Run dbt models to create/populate marts
dbt run

# Verify marts exist
dbt test
```

**Expected output**: All dbt models (dim_channels, dim_dates, fct_messages, fct_image_detections) should be created in the `marts` schema.

### 6. Start FastAPI Server

**Option A: Using convenience script**
```bash
python run_api.py
```

**Option B: Using uvicorn directly**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 7. Access API Documentation

Once the server is running, open your browser and navigate to:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 8. Test API Endpoints

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Top Products:**
```bash
curl "http://localhost:8000/api/reports/top-products?limit=10"
```

**Channel Activity:**
```bash
curl "http://localhost:8000/api/channels/CheMed/activity?period=daily&days_back=30"
```

**Message Search:**
```bash
curl "http://localhost:8000/api/search/messages?query=paracetamol&limit=20"
```

**Visual Content Stats:**
```bash
curl http://localhost:8000/api/reports/visual-content
```

## Troubleshooting

### Issue: "pip is not recognized"
**Solution**: Use `python -m pip` instead, or activate your virtual environment.

### Issue: "Python was not found"
**Solution**:
1. Install Python 3.11+ from python.org
2. Add Python to PATH during installation
3. Or use the full path to Python executable

### Issue: "Database connection failed"
**Solution**:
1. Verify PostgreSQL is running: `docker-compose ps` or check service status
2. Check `.env` file has correct database credentials
3. Test connection manually: `psql -h localhost -U medical_user -d medical_warehouse`

### Issue: "No module named 'api'"
**Solution**:
1. Ensure you're in the project root directory
2. Run from the directory containing the `api/` folder
3. Check that `api/__init__.py` exists

### Issue: "Table 'marts.fct_messages' does not exist"
**Solution**: Run `dbt run` to create dbt marts before starting the API.

### Issue: Port 8000 already in use
**Solution**:
1. Change port: `uvicorn api.main:app --port 8001`
2. Or stop the process using port 8000

## Verification Checklist

Before accessing the API, verify:

- [ ] Python and pip are accessible
- [ ] All dependencies installed successfully
- [ ] PostgreSQL is running
- [ ] dbt marts are populated (check with `dbt run`)
- [ ] `.env` file has correct database credentials
- [ ] FastAPI server starts without errors
- [ ] Health endpoint returns 200: `curl http://localhost:8000/health`

## Next Steps

Once the API is running:

1. **Explore API Documentation**: Visit http://localhost:8000/docs
2. **Test Endpoints**: Use the interactive Swagger UI to test all endpoints
3. **Integrate with BI Tools**: Connect dashboards or BI tools to the API endpoints
4. **Monitor Performance**: Check logs for any errors or performance issues

## Support

For issues or questions, refer to:
- Task-4 documentation: `docs/task-4-api-documentation.md`
- README.md: See Task-4 section
- API code: `api/main.py` for endpoint implementations
