import os
from flask import Flask, request, jsonify
import requests
from pymongo import MongoClient
from datetime import datetime, timezone
from bson import ObjectId
from flask_cors import CORS  # Importing CORS

app = Flask(__name__)

# Apply CORS to all routes
CORS(app)

# MongoDB connection
client = MongoClient("mongodb+srv://adicodess11:acche4log12se13@cluster0.bjc8a.mongodb.net/AutoProposalAI")
db = client["AutoProposalAI"]
customer_input_collection = db["customerrequirementinputs"]
car_spec_collection = db["CarSpecificationDataset"]
ai_generated_content_collection = db["AIGeneratedProposalContent"]
users_collection = db["users"]

# Add a root route to serve a welcome message
@app.route('/')
def index():
    return "Welcome to the Proposal Generation API!", 200

def generate_text_with_gemini(prompt):
    api_key = "AIzaSyD5RZ3PQxTMHl36Q9Qfz_EutgSIs2kLaHw"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        try:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except KeyError:
            return "Error: Unexpected response structure"
    else:
        return f"Error: {response.status_code}, {response.text}"

def get_car_data_from_mongodb(car_model_name, version_name):
    car_data = car_spec_collection.find_one({
        "Model": car_model_name,
        "Version": version_name
    })
    
    if car_data is None:
        print(f"No data found for car model: {car_model_name}, version: {version_name}")
    return car_data

def get_customer_fullname_from_users(created_by):
    try:
        # Use the createdBy id to find the user in the users collection
        user_data = users_collection.find_one({"_id": ObjectId(created_by)})
        if user_data:
            return user_data.get('fullname', 'Valued Customer')
        else:
            print(f"No user found for createdBy id: {created_by}")
            return 'Valued Customer'
    except Exception as e:
        print(f"Error fetching customer name: {e}")
        return 'Valued Customer'

def generate_proposal_introduction(car_data, customer_name):
    prompt = f"""
    Create a formal and impressive proposal introduction for the {car_data['Model']} {car_data['Version']} for {customer_name}.
    The introduction should be around 60 - 80 words and include:
    1. A personalized greeting
    2. The value proposition

    The tone should be professional, engaging, and tailored to the customer.
    """
    return generate_text_with_gemini(prompt)

def generate_car_overview(car_data):
    prompt = f"""
    Provide a compelling and informative overview of the {car_data['Model']} {car_data['Version']} without using headings or bullet points. 
    Include the following information in a flowing, narrative style:

    - Brief introduction to the car model and its place in the market
    - General description of the car's design and aesthetics
    - Mention of the car's key strengths (e.g., performance, comfort, technology)
    - How the car stands out in its segment
    - Brief mention of the car's suitability for different types of drivers or uses
    - A subtle nod to the car's value proposition, mentioning its price point of ₹{car_data['Ex-Showroom Price']}

    The tone should be engaging and informative, aimed at giving the reader a clear picture of what the {car_data['Model']} {car_data['Version']} offers. 
    Avoid technical jargon and focus on creating an appealing description that highlights the car's overall character and benefits.
    Do not include any placeholder text or section headers. The response should be a cohesive, flowing paragraph that can be directly used in a professional proposal.
    """
    return generate_text_with_gemini(prompt)

def create_customization_prompt(customer_data, car_data):
    return f"""
    Suggest customization options for the {car_data['Model']} {car_data['Version']} in the following categories:
    1. Exterior Modifications (4 options)
    2. Interior Upgrades (4 options)
    3. Technology Enhancements (4 options)
    Format the response as follows:
    Category Name
    1. Option Name: Brief description.
    2. Option Name: Brief description.
    ...
    Do not use asterisks (*) or hash (#) symbols in your response. Use plain text only.
    """

def process_customization_suggestions(raw_text):
    clean_text = raw_text.replace('*', '').replace('#', ' ')
    
    categories = clean_text.split('\n\n')
    processed_output = []
    
    for category in categories:
        lines = category.strip().split('\n')
        category_name = lines[0]
        options = lines[1:]
        
        processed_output.append(category_name)
        for option in options:
            processed_output.append(option.strip())
        processed_output.append('')  # Add an empty line between categories
    
    return '\n'.join(processed_output).strip()

def generate_proposal_summary(customer_data, car_data):
    prompt = f"""
    Generate a comprehensive summary of the entire car proposal for the {car_data['Model']} {car_data['Version']}. 
    The summary should provide an overview of all key aspects covered in the proposal, following this structure:

    1. Introduction (1 paragraph):
       - Begin with "This proposal outlines a compelling automotive solution for your transportation needs, focusing on the [Car Model and Version]."
       - Mention the customer's key requirements (budget, seating, fuel type, primary use).
       - Conclude by stating how the proposed car aligns with these needs.

    2. Vehicle Specifications and Value Proposition (1 paragraph):
       - Highlight key specifications (engine size, fuel efficiency).
       - Discuss how these features meet the customer's needs, especially for their primary use.
       - Address any pricing considerations, especially if the price exceeds the budget.
       - Mention available financing options or potential offers if applicable.

    3. Additional Features and Customizations (1 paragraph):
       - Briefly mention any suggested customizations or add-ons.
       - Indicate that detailed information on these options is provided in the proposal.

    4. Summary and Conclusion (1 paragraph):
       - Recap the car's standout features (e.g., safety, design, practicality).
       - Emphasize the overall value proposition.
       - Mention any next steps or additional services offered (e.g., test drives, further consultations).

    Use these specific details:
    - Car: {car_data['Model']} {car_data['Version']}
    - Engine: {car_data['Engine Power (cc)']} cc
    - Fuel efficiency: {car_data['Mileage (ARAI) (kmpl)']} kmpl
    - Price: ₹{car_data['Ex-Showroom Price']}
    - Customer Budget: ₹{customer_data['budgetMin']} to ₹{customer_data['budgetMax']}
    - Seating Capacity: {customer_data['seatingCapacity']} seats
    - Fuel Type: {customer_data['fuelType']}
    - Primary Use: {customer_data['primaryUse']}

    Guidelines:
    - Aim for about 200-250 words in total.
    - Ensure the summary provides a complete overview of the proposal's contents.
    - Use a professional yet engaging tone.
    - The summary should be self-contained, allowing readers to understand the key points of the proposal without reading the entire document.

    Generate a unique, comprehensive proposal summary that covers all key aspects of the proposal document.
    """
    return generate_text_with_gemini(prompt)

def create_conclusion_prompt(car_data, customer_name):
    return f"""
    Create a personalized and engaging conclusion for a car proposal for the {car_data['Model']} {car_data['Version']} to be presented to {customer_name}.

    Car Information:
    - Model: {car_data['Model']}
    - Version: {car_data['Version']}
    - Key Features: {', '.join(car_data.get('Key Features', ['Feature information not available']))}
    - Engine: {car_data.get('Engine', 'Engine information not available')}
    - Fuel Type: {car_data.get('Fuel Type', 'Fuel type information not available')}
    - Price: {car_data.get('Price', 'Price information not available')}

    The conclusion should follow this structure:
    1. Address the customer by their name.
    2. State that "as we've explored", the car presents a compelling proposition for their needs.
    3. Mention how it's ideal for daily commutes and weekend adventures.
    4. Emphasize competitive pricing, safety features, and fuel economy.
    5. Mention that it "ticks all the boxes" for their requirements.
    6. Encourage a test drive to experience its qualities firsthand.
    7. Thank them for considering the proposal.
    8. Offer to answer further questions.
    9. End with an invitation to "embark on this exciting journey together" and experience the joy of driving the car.
    10. Don't use I, use we and that too sparingly.

    Guidelines:
    - Use the exact phrasing provided where possible.
    - Maintain a warm yet professional tone.
    - Ensure the content flows naturally and builds excitement.
    - The conclusion should be about 6-8 sentences long.
    """

def save_to_mongodb(session_id, content):
    ai_generated_content_collection.update_one(
        {"sessionId": session_id},
        {"$set": content},
        upsert=True
    )

@app.route('/generateProposal', methods=['POST'])
def generate_proposal():
    # Get data from the POST request
    data = request.get_json()

    session_id = data.get("sessionId")
    car_model_name = data.get("carModelName")
    version_name = data.get("versionName")
    created_by = data.get("createdBy")

    if not session_id or not car_model_name or not version_name or not created_by:
        return jsonify({"error": "Missing required fields"}), 400

    # Fetch customer and car data from MongoDB
    customer_data = customer_input_collection.find_one({"sessionId": session_id})
    car_data = get_car_data_from_mongodb(car_model_name, version_name)

    if not customer_data or not car_data:
        return jsonify({"error": "Unable to fetch customer or car data"}), 404

    # Generate proposal sections
    customer_name = get_customer_fullname_from_users(created_by)
    introduction = generate_proposal_introduction(car_data, customer_name)
    car_overview = generate_car_overview(car_data)
    customization_prompt = create_customization_prompt(customer_data, car_data)
    customization_suggestions = generate_text_with_gemini(customization_prompt)
    processed_customization = process_customization_suggestions(customization_suggestions)
    proposal_summary = generate_proposal_summary(customer_data, car_data)
    conclusion_prompt = create_conclusion_prompt(car_data, customer_name)
    conclusion = generate_text_with_gemini(conclusion_prompt)

    # Add timestamps
    content = {
        "sessionId": session_id,
        "createdBy": created_by,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
        "introduction": introduction,
        "carOverview": car_overview,
        "customizationSuggestions": processed_customization,
        "proposalSummary": proposal_summary,
        "conclusion": conclusion,
        "generatedAt": datetime.now(timezone.utc)
    }

    # Save the generated proposal content to MongoDB
    save_to_mongodb(session_id, content)

    # Return the generated proposal as a response
    return jsonify(content), 200

# Bind to 0.0.0.0 and dynamically set the port
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
