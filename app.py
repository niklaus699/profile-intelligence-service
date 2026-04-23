import os, requests, uuid6
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database Configuration for Postgres
database_url = os.environ.get('DATABASE_URL', 'sqlite:///profiles.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

COUNTRIES_MAP = {
    'tanzania': 'TZ', 'nigeria': 'NG', 'uganda': 'UG', 'sudan': 'SD', 'united states': 'US', 
    'madagascar': 'MG', 'united kingdom': 'GB', 'india': 'IN', 'cameroon': 'CM', 'cape verde': 'CV', 
    'republic of the congo': 'CG', 'mozambique': 'MZ', 'south africa': 'ZA', 'mali': 'ML', 
    'angola': 'AO', 'dr congo': 'CD', 'france': 'FR', 'kenya': 'KE', 'zambia': 'ZM', 
    'eritrea': 'ER', 'gabon': 'GA', 'rwanda': 'RW', 'senegal': 'SN', 'namibia': 'NA', 
    'gambia': 'GM', "côte d'ivoire": 'CI', 'ethiopia': 'ET', 'morocco': 'MA', 'malawi': 'MW', 
    'brazil': 'BR', 'tunisia': 'TN', 'somalia': 'SO', 'ghana': 'GH', 'zimbabwe': 'ZW', 
    'egypt': 'EG', 'benin': 'BJ', 'western sahara': 'EH', 'australia': 'AU', 'china': 'CN', 
    'botswana': 'BW', 'canada': 'CA', 'liberia': 'LR', 'mauritania': 'MR', 'burundi': 'BI', 
    'burkina faso': 'BF', 'central african republic': 'CF', 'mauritius': 'MU', 'algeria': 'DZ', 
    'japan': 'JP', 'guinea-bissau': 'GW', 'eswatini': 'SZ', 'sierra leone': 'SL', 'comoros': 'KM', 
    'seychelles': 'SC', 'south sudan': 'SS', 'germany': 'DE', 'djibouti': 'DJ', 'niger': 'NE', 
    'togo': 'TG', 'lesotho': 'LS', 'chad': 'TD', 'são tomé and príncipe': 'ST', 'libya': 'LY', 
    'guinea': 'GN', 'equatorial guinea': 'GQ'
}

class Profile(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    gender = db.Column(db.String(20), index=True)
    gender_probability = db.Column(db.Float)
    sample_size = db.Column(db.Integer)
    age = db.Column(db.Integer, index=True)
    age_group = db.Column(db.String(20))
    country_id = db.Column(db.String(10), index=True)
    country_name = db.Column(db.String(100))
    country_probability = db.Column(db.Float)
    created_at = db.Column(db.String(30))

with app.app_context():
    db.create_all()
    

def get_age_group(age):
    if age <= 12: return "child"
    if age <= 19: return "teenager"
    if age <= 59: return "adult"
    return "senior"

def format_profile(p):
    return {
        "id": p.id, 
        "name": p.name, 
        "gender": p.gender,
        "gender_probability": p.gender_probability, 
        "sample_size": p.sample_size,
        "age": p.age, 
        "age_group": p.age_group, 
        "country_id": p.country_id,
        "country_name": p.country_name,
        "country_probability": p.country_probability, 
        # Format as UTC ISO 8601 string
        "created_at": p.created_at.strftime('%Y-%m-%dT%H:%M:%SZ') 
    }

# --- ENDPOINTS ---

@app.route('/api/profiles', methods=['POST'])
def create_profile():
    data = request.get_json()
    if not data or 'name' not in data or not str(data['name']).strip():
        return jsonify({"status": "error", "message": "Missing or empty name"}), 400
    
    name = str(data['name']).lower().strip()

    # Idempotency
    existing = Profile.query.filter_by(name=name).first()
    if existing:
        return jsonify({"status": "success", "message": "Profile already exists", "data": format_profile(existing)}), 200

    try:
        g = requests.get(f"https://api.genderize.io?name={name}").json()
        a = requests.get(f"https://api.agify.io?name={name}").json()
        n = requests.get(f"https://api.nationalize.io?name={name}").json()

        if not g.get('gender'): return jsonify({"status": "error", "message": "Genderize returned an invalid response"}), 502
        if a.get('age') is None: return jsonify({"status": "error", "message": "Agify returned an invalid response"}), 502
        if not n.get('country'): return jsonify({"status": "error", "message": "Nationalize returned an invalid response"}), 502

        top_country = max(n['country'], key=lambda x: x['probability'])
        
        new_p = Profile(
            id=str(uuid6.uuid7()), name=name, gender=g['gender'],
            gender_probability=g['probability'], sample_size=g['count'],
            age=a['age'], age_group=get_age_group(a['age']),
            country_id=top_country['country_id'], country_probability=top_country['probability'],
            created_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        )
        db.session.add(new_p)
        db.session.commit()
        return jsonify({"status": "success", "data": format_profile(new_p)}), 201
    except Exception:
        return jsonify({"status": "error", "message": "Upstream server failure"}), 502

@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    try:
        query = Profile.query
        
        # 1. Filtering
        filters = {
            "gender": lambda v: Profile.gender == v.lower(),
            "age_group": lambda v: Profile.age_group == v.lower(),
            "country_id": lambda v: Profile.country_id == v.upper(),
            "min_age": lambda v: Profile.age >= int(v),
            "max_age": lambda v: Profile.age <= int(v),
            "min_gender_probability": lambda v: Profile.gender_probability >= float(v),
            "min_country_probability": lambda v: Profile.country_probability >= float(v)
        }
        
        for param, logic in filters.items():
            val = request.args.get(param)
            if val:
                query = query.filter(logic(val))

        # 2. Sorting (MOVED OUTSIDE THE LOOP)
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'asc')
        sort_map = {
            'age': Profile.age,
            'created_at': Profile.created_at,
            'gender_probability': Profile.gender_probability
        }
        sort_attr = sort_map.get(sort_by, Profile.created_at)
        query = query.order_by(sort_attr.desc() if order == 'desc' else sort_attr.asc())

        # 3. Pagination
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 10)), 50)
        pagination = query.paginate(page=page, per_page=limit, error_out=False)

        return jsonify({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": pagination.total,
            "data": [format_profile(p) for p in pagination.items]
        }), 200
    except Exception:
        return jsonify({"status": "error", "message": "Invalid query parameters"}), 422

@app.route('/api/profiles/<id>', methods=['GET'])
def get_profile(id):
    p = Profile.query.get(id)
    if not p: return jsonify({"status": "error", "message": "Profile not found"}), 404
    return jsonify({"status": "success", "data": format_profile(p)}), 200

@app.route('/api/profiles/<id>', methods=['DELETE'])
def delete_profile(id):
    p = Profile.query.get(id)
    if not p: return jsonify({"status": "error", "message": "Profile not found"}), 404
    db.session.delete(p)
    db.session.commit()
    return '', 204

@app.route('/api/profiles/search', methods=['GET'])
def search_profiles():
    q = request.args.get('q', '').lower()
    if not q:
        return jsonify({"status": "error", "message": "Invalid query parameters"}), 400

    query = Profile.query
    interpreted = False

    # Gender Parsing
    if 'male' in q and 'female' not in q:
        query = query.filter(Profile.gender == 'male'); interpreted = True
    elif 'female' in q:
        query = query.filter(Profile.gender == 'female'); interpreted = True

    # Age Parsing
    if 'young' in q:
        query = query.filter(Profile.age >= 16, Profile.age <= 24); interpreted = True
    if 'teenager' in q:
        query = query.filter(Profile.age_group == 'teenager'); interpreted = True
    if 'adult' in q:
        query = query.filter(Profile.age_group == 'adult'); interpreted = True
    
    import re
    above_match = re.search(r'above (\d+)', q)
    if above_match:
        query = query.filter(Profile.age > int(above_match.group(1))); interpreted = True

    for country_name, code in COUNTRIES_MAP.items():
        if country_name in q:
            query = query.filter(Profile.country_id == code); interpreted = True
            break
    if not interpreted:
        return jsonify({"status": "error", "message": "Unable to interpret query"}), 422

    # Apply same pagination to search
    page = int(request.args.get('page', 1))
    limit = min(int(request.args.get('limit', 10)), 50)
    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    return jsonify({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": pagination.total,
        "data": [format_profile(p) for p in pagination.items]
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)


