import json
import random
import uuid
from datetime import datetime, timedelta

# Configuration
NUM_USERS = 500  # > 300
NUM_FLIGHTS = 30000  # > 20,000 (representing available flights or history)
AIRPORTS = ["DXB", "DEL", "SIN", "LHR", "JFK", "HND", "CDG", "AMS", "FRA", "ICN", "BKK", "SFO", "JED"]
AIRLINES = [
    {"name": "Emirates", "reliability": 0.95},
    {"name": "Singapore Airlines", "reliability": 0.96},
    {"name": "British Airways", "reliability": 0.85},
    {"name": "Lufthansa", "reliability": 0.88},
    {"name": "Air India", "reliability": 0.75},
    {"name": "United Airlines", "reliability": 0.82},
    {"name": "Korean Air", "reliability": 0.90},
    {"name": "Delta", "reliability": 0.89},
]
CABS = ["Economy", "Business", "First"]
HOTEL_CHAINS = ["Hilton", "Marriott", "Hyatt", "Sheraton", "Ritz-Carlton", "Holiday Inn", "Local Luxury", "Comfort Inn"]
ROOM_TYPES = ["Standard King", "Double Queen", "Deluxe Suite", "Executive Room"]

def generate_users(num_users):
    users = []
    for _ in range(num_users):
        user_type = random.choice(["guest", "logged_in"])
        user_id = str(uuid.uuid4())
        
        user = {
            "user_id": user_id,
            "user_type": user_type,
            "preferences": {},
            "history": []
        }
        
        if user_type == "logged_in":
            user["name"] = f"User_{user_id[:8]}"
            user["preferences"] = {
                "preferred_airlines": random.sample([a["name"] for a in AIRLINES], k=random.randint(0, 2)),
                "max_stops": random.choice([0, 1, 2, "any"]),
                "price_sensitivity": random.choice(["low", "medium", "high"]), # low = wants cheapest
                "preferred_time": random.choice(["morning", "afternoon", "night", "any"])
            }
        
        users.append(user)
    return users

def generate_hotels():
    hotels = []
    for city in AIRPORTS:
        # Generate ~50 hotel options per city
        for _ in range(50):
            chain = random.choice(HOTEL_CHAINS)
            name = f"{chain} {city} {random.choice(['Downtown', 'Airport', 'City Center', 'Grand', 'Resort'])}"
            room = random.choice(ROOM_TYPES)
            
            # Price logic
            base = 100
            if "Suite" in room: base += 200
            elif "Executive" in room: base += 100
            if chain in ["Ritz-Carlton", "Hyatt", "Local Luxury"]: base *= 1.5
            
            price = base + random.randint(-50, 50)
            
            # Rating logic (weighted towards better ratings for demo)
            rating = round(random.uniform(3.0, 5.0), 1)
            
            hotel = {
                "hotel_id": str(uuid.uuid4()),
                "city": city,
                "name": name,
                "room_type": room,
                "price_per_night": round(price, 2),
                "rating": rating
            }
            hotels.append(hotel)
    return hotels

def generate_flight_records(num_records):
    flights = []
    base_date = datetime.now()
    
    for _ in range(num_records):
        origin = random.choice(AIRPORTS)
        destination = random.choice([a for a in AIRPORTS if a != origin])
        airline = random.choice(AIRLINES)
        
        # Base price calculation logic
        distance_factor = random.uniform(0.5, 2.0) 
        base_price = 300 + (distance_factor * 500)
        
        stops = random.choices([0, 1, 2], weights=[0.4, 0.4, 0.2])[0]
        
        # Duration logic (approximate)
        base_duration_hours = 3 + (distance_factor * 8)
        duration_multiplier = 1.0 + (stops * 0.3) # Stops add time
        total_duration = base_duration_hours * duration_multiplier
        
        departure_time = base_date + timedelta(days=random.randint(1, 90), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        arrival_time = departure_time + timedelta(hours=total_duration)
        
        # Adjust price based on airline and stops (non-stop is usually more expensive)
        price = base_price * (1.2 if stops == 0 else 0.8) * (1.0 + (airline["reliability"] - 0.8))
        price = round(price, 2)
        
        flight = {
            "flight_id": str(uuid.uuid4()),
            "airline": airline["name"],
            "flight_number": f"{airline['name'][:2].upper()}{random.randint(100, 999)}",
            "origin": origin,
            "destination": destination,
            "departure_time": departure_time.isoformat(),
            "arrival_time": arrival_time.isoformat(),
            "duration_minutes": int(total_duration * 60),
            "stops": stops,
            "price": price,
            "reliability_score": airline["reliability"]
        }
        flights.append(flight)
        
    return flights

def assign_history_to_users(users, flights):
    # Simulate past bookings/searches for logged-in users using a subset of generated flights
    logged_in_users = [u for u in users if u["user_type"] == "logged_in"]
    
    for user in logged_in_users:
        if not flights:
            break
            
        # Give each logged-in user 5-20 historical records
        num_history = random.randint(5, 20)
        history_flights = random.sample(flights, min(num_history, len(flights)))
        
        history_records = []
        for f in history_flights:
            record = {
                "flight_id": f["flight_id"],
                "action": random.choice(["booked", "searched", "clicked"]),
                "timestamp": (datetime.fromisoformat(f["departure_time"]) - timedelta(days=random.randint(10, 30))).isoformat(),
                # Embedding flight details for easier analysis
                "airline": f["airline"],
                "origin": f["origin"],
                "destination": f["destination"],
                "stops": f["stops"],
                "price": f["price"],
                "duration_minutes": f["duration_minutes"]
            }
            history_records.append(record)
            
        user["history"] = history_records

def main():
    print("Generating users...")
    users = generate_users(NUM_USERS)
    
    print("Generating flight data...")
    flights = generate_flight_records(NUM_FLIGHTS)
    
    print("Generating hotel data...")
    hotels = generate_hotels()
    
    print("Assigning history to logged-in users...")
    assign_history_to_users(users, flights)
    
    print("Saving to JSON files...")
    with open("user_profiles.json", "w") as f:
        json.dump(users, f, indent=2)
        
    with open("flights_data.json", "w") as f:
        json.dump(flights, f, indent=2)
        
    with open("hotels_data.json", "w") as f:
        json.dump(hotels, f, indent=2)
        
    print(f"Done! Generated {len(users)} users, {len(flights)} flights, and {len(hotels)} independent hotel options.")

if __name__ == "__main__":
    main()
