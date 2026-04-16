import os, requests, uuid6
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///profiles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Profile(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    gender = db.Column(db.String(20))
    gender_probability = db.Column(db.Float)
    sample_size = db.Column(db.Integer)
    age = db.Column(db.Integer)
    age_group = db.Column(db.String(20))
    country_id = db.Column(db.String(10))
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
        "id": p.id, "name": p.name, "gender": p.gender,
        "gender_probability": p.gender_probability, "sample_size": p.sample_size,
        "age": p.age, "age_group": p.age_group, "country_id": p.country_id,
        "country_probability": p.country_probability, "created_at": p.created_at
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
    gender = request.args.get('gender')
    country = request.args.get('country_id')
    age_grp = request.args.get('age_group')
    
    query = Profile.query
    if gender: query = query.filter(Profile.gender.ilike(gender))
    if country: query = query.filter(Profile.country_id.ilike(country))
    if age_grp: query = query.filter(Profile.age_group.ilike(age_grp))
    
    results = query.all()
    return jsonify({"status": "success", "count": len(results), "data": [format_profile(p) for p in results]}), 200

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
