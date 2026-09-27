**AI Spend Calculator 💰**

A smart personal finance tracker that helps you understand your spending habits with AI-powered insights.

** What is AI Spend Calculator?**

AI Spend Calculator is a simple yet powerful web app that lets you:

- **Track expenses** - Log your daily transactions with categories

- **Get AI insights** - Automatically categorizes your spending as "useful" or "wasteful"

- **Set budgets** - Monthly budget tracking with progress alerts

- **Visualize spending** - Charts and graphs to see where your money goes

- **Predict future spending** - AI predicts your next month's expenses based on your history


 **Features**

📱 Easy Transaction Management

- Add expenses with simple forms

- Auto-suggest categories based on transaction notes

- Edit or delete transactions easily

- Search and filter your spending history


 **Smart AI Features**

- Auto-categorization: Just type "coffee at Starbucks" and it suggests "Food & Dining"

- Useful vs Wasteful Analysis: Understand your spending patterns

- Spending Predictions: Get next month's expense estimates


** Visual Analytics**

- Pie charts by category

- Monthly spending trends

- Daily expense patterns

- Budget progress tracker

 **Privacy First**

- Your data stays on your device

- Secure user accounts

- No sharing of financial information


**🛠️ Installation**
Prerequisites
Python 3.7 or higher
pip (Python package manager)

Setup
1. Clone the repository
git clone https://github.com/piyush16512/ai-spend-calculator.git

cd ai-spend-calculator

2. Create a virtual environment
python -m venv venv

3. Activate the virtual environment
Windows:
venv\Scripts\activate

4. Install dependencies
pip install -r requirements.txt

5. Run the application
streamlit run app.py

**📁 Project Structure**

ai-spend-calculator/

├── app.py              # Main application file

├── db.py               # Database operations

├── utils.py            # Helper functions and AI logic

├── requirements.txt    # Python dependencies

└── README.md           # This file


 How to Use
Getting Started
1. Create an account - Sign up with a username and password
2. Set your budget - Enter your monthly spending limit
3. Start logging - Add your daily transactions

Adding Transactions
1. Go to the Dashboard
2. Fill in the "Add Transaction" form:
- Date: When you spent the money
- Note: Description (like "lunch at cafe")
- Category: Type or let AI suggest one
- Amount: How much you spent


 **Technical Details**

Built With
- **Streamlit** - Web app framework

- **SQLite** - Database storage

- **Pandas** - Data manipulation

- **Altair** - Data visualization

- **Python** - Backend logic


**AI Features:**

- Category Suggestion: Uses keyword matching from transaction notes
- Useful/Wasteful Classification: Rule-based system for spending analysis
- Spending Prediction: 3-month moving average forecasting

**🤝 Contributing**

We welcome contributions! Here's how:
1. Fork the project
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

**👨‍💻 Developer**

**Piyush Kumar**

Building simple solutions for everyday problems
