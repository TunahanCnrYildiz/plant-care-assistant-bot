import json
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

def train_model():
    # 1. Load the dataset
    dataset_path = 'dataset.json'
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found!")
        return

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 2. Split data into features (X: questions) and targets (y: labels)
    questions = []
    labels = []
    
    for label, examples in dataset.items():
        for example in examples:
            questions.append(example.lower())  # Standardize by converting to lowercase
            labels.append(label)

    print(f"Loaded a total of {len(questions)} training examples.")
    print(f"Detected a total of {len(dataset.keys())} distinct classes (categories).")

    # 3. Vectorize text into numerical values (TF-IDF Vectorizer)
    # Use ngram_range=(1, 2) to capture unigrams and bigrams
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
    X = vectorizer.fit_transform(questions)
    y = labels

    # 4. Train the model (Logistic Regression)
    # Logistic Regression is highly effective for text classification and provides well-calibrated confidence scores.
    model = LogisticRegression(C=10.0, max_iter=200)  # C=10.0 helps prevent overfitting on small datasets
    model.fit(X, y)

    # Evaluate accuracy on training data
    accuracy = model.score(X, y) * 100
    print(f"Model successfully trained! Training set accuracy: %{accuracy:.2f}")

    # 5. Save the trained model and the vectorizer
    joblib.dump(model, 'model.joblib')
    joblib.dump(vectorizer, 'vectorizer.joblib')
    print("Saved model ('model.joblib') and vectorizer ('vectorizer.joblib') successfully!")

    # Perform a quick sample prediction for testing
    test_text = "çiçeğime ne sıklıkla su dökeyim"
    test_vector = vectorizer.transform([test_text.lower()])
    predicted_category = model.predict(test_vector)[0]
    
    # Get prediction probabilities
    probabilities = model.predict_proba(test_vector)[0]
    highest_probability = max(probabilities) * 100
    
    print("\n--- Sample Test Prediction ---")
    print(f"Test Question: '{test_text}'")
    print(f"Predicted Category: '{predicted_category}'")
    print(f"Confidence Score: %{highest_probability:.2f}")

if __name__ == "__main__":
    train_model()
