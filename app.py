from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import pandas as pd
import base64
import os
import traceback
import bcrypt

# Initialize Flask app and enable CORS
app = Flask(__name__)
CORS(app)

load_dotenv()

#Configure MongoDB (adjust your MongoDB URI here)
client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]
organisation_collection = db["organisations"]

# Helper function to handle logo upload (mock implementation)
def upload_image(base64_data):
    try:
        # Decode the base64 data
        image_data = base64.b64decode(base64_data)
        # Create an image path (mock save path)
        image_path = os.path.join("uploads", "logo.jpg")
        os.makedirs("uploads", exist_ok=True)
        with open(image_path, "wb") as f:
            f.write(image_data)
        # Return the path or URL where the image is stored
        return image_path
    except Exception as e:
        app.logger.error(f"Failed to upload image: {e}")
        return None

# Route to register an organization
@app.route('/register_org', methods=['POST'])
def register_org():
    org_name = request.form.get('orgName')
    org_username = request.form.get('orgUsername')
    org_password = request.form.get('orgPassword')
    contact_number = request.form.get('contactNumber')
    email = request.form.get('email')

    # Check if organization username already exists
    existing_org = organisation_collection.find_one({"orgUsername": org_username})
    if existing_org:
        return jsonify({"message": "Organisation with this username already exists"}), 400

    # Process Excel file if provided
    user_records = []
    if 'excelFile' in request.files:
        file = request.files['excelFile']
        try:
            df = pd.read_excel(file)
            user_records = df.to_dict(orient='records')
        except Exception as e:
            app.logger.error(f"Error processing Excel file: {str(e)}")
            return jsonify({"message": "Failed to process Excel file"}), 500
    else:
        return jsonify({"message": "No Excel file uploaded"}), 400

    # Process logo if provided
    logo_url = None
    if 'logo' in request.form:
        logo_data = request.form.get('logo')
        logo_url = upload_image(logo_data)
        if not logo_url:
            return jsonify({"message": "Failed to upload logo image"}), 500

    # Insert organization data into MongoDB
    org_data = {
        "orgName": org_name,
        "orgUsername": org_username,
        "orgPassword": org_password,
        "contactNumber": contact_number,
        "email": email,
        "userRecords": user_records,
        "logoUrl": logo_url
    }
    organisation_collection.insert_one(org_data)

    return jsonify({"message": "Organisation registered successfully"}), 201

@app.route('/login_org', methods=['POST'])
def login_org():
    """
    curl -X POST http://localhost:5000/login \
    -H "Content-Type: application/json" \
    -d '{
      "username": "exampleUsername",
      "email": "example@example.com",
      "password": "examplePassword"
    }'

    {
      "message": "Login successful"
    }
    """
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        print(username, email, password)

        if not username or not email or not password:
            return jsonify({"error": "Missing credentials"}), 400

        user = organisation_collection.find_one({"orgName": username})
        print(user)
        if user:
            if password == user.get('orgPassword'):
                return jsonify({"message": "Login successful"}), 200
            else:
                return jsonify({"error": "Invalid credentials"}), 401
        else:
            return jsonify({"error": "User does not exist"}), 401

    except PyMongoError as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
