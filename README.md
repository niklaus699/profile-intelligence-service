🚀 Live API URLBase URL: https://profile-intelligence-service-production-2118.up.railway.app/ 
🛠 Features 
1. Advanced Query EngineThe GET /api/profiles endpoint supports complex combinations of the following filters:Demographics: gender, age_groupLocation: country_id (ISO 2-letter codes)Thresholds: min_age, max_age, min_gender_probability, min_country_probabilitySorting: Results can be sorted by age, created_at, or gender_probability in asc or desc order.Pagination: Strictly controlled pagination via page and limit (max 50 per page).
2. Natural Language Query (NLQ)The GET /api/profiles/search endpoint allows users to query the database using plain English.
How the parser works (No-AI Implementation):Our custom rule-based engine tokenizes the input string and matches keywords against predefined mapping logic:


Age Mapping: "young" is dynamically mapped to the 16–24 age range.



Group Mapping: Keywords like "adult" or "teenager" apply filters to the age_group field.
Comparative Logic: Uses Regex to detect patterns like "above 30" to apply numerical filters.
Geography: Scans the query for full country names (e.g., "Nigeria") and maps them to their respective ISO codes (NG).Example Search: GET /api/profiles/search?q=young males from nigeria
        📊 Database Schema
The system uses PostgreSQL with the following required structure:FieldTypeNotesidUUID v7Primary Key (Time-ordered)nameVARCHARUnique, full namegenderVARCHAR"male" or "female"ageINTExact ageage_groupVARCHARchild, teenager, adult, seniorcountry_idVARCHAR(2)ISO code (e.g., NG)created_atTIMESTAMPUTC ISO 8601⚙️ Technical SetupData SeedingThe database is seeded with 2026 unique records using a custom idempotency script (seed.py). This script ensures that re-running the process does not create duplicate records while maintaining the UUID v7 standard for all new entries.Performance OptimizationIndexing: Indexes are applied to filtered columns to ensure efficient querying of the 2,000+ record dataset.Standardized Responses: All API errors follow the strict JSON structure:JSON{ "status": "error", "message": "<error message>" }

📦 Requirements

Flask & Flask-SQLAlchemy
Psycopg2-binary
(PostgreSQL Driver)UUID6 (for UUID v7 generation)Flask-CORS