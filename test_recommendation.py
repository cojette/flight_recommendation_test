# Test Recommendation Engine with Data 

import json
from recommendation_engine import FlightRecommendationEngine

def print_flight_summary(flight, rank=None):
    prefix = f"{rank}. " if rank else ""
    bad_flag = "[BAD]" if flight.get('is_bad_option') else ""
    boost = f"(Boost: {flight.get('boost_reason')})" if flight.get('boost_reason') else ""
    print(f"{prefix}{bad_flag} {flight['airline']}, ${flight['price']}, {flight['duration_minutes']}m, {flight['stops']} stops {boost}")
    if flight.get('llm_explanation'):
        print(f"   [AI Explanation]: {flight['llm_explanation']}")
    if bad_flag and not flight.get('llm_explanation'): # Fallback to rule reason if no LLM
        print(f"   [Reason]: {flight['bad_option_reason']}")

def main():
    engine = FlightRecommendationEngine('user_profiles.json', 'flights_data.json')
    engine.load_data()
    
    # 1. Test Guest Recommendation
    print("\n" + "="*50)
    print("TEST CASE 1: Guest User (DXB -> LHR)")
    print("="*50)
    results_guest = engine.filter_and_rank("DXB", "LHR")
    
    if "error" in results_guest:
        print("No flights found for DXB -> LHR")
        return

    print(f"Found {results_guest['metadata']['total_found']} flights.")
    print("\nTop 5 Recommended (Guest):")
    for i, f in enumerate(results_guest['recommended'][:20], 1):
        print_flight_summary(f, i)
        
    print("\nCheapest Option:")
    print_flight_summary(results_guest['cheapest'][0])
    
    print("\nBad Option Example (with AI Explanation):")
    if 'bad_options_sample' in results_guest and results_guest['bad_options_sample']:
        for f in results_guest['bad_options_sample'][:2]:
            print_flight_summary(f)
    else:
        print("No bad options found in this sample query.")

    # 2. Test Logged-in User (Find one with clear preferences if possible, or simulate)
    # Let's pick a user from profiles who has preferences
    logged_in_users = [u for u in engine.users if u['user_type'] == 'logged_in']
    if logged_in_users:
        test_user = logged_in_users[0]
        print("\n" + "="*50)
        print(f"TEST CASE 2: Logged-in User ({test_user['user_id']})")
        print(f"Preferences: {test_user['preferences']}")
        print(f"History Len: {len(test_user['history'])}")
        print("="*50)
        
        # We assume the user searches a route that exists. DXB->LHR exists? 
        # Since data is random, let's pick a route from our flights data that actually exists.
        sample_flight = engine.flights[0] # Pick a random flight to get valid route
        origin = sample_flight['origin']
        dest = sample_flight['destination']
        
        print(f"Searching {origin} -> {dest} for Test User...")
        
        results_login = engine.filter_and_rank(origin, dest, user_id=test_user['user_id'])
        
        print("\nTop 5 Recommended (Logged-in):")
        for i, f in enumerate(results_login['recommended'][:20], 1):
            print_flight_summary(f, i)

if __name__ == "__main__":
    main()
