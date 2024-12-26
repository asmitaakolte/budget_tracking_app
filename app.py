from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import os

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()
app.config["MONGO_URI"] = "mongodb+srv://asmitaakolte:2L4EBv1LHZE13YZw@cluster0.zthl5.mongodb.net/budget_tracker?retryWrites=true&w=majority&appName=Cluster0"

mongo = PyMongo(app)


# Helper function to make MongoDB objects JSON serializable
def serialize_mongo_obj(obj):
    if not obj:
        return obj
    obj['_id'] = str(obj['_id'])  # Convert ObjectId to string
    return obj




@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        collections = mongo.db.list_collection_names()
        return jsonify({"message": "MongoDB connected", "collections": collections}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/add-income', methods=['POST'])
def add_income():
    data = request.json  # Access the JSON data from the request
    date = data.get('date')
    income = data.get('income')

    if not date or not income:
        return jsonify({"error": "Date and income are required"}), 400

    mongo.db.income.update_one(
        {"date": date},
        {"$set": {"date": date, "income": income}},
        upsert=True
    )
    return jsonify({"message": "Income saved successfully!"}), 201

# API: Add Expense
@app.route('/add-expense', methods=['POST'])
def add_expense():
    data = request.json
    date = data.get('date')
    expense_name = data.get('name')
    expense_amount = data.get('amount')

    if not date or not expense_name or not expense_amount:
        return jsonify({"error": "Date, expense name, and amount are required"}), 400

    mongo.db.expenses.insert_one({"date": date, "name": expense_name, "amount": expense_amount})
    return jsonify({"message": "Expense added successfully!"}), 201

# API: Get Monthly Data
@app.route('/monthly/<string:date>', methods=['GET'])
def get_monthly_dashboard(date):
    # Fetch income for the given month
    income = mongo.db.income.find_one({"date": date})
    income = serialize_mongo_obj(income) if income else {"income": 0}

    # Fetch all expenses for the given month
    expenses = list(mongo.db.expenses.find({"date": date}))
    expenses = [serialize_mongo_obj(expense) for expense in expenses]

    # Calculate total expenses
    total_expenses = sum(expense["amount"] for expense in expenses)

    # Calculate savings
    monthly_income = income["income"]
    savings = monthly_income - total_expenses

    return jsonify({
        "date": date,
        "income": monthly_income,
        "total_expenses": total_expenses,
        "savings": savings,
        "expenses": expenses
    }), 200

# API: Get Yearly Data
@app.route('/yearly/<string:year>', methods=['GET'])
def get_yearly_dashboard(year):
    # Fetch income data for the year
    income_data = list(mongo.db.income.find({"date": {"$regex": f"^{year}"}}))

    # Fetch expenses data for the year
    expenses_data = list(mongo.db.expenses.find({"date": {"$regex": f"^{year}"}}))

    # Aggregate income and expenses by month
    monthly_data = {}
    for income in income_data:
        month = income["date"]
        monthly_data[month] = {"income": income["income"], "expenses": 0}

    for expense in expenses_data:
        month = expense["date"]
        if month not in monthly_data:
            monthly_data[month] = {"income": 0, "expenses": 0}
        monthly_data[month]["expenses"] += expense["amount"]

    # Prepare response data
    monthly_summary = [
        {
            "month": month,
            "income": data["income"],
            "expenses": data["expenses"],
            "savings": data["income"] - data["expenses"],
        }
        for month, data in sorted(monthly_data.items())
    ]

    total_income = sum(item["income"] for item in monthly_summary)
    total_expenses = sum(item["expenses"] for item in monthly_summary)
    total_savings = total_income - total_expenses

    return jsonify({
        "year": year,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_savings": total_savings,
        "monthly_summary": monthly_summary,
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
