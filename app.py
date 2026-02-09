from flask import Flask, render_template, request, jsonify
from recommendation_engine import FlightRecommendationEngine
import os

app = Flask(__name__)

# Initialize Engine
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Note: Assuming data is in the same dir as per previous steps
# If running from scratch dir, these paths are correct relative to where we run python
engine = FlightRecommendationEngine(
    os.path.join(BASE_DIR, 'user_profiles.json'),
    os.path.join(BASE_DIR, 'flights_data.json')
)
engine.load_data()

@app.route('/')
def index():
    # Pass generic lists for dropdowns
    origins = sorted(list(set(f['origin'] for f in engine.flights)))
    destinations = sorted(list(set(f['destination'] for f in engine.flights)))
    # Sample logged-in users for testing
    sample_users = [u for u in engine.users if u['user_type'] == 'logged_in'][:10]
    return render_template('index.html', origins=origins, destinations=destinations, sample_users=sample_users)

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    user_id = data.get('user_id')
    semantic_query = data.get('semantic_query')
    include_hotels = data.get('include_hotels', False) # New field
    
    if user_id == "guest":
        user_id = None
        
    results = engine.filter_and_rank(origin, destination, user_id, semantic_query)
    
    if include_hotels and "error" not in results:
        try:
            print(f"Fetching hotels for {destination}...")
            results['hotels'] = engine.recommend_hotels(destination)
            print(f"Found {len(results['hotels'])} hotels.")
        except Exception as e:
            print(f"Hypothetical Hotel Error: {e}")
            import traceback
            traceback.print_exc()
            results['hotels_error'] = str(e)
            
    return jsonify(results)

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, port=5000)
