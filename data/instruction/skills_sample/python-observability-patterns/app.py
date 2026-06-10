from flask import Flask, request, jsonify
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    user_id = request.json.get('user_id')
    start = time.time()
    
    logger.info(f"Getting recommendations for user {user_id}")
    
    # Fetch user profile
    user_profile = fetch_user_profile(user_id)
    
    # Call ML model
    recommendations = ml_model.predict(user_profile)
    
    duration = time.time() - start
    logger.info(f"Recommendations generated in {duration:.3f}s")
    
    return jsonify({"recommendations": recommendations})

def fetch_user_profile(user_id: int) -> dict:
    # Simulated DB call
    return {"user_id": user_id, "preferences": []}
