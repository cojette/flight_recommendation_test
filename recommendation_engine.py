import json
import copy
import statistics
from collections import Counter
from datetime import datetime
from llm_service import LLMService


## Main Flight Recommendation Engine

class FlightRecommendationEngine:
    def __init__(self, user_profiles_path, flights_data_path):
        self.user_profiles_path = user_profiles_path
        self.flights_data_path = flights_data_path
        self.users = []
        self.flights = []
        self.hotels = []
        self.user_map = {}
        self.llm_service = LLMService() # Initialize LLM Service (Auto-detects Mock/Real)

    def load_data(self):
        """Loads user and flight data from JSON files."""
        try:
            with open(self.user_profiles_path, 'r') as f:
                self.users = json.load(f)
                self.user_map = {u['user_id']: u for u in self.users}
            
            with open(self.flights_data_path, 'r') as f:
                self.flights = json.load(f)
            
            try:
                with open('hotels_data.json', 'r') as f:
                    self.hotels = json.load(f)
            except FileNotFoundError:
                print("Warning: hotels_data.json not found.")

            print(f"Loaded {len(self.users)} users, {len(self.flights)} flights, and {len(self.hotels)} hotels.")
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")

    def identify_bad_options(self, flights):
        """
        Identifies 'bad' flight options based on price and duration relative to the average.
        Adds 'is_bad_option' flag and 'bad_option_reason'.
        """
        if not flights:
            return flights

        prices = [f['price'] for f in flights]
        durations = [f['duration_minutes'] for f in flights]
        
        avg_price = statistics.mean(prices)
        avg_duration = statistics.mean(durations)
        
        # Simple thresholds: > 1.5x average price OR > 2.0x average duration
        price_threshold = avg_price * 1.5
        duration_threshold = avg_duration * 2.0
        
        for flight in flights:
            flight['is_bad_option'] = False
            flight['bad_option_reason'] = None
            
            reasons = []
            if flight['price'] > price_threshold:
                reasons.append(f"Price (${flight['price']}) is significantly higher than average (${avg_price:.2f}).")
            
            if flight['duration_minutes'] > duration_threshold:
                reasons.append(f"Duration ({flight['duration_minutes']}m) is significantly longer than average ({avg_duration:.0f}m).")
                
            if reasons:
                flight['is_bad_option'] = True
                flight['bad_option_reason'] = " ".join(reasons)
                
        return flights

    def _calculate_score(self, flight, weight_price=0.4, weight_duration=4.0, weight_stops=50):
        """
        Calculates a base score for a flight (Lower is better).
        Weights are heuristic.
        """
        # Score = (Price * w_p) + (Duration_minutes * w_d) + (Stops * w_s)
        # Note: Normalize inputs or adjust weights if scales are vastly different.
        # Here we rely on tuning weights for the specific data range.
        score = (flight['price'] * weight_price) + \
                (flight['duration_minutes'] * weight_duration) + \
                (flight['stops'] * weight_stops)
        return score

    def recommend_guest(self, flights):
        """
        Recommendation logic for guest users.
        Rank by lowest score (Price, Duration, Stops).
        """
        
        for flight in flights:
            flight['score'] = self._calculate_score(flight)
            
        # Sort by score ascending
        ranked_flights = sorted(flights, key=lambda x: x['score'])
        return ranked_flights

    def recommend_login(self, user_id, flights):
        """
        Personalized recommendation.
        Boosts score based on user history: Airline preference and Direct flight preference.
        """
        user = self.user_map.get(user_id)
        if not user:
            print(f"User {user_id} not found, defaulting to guest recommendation.")
            return self.recommend_guest(flights)
            
        history = user.get('history', [])
        
        # 1. Analyze History
        airline_counts = Counter()
        direct_flight_count = 0
        total_history = len(history)
        
        for record in history:
            # Enhanced logic using embedded details
            if 'airline' in record:
                airline_counts[record['airline']] += 1
                if record.get('stops', 1) == 0:
                    direct_flight_count += 1
            else:
                 pass
        
        preferred_airlines = [airline for airline, count in airline_counts.items() if count >= 3]
        prefers_direct = (total_history > 0) and ((direct_flight_count / total_history) > 0.5)

        # 2. Score with Boosts
        for flight in flights:
            base_score = self._calculate_score(flight)
            multiplier = 1.0
            
            # Boost for preferred airline
            if flight['airline'] in preferred_airlines:
                multiplier *= 0.8 # 20% boost (reduction in score)
                flight['boost_reason'] = f"Preferred Airline: {flight['airline']}"
                
            # Boost for direct flight preference
            if prefers_direct and flight['stops'] == 0:
                multiplier *= 0.8
                if 'boost_reason' in flight:
                    flight['boost_reason'] += ", Preferred Direct Flight"
                else:
                    flight['boost_reason'] = "Preferred Direct Flight"
            
            flight['score'] = base_score * multiplier
            
        # Sort
        ranked_flights = sorted(flights, key=lambda x: x['score'])
        return ranked_flights

    def recommend_hotels(self, city, top_k=3):
        """
        Returns top k hotels in the destination city, sorted by rating.
        """
        if not self.hotels:
            print("No hotels loaded.")
            return []
            
        relevant = [h for h in self.hotels if h['city'].upper() == city.upper()]
        # Sort by rating descending
        ranked = sorted(relevant, key=lambda x: x['rating'], reverse=True)
        return ranked[:top_k]


    def filter_and_rank(self, origin, destination, user_id=None, semantic_query=None):
        """
        Main entry point. Filters flights by route, applies recommendation logic, 
        and returns categorized results with top 20 recommendations.
        """
        # 1. Filter by Route (Case insensitive) & Deep Copy to prevent shared state issues
        relevant_flights = [
            copy.deepcopy(f) for f in self.flights 
            if f['origin'].upper() == origin.upper() and f['destination'].upper() == destination.upper()
        ]
        
        if not relevant_flights:
            return {"error": "No flights found for this route."}

        # 1.5 Semantic Filtering
        if semantic_query:
            criteria = self.llm_service.parse_search_query(semantic_query)
            print(f"Semantic Criteria: {criteria}")
            
            filtered = []
            for f in relevant_flights:
                keep = True
                
                # Max Price
                if 'max_price' in criteria and f['price'] > criteria['max_price']:
                    keep = False
                    
                # Max Stops
                if 'max_stops' in criteria and f['stops'] > criteria['max_stops']:
                    keep = False
                    
                # Time of Day (Approximate)
                if 'time_of_day' in criteria:
                    hour = int(f['departure_time'].split('T')[1].split(':')[0])
                    period = criteria['time_of_day']
                    if period == 'morning' and not (5 <= hour < 12): keep = False
                    elif period == 'afternoon' and not (12 <= hour < 17): keep = False
                    elif period == 'evening' and not (17 <= hour < 21): keep = False
                    elif period == 'night' and not (21 <= hour or hour < 5): keep = False
                
                if keep:
                    f['boost_reason'] = f"Matches '{semantic_query}'"
                    filtered.append(f)
            
            relevant_flights = filtered
            
            if not relevant_flights:
                return {"error": f"No flights match your smart search: {semantic_query}"}
        
        # 2. Identify Bad Options
        relevant_flights = self.identify_bad_options(relevant_flights)
        
        # 3. Apply Recommendation Logic
        if user_id:
            ranked_flights = self.recommend_login(user_id, relevant_flights)
        else:
            ranked_flights = self.recommend_guest(relevant_flights)
            
        # 4. Extract categories
        fastest = sorted(relevant_flights, key=lambda x: x['duration_minutes'])[:20]
        cheapest = sorted(relevant_flights, key=lambda x: x['price'])[:20]
        
        top_20 = ranked_flights[:20]
        
        # 5. Generate Explanations with LLM
        # Calculate market stats for context
        prices = [f['price'] for f in relevant_flights]
        durations = [f['duration_minutes'] for f in relevant_flights]
        market_stats = {
            "avg_price": statistics.mean(prices) if prices else 0,
            "avg_duration": statistics.mean(durations) if durations else 0
        }
        
        user_prefs = None
        if user_id:
            user = self.user_map.get(user_id)
            if user:
                user_prefs = user.get('preferences')

        # Explain Top 5
        for flight in top_20[:20]:
            explanation = self.llm_service.generate_explanation(
                flight, market_stats, user_prefs, status="Recommended"
            )
            flight['llm_explanation'] = explanation
            
        # Explain Bad Options 
        bad_options = [f for f in relevant_flights if f.get('is_bad_option')]
        # Limit to explaining a few bad ones 
        for flight in bad_options[:3]:
             explanation = self.llm_service.generate_explanation(
                flight, market_stats, user_prefs, status="Avoid"
            )
             flight['llm_explanation'] = explanation
        
        return {
            "metadata": {
                "origin": origin,
                "destination": destination,
                "total_found": len(relevant_flights),
                "user_type": "logged_in" if user_id else "guest",
                "market_stats": market_stats
            },
            "recommended": top_20,
            "cheapest": cheapest,
            "fastest": fastest,
            "bad_options_sample": bad_options[:5]
        }

if __name__ == "__main__":
    # Quick sanity check
    engine = FlightRecommendationEngine('user_profiles.json', 'flights_data.json')
    engine.load_data()
    
    # Test Guest
    print("\n--- Testing Guest Recommendation (DXB -> LHR) ---")
    results = engine.filter_and_rank("DXB", "LHR")
    if "error" not in results:
        print(f"Top Recommended: {results['recommended'][0]['airline']} - ${results['recommended'][0]['price']}")
        print(f"Bad Options Count: {sum(1 for f in results['recommended'] if f['is_bad_option'])}")
    else:
        print(results['error'])
