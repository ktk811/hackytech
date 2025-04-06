import pickle
import os
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier

# Load trained models
def load_models():
    # Check if models exist
    models_exist = (os.path.exists("vectorizer.pkl") and 
                    os.path.exists("type_classifier.pkl") and 
                    os.path.exists("cat_classifier.pkl") and 
                    os.path.exists("vectorizer_needs.pkl") and 
                    os.path.exists("needs_cat_classifier.pkl"))
    
    if models_exist:
        # Load models
        with open("vectorizer.pkl", "rb") as f:
            vectorizer = pickle.load(f)
        with open("type_classifier.pkl", "rb") as f:
            type_clf = pickle.load(f)
        with open("cat_classifier.pkl", "rb") as f:
            cat_clf = pickle.load(f)
        with open("vectorizer_needs.pkl", "rb") as f:
            vectorizer_needs = pickle.load(f)
        with open("needs_cat_classifier.pkl", "rb") as f:
            needs_cat_clf = pickle.load(f)
            
        return {
            "vectorizer": vectorizer,
            "type_classifier": type_clf,
            "cat_classifier": cat_clf,
            "vectorizer_needs": vectorizer_needs,
            "needs_cat_classifier": needs_cat_clf
        }
    else:
        # Train models
        train_models()
        train_needs_model()
        
        # Now load the trained models
        with open("vectorizer.pkl", "rb") as f:
            vectorizer = pickle.load(f)
        with open("type_classifier.pkl", "rb") as f:
            type_clf = pickle.load(f)
        with open("cat_classifier.pkl", "rb") as f:
            cat_clf = pickle.load(f)
        with open("vectorizer_needs.pkl", "rb") as f:
            vectorizer_needs = pickle.load(f)
        with open("needs_cat_classifier.pkl", "rb") as f:
            needs_cat_clf = pickle.load(f)
            
        return {
            "vectorizer": vectorizer,
            "type_classifier": type_clf,
            "cat_classifier": cat_clf,
            "vectorizer_needs": vectorizer_needs,
            "needs_cat_classifier": needs_cat_clf
        }

# Train models if they don't exist
def train_models():
    import pandas as pd
    from sklearn.model_selection import train_test_split
    
    # Full synthetic dataset with 70 examples (10 each for 7 categories)
    data = {
        "description": [
            "Bought milk and bread", "Ordered pizza online", "Had dinner at an Italian restaurant", 
            "Grabbed a coffee on the way", "Lunch at a local cafe", "Grocery shopping for vegetables and fruits", 
            "Dinner at a sushi bar", "Breakfast at a diner", "Snacked on chips", "Ordered takeout Chinese food", 
            "Paid electricity bill for this month", "Paid water bill", "Settled internet bill", 
            "Paid gas bill", "Paid cable TV subscription", "Received phone bill", "Paid heating bill", 
            "Paid property tax", "Monthly rent payment", "Paid maintenance fee for condo", 
            "Bought a monthly bus pass", "Uber ride to the airport", "Taxi fare from downtown", 
            "Subway ticket purchase", "Train ticket to the city", "Rented a car for a day", 
            "Bike sharing rental", "Paid for ride-sharing service", "Bus fare for school commute", 
            "Ferry ticket to the island", "Bought new shoes online", "Purchased a designer bag", 
            "Online shopping for clothes", "Bought a new jacket at the mall", "Purchased a smartphone accessory", 
            "Bought electronics from a store", "Shopping spree at a department store", "Bought a new pair of jeans", 
            "Purchased a watch", "Bought home decor items", "Subscribed to an online course", 
            "Bought textbooks for college", "Paid tuition fees", "Enrolled in a language course", 
            "Paid for a workshop", "Purchased educational software", "Registered for an online seminar", 
            "Bought study materials", "Paid for certification exam", "Subscribed to an academic journal", 
            "Movie night ticket", "Concert ticket purchase", "Attended a comedy show", 
            "Paid for streaming service subscription", "Bought a ticket for a theatre play", 
            "Went to a music festival", "Paid for a dance class", "Attended a sports game", 
            "Bought a video game", "Visited an amusement park", "Recharged my mobile phone", 
            "Bought a birthday gift for a friend", "Repaired a broken laptop", "Gym membership fee", 
            "Paid for a haircut", "Purchased office supplies", "Paid for a pet grooming session", 
            "Donated to charity", "Purchased a book", "Had a medical checkup"
        ],
        "type": ["Needs", "Wants", "Wants", "Wants", "Needs", "Needs", "Wants", "Needs", "Wants", "Wants",
                 "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs",
                 "Needs", "Wants", "Wants", "Needs", "Needs", "Wants", "Needs", "Wants", "Needs", "Wants",
                 "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants",
                 "Wants", "Needs", "Needs", "Wants", "Needs", "Needs", "Wants", "Needs", "Needs", "Wants",
                 "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants",
                 "Needs", "Wants", "Needs", "Wants", "Needs", "Needs", "Wants", "Wants", "Needs", "Needs"],
        "category": ["Food", "Food", "Food", "Food", "Food", "Food", "Food", "Food", "Food", "Food",
                     "Utilities", "Utilities", "Utilities", "Utilities", "Utilities", "Utilities", "Utilities", 
                     "Utilities", "Housing", "Housing", "Transport", "Transport", "Transport", "Transport", 
                     "Transport", "Transport", "Transport", "Transport", "Transport", "Transport", "Shopping", 
                     "Shopping", "Shopping", "Shopping", "Shopping", "Electronics", "Shopping", "Shopping", 
                     "Shopping", "Shopping", "Education", "Education", "Education", "Education", "Education", 
                     "Education", "Education", "Education", "Education", "Education", "Entertainment", 
                     "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment", 
                     "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment", 
                     "Utilities", "Gifts", "Electronics", "Fitness", "Personal Care", "Shopping", "Personal Care", 
                     "Charity", "Education", "Health"]
    }
    df = pd.DataFrame(data)
    vectorizer = CountVectorizer(stop_words="english")
    X = vectorizer.fit_transform(df["description"])
    
    # Train type classifier (for both Wants and Needs)
    y_type = df["type"]
    X_train_type, X_test_type, y_train_type, y_test_type = train_test_split(X, y_type, test_size=0.2, random_state=42)
    type_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    type_clf.fit(X_train_type, y_train_type)
    
    # Train general (Wants) category classifier
    y_cat = df["category"]
    X_train_cat, X_test_cat, y_train_cat, y_test_cat = train_test_split(X, y_cat, test_size=0.2, random_state=42)
    cat_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    cat_clf.fit(X_train_cat, y_train_cat)
    
    # Save the general models (used for Wants)
    with open("vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open("type_classifier.pkl", "wb") as f:
        pickle.dump(type_clf, f)
    with open("cat_classifier.pkl", "wb") as f:
        pickle.dump(cat_clf, f)

def train_needs_model():
    import pandas as pd
    from sklearn.model_selection import train_test_split
    
    # Use the same synthetic dataset as in the train_models function
    data = {
        "description": [
            "Bought milk and bread", "Ordered pizza online", "Had dinner at an Italian restaurant", 
            "Grabbed a coffee on the way", "Lunch at a local cafe", "Grocery shopping for vegetables and fruits", 
            "Dinner at a sushi bar", "Breakfast at a diner", "Snacked on chips", "Ordered takeout Chinese food", 
            "Paid electricity bill for this month", "Paid water bill", "Settled internet bill", 
            "Paid gas bill", "Paid cable TV subscription", "Received phone bill", "Paid heating bill", 
            "Paid property tax", "Monthly rent payment", "Paid maintenance fee for condo", 
            "Bought a monthly bus pass", "Uber ride to the airport", "Taxi fare from downtown", 
            "Subway ticket purchase", "Train ticket to the city", "Rented a car for a day", 
            "Bike sharing rental", "Paid for ride-sharing service", "Bus fare for school commute", 
            "Ferry ticket to the island", "Bought new shoes online", "Purchased a designer bag", 
            "Online shopping for clothes", "Bought a new jacket at the mall", "Purchased a smartphone accessory", 
            "Bought electronics from a store", "Shopping spree at a department store", "Bought a new pair of jeans", 
            "Purchased a watch", "Bought home decor items", "Subscribed to an online course", 
            "Bought textbooks for college", "Paid tuition fees", "Enrolled in a language course", 
            "Paid for a workshop", "Purchased educational software", "Registered for an online seminar", 
            "Bought study materials", "Paid for certification exam", "Subscribed to an academic journal", 
            "Movie night ticket", "Concert ticket purchase", "Attended a comedy show", 
            "Paid for streaming service subscription", "Bought a ticket for a theatre play", 
            "Went to a music festival", "Paid for a dance class", "Attended a sports game", 
            "Bought a video game", "Visited an amusement park", "Recharged my mobile phone", 
            "Bought a birthday gift for a friend", "Repaired a broken laptop", "Gym membership fee", 
            "Paid for a haircut", "Purchased office supplies", "Paid for a pet grooming session", 
            "Donated to charity", "Purchased a book", "Had a medical checkup"
        ],
        "type": ["Needs", "Wants", "Wants", "Wants", "Needs", "Needs", "Wants", "Needs", "Wants", "Wants",
                 "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs", "Needs",
                 "Needs", "Wants", "Wants", "Needs", "Needs", "Wants", "Needs", "Wants", "Needs", "Wants",
                 "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants",
                 "Wants", "Needs", "Needs", "Wants", "Needs", "Needs", "Wants", "Needs", "Needs", "Wants",
                 "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants", "Wants",
                 "Needs", "Wants", "Needs", "Wants", "Needs", "Needs", "Wants", "Wants", "Needs", "Needs"],
        "category": ["Food", "Food", "Food", "Food", "Food", "Food", "Food", "Food", "Food", "Food",
                     "Utilities", "Utilities", "Utilities", "Utilities", "Utilities", "Utilities", "Utilities", 
                     "Utilities", "Housing", "Housing", "Transport", "Transport", "Transport", "Transport", 
                     "Transport", "Transport", "Transport", "Transport", "Transport", "Transport", "Shopping", 
                     "Shopping", "Shopping", "Shopping", "Shopping", "Electronics", "Shopping", "Shopping", 
                     "Shopping", "Shopping", "Education", "Education", "Education", "Education", "Education", 
                     "Education", "Education", "Education", "Education", "Education", "Entertainment", 
                     "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment", 
                     "Entertainment", "Entertainment", "Entertainment", "Entertainment", "Entertainment", 
                     "Utilities", "Gifts", "Electronics", "Fitness", "Personal Care", "Shopping", "Personal Care", 
                     "Charity", "Education", "Health"]
    }
    df_full = pd.DataFrame(data)
    df_needs = df_full[df_full["type"] == "Needs"].reset_index(drop=True)
    
    vectorizer_needs = CountVectorizer(stop_words="english")
    X = vectorizer_needs.fit_transform(df_needs["description"])
    y_needs = df_needs["category"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y_needs, test_size=0.2, random_state=42)
    needs_cat_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    needs_cat_clf.fit(X_train, y_train)
    
    with open("vectorizer_needs.pkl", "wb") as f:
        pickle.dump(vectorizer_needs, f)
    with open("needs_cat_classifier.pkl", "wb") as f:
        pickle.dump(needs_cat_clf, f)

# Load models only once
_models = None

def get_models():
    global _models
    if _models is None:
        _models = load_models()
    return _models

def predict_expense_type(description):
    """Predict whether an expense is a 'Want' or a 'Need'."""
    models = get_models()
    vectorizer = models["vectorizer"]
    clf = models["type_classifier"]
    
    # Vectorize the description
    X = vectorizer.transform([description])
    
    # Predict the type
    prediction = clf.predict(X)[0]
    return prediction

def predict_expense_category(description):
    """Predict the category of an expense."""
    # First determine if it's a want or need
    expense_type = predict_expense_type(description)
    models = get_models()
    
    if expense_type == "Needs":
        # Use needs-specific classifier
        vectorizer = models["vectorizer_needs"]
        clf = models["needs_cat_classifier"]
    else:
        # Use general classifier
        vectorizer = models["vectorizer"]
        clf = models["cat_classifier"]
    
    # Vectorize the description
    X = vectorizer.transform([description])
    
    # Predict the category
    prediction = clf.predict(X)[0]
    return prediction
