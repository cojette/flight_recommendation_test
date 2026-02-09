import os
import sys
from recommendation_engine import FlightRecommendationEngine

# ==========================================
# ENTER YOUR GEMINI API KEY HERE
# ==========================================
GEMINI_API_KEY = "AIzaSyAZyVO_IvNbNDwBEnRQl4rHyJ-COlu3zBs" 
# ==========================================

def print_flight_summary(flight, rank=None):
    prefix = f"{rank}. " if rank else ""
    bad_flag = "[BAD]" if flight.get('is_bad_option') else ""
    boost = f"(Boost: {flight.get('boost_reason')})" if flight.get('boost_reason') else ""
    print(f"{prefix}{bad_flag} {flight['airline']}, ${flight['price']}, {flight['duration_minutes']}m, {flight['stops']} stops {boost}")
    if flight.get('llm_explanation'):
        print(f"   [AI Explanation]: {flight['llm_explanation']}")

def main():
    # Set the key in environment for LLMService to pick it up
    if GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        print("Please edit this file and replace 'YOUR_API_KEY_HERE' with your actual Gemini API Key.")
        print("Running in MOCK MODE for now...\n")
    else:
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        print("Running with REAL GEMINI API...\n")

    engine = FlightRecommendationEngine('user_profiles.json', 'flights_data.json')
    engine.load_data()
    
    print("\n" + "="*50)
    print("TEST: Guest User (DXB -> LHR) with Explanations")
    print("="*50)
    
    results = engine.filter_and_rank("DXB", "LHR")
    
    if "error" in results:
        print(results['error'])
        return

    print("\nTop 3 Recommended:")
    for i, f in enumerate(results['recommended'], 1):
        print_flight_summary(f, i)
        
    print("\nBad Option Example:")
    if 'bad_options_sample' in results and results['bad_options_sample']:
        print_flight_summary(results['bad_options_sample'][0])

if __name__ == "__main__":
    main()
