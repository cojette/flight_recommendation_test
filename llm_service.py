import os
import random
import json
import re
try:
    import google.genai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

class LLMService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.use_mock = not self.api_key
        
        if not self.use_mock and HAS_GEMINI:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-3-pro-preview')
            except Exception as e:
                print(f"Failed to initialize Gemini: {e}. Falling back to Mock.")
                self.use_mock = True
        elif not self.use_mock and not HAS_GEMINI:
            print("google-generativeai package not installed. Falling back to Mock.")
            self.use_mock = True

    def generate_explanation(self, flight, market_stats, user_prefs=None, status="Recommended"):
        """
        Generates a natural language explanation for a flight recommendation.
        
        Args:
            flight (dict): Flight details.
            market_stats (dict): Avg price and duration for the route.
            user_prefs (dict): User preferences (optional).
            status (str): "Recommended" or "Avoid".
            
        Returns:
            str: Explanation text.
        """
        if self.use_mock:
            return self._generate_mock_explanation(flight, market_stats, user_prefs, status)
        else:
            return self._generate_gemini_explanation(flight, market_stats, user_prefs, status)

    def _generate_mock_explanation(self, flight, market_stats, user_prefs, status):
        """Logic-based mock explanation generator."""
        avg_price = market_stats.get('avg_price', flight['price'])
        avg_duration = market_stats.get('avg_duration', flight['duration_minutes'])
        
        price_diff_pct = ((flight['price'] - avg_price) / avg_price) * 100
        duration_diff_mins = flight['duration_minutes'] - avg_duration
        
        reasons = []
        
        if status == "Recommended":
            if price_diff_pct < -10:
                reasons.append(f"{abs(int(price_diff_pct))}% cheaper than average")
            if duration_diff_mins < -30:
                reasons.append(f"{abs(int(duration_diff_mins/60))}h faster")
            if flight['stops'] == 0:
                reasons.append("non-stop")
            
            if user_prefs:
                if flight['airline'] in user_prefs.get('preferred_airlines', []):
                    reasons.append(f"matches your preference for {flight['airline']}")
            
            if not reasons:
                return "Balanced option with good value."
                
            return f"Recommended because it is {', '.join(reasons)}."
            
        else: # Avoid / Bad Option
            if price_diff_pct > 20:
                reasons.append(f"price is {int(price_diff_pct)}% higher than average")
            if duration_diff_mins > 60:
                reasons.append(f"duration is {int(duration_diff_mins/60)}h longer")
            if flight['stops'] > 1:
                reasons.append("multiple layovers")
                
            if not reasons:
                return "Not the best value compared to other options."
                
            return f"Note: {', '.join(reasons)}."

    def _generate_gemini_explanation(self, flight, market_stats, user_prefs, status):
        """Calls Gemini API for explanation."""
        prompt = f"""
        You are an AI travel assistant.
        
        Context:
        - Flight: {flight['airline']} to {flight['destination']}, ${flight['price']:.2f}, {flight['duration_minutes']}m, {flight['stops']} stops.
        - Market Average: ${market_stats['avg_price']:.2f}, {market_stats['avg_duration']:.0f}m.
        - User Preferences: {user_prefs if user_prefs else 'None'}
        - Status: {status}
        
        Task: Explain why this flight is {status} in 1 short sentence (max 20 words).
        - If Recommended: Highlight savings or time benefits explicitly (e.g., "20% cheaper", "3h faster").
        - If Avoid: Highlight downsides explicitly (e.g., "Price is 50% above average", "2x longer duration").
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating explanation: {str(e)}"

    def parse_search_query(self, query):
        """
        Parses a natural language query into structured search criteria.
        Returns JSON: { 'max_price': int, 'max_stops': int, 'time_of_day': str, 'sort_by': str }
        """
        if not query:
            return {}

        if self.use_mock:
            return self._mock_parse_query(query)

        prompt = f"""
        Extract search filters from this user query for flight search.
        Return ONLY a raw JSON object (no markdown, no constraints if not mentioned).
        Fields:
        - max_price (int): if mentioned (e.g. "under 500")
        - max_stops (int): if mentioned (e.g. "direct" is 0, "1 stop" is 1)
        - time_of_day (str): "morning" (5-12), "afternoon" (12-17), "evening" (17-21), "night" (21-5)
        - sort_by (str): "price", "duration"
        
        User Query: "{query}"
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Simple cleanup to ensure valid JSON
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            return json.loads(text)
        except Exception as e:
            print(f"LLM Parsing failed: {e}. Falling back to keyword search.")
            return self._mock_parse_query(query)

    def _mock_parse_query(self, query):
        """Simple keyword fallback"""
        criteria = {}
        q = query.lower()
        
        if "direct" in q or "non-stop" in q:
            criteria['max_stops'] = 0
            
        if "morning" in q:
            criteria['time_of_day'] = 'morning'
        elif "afternoon" in q:
            criteria['time_of_day'] = 'afternoon'
        elif "evening" in q:
            criteria['time_of_day'] = 'evening'
            
        if "cheap" in q or "budget" in q:
            criteria['sort_by'] = 'price'
        elif "fast" in q or "short" in q:
            criteria['sort_by'] = 'duration'
            
        # simple price extraction
        price_match = re.search(r'under \$?(\d+)', q)
        if price_match:
            criteria['max_price'] = int(price_match.group(1))
            
        return criteria
