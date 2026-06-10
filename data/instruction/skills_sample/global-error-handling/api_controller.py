from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    
    # Call payment service
    payment_response = requests.post(
        'http://payment-service/charge',
        json={"amount": data["amount"], "card": data["card_token"]}
    )
    
    # Call inventory service
    inventory_response = requests.post(
        'http://inventory-service/reserve',
        json={"product_id": data["product_id"], "quantity": data["quantity"]}
    )
    
    # Save to database
    order_id = save_order_to_db(data, payment_response.json(), inventory_response.json())
    
    return jsonify({"order_id": order_id, "status": "created"})

def save_order_to_db(data, payment, inventory):
    # Database save logic
    return 12345
