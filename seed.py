import json
import uuid6
from app import app, db, Profile

def seed_data():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        try:
            with open('seed_profiles.json', 'r') as f:
                data = json.load(f)
                # Adjust based on your JSON structure (usually 'profiles' key)
                profiles_list = data.get('profiles', data) 
        except FileNotFoundError:
            print("Error: seed_profiles.json not found.")
            return

        print(f"Starting seed process for {len(profiles_list)} records...")
        
        count = 0
        for item in profiles_list:
            # Idempotency check: Don't add if name already exists
            exists = Profile.query.filter_by(name=item['name']).first()
            if not exists:
                new_profile = Profile(
                    id=str(uuid6.uuid7()), # Requirement: UUID v7
                    name=item['name'],
                    gender=item['gender'],
                    gender_probability=item.get('gender_probability'),
                    age=item['age'],
                    age_group=item['age_group'],
                    country_id=item['country_id'],
                    country_name=item['country_name'],
                    country_probability=item.get('country_probability'),
                    sample_size=item.get('sample_size', 0)
                )
                db.session.add(new_profile)
                count += 1
            
            # Commit in batches for performance
            if count % 100 == 0:
                db.session.commit()

        db.session.commit()
        print(f"Success! Seeded {count} new profiles.")

if __name__ == "__main__":
    seed_data()