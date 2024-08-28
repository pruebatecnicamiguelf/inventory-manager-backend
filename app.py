from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
from flask_pymongo import PyMongo
from pymongo.errors import PyMongoError

app = Flask(__name__)
app.config.from_object('config.Config')
mongo = PyMongo(app)

CORS(app, resources={r"/api/*": {"origins": "http://localhost:4200", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})

def get_db_connection():
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

# API Routes

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT id, name FROM ProductTypes")
        products = cursor.fetchall()
        connection.close()

        product_list = [{"id": row[0], "name": row[1]} for row in products]
        return jsonify(product_list), 200
    except pymysql.MySQLError as e:
        return jsonify({"message": "Error fetching products from database.", "error": str(e)}), 500


@app.route('/api/inventory', methods=['POST'])
def add_inventory():
    data = request.json

    if not all(key in data for key in ('product_id', 'product_name', 'serial_number', 'username', 'date')):
        return jsonify({"message": "Missing required fields: product_id, serial_number, username, or date."}), 400
    
    try:
        mongo.db.inventory.insert_one({
            "ProductID": data['product_id'],
            "ProductName": data['product_name'], 
            "SerialNumber": data['serial_number'],
            "Username": data['username'],
            "Date": data['date'],
            "Status": "Available"
        })
        return jsonify({"message": "Product successfully registered in inventory."}), 201
    except PyMongoError as e:
        return jsonify({"message": "Error registering product in inventory.", "error": str(e)}), 500


@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    try:
        products = mongo.db.inventory.find()
        product_list = [{
            "ProductID": product["ProductID"],
            "ProductName": product["ProductName"],
            "SerialNumber": product["SerialNumber"],
            "Username": product.get("Username", ""),
            "Date": product.get("Date", ""),
            "Status": product["Status"]
        } for product in products]
        return jsonify(product_list), 200
    except PyMongoError as e:
        return jsonify({"message": "Error fetching inventory data.", "error": str(e)}), 500



@app.route('/api/inventory/deliver', methods=['POST'])
def deliver_inventory():
    data = request.json

    if 'serial_number' not in data:
        return jsonify({"message": "serial_number is required."}), 400

    try:
        product = mongo.db.inventory.find_one({"SerialNumber": data['serial_number']})
        if product and product['Status'] == "Delivered":
            return jsonify({"message": "This product has already been delivered."}), 400

        mongo.db.inventory.update_one(
            {"SerialNumber": data['serial_number']},
            {"$set": {"Status": "Delivered"}}
        )
        return jsonify({"message": "Product successfully marked as delivered."}), 200
    except PyMongoError as e:
        return jsonify({"message": "Error delivering product.", "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
