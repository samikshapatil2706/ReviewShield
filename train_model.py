import os
import re

# Set single-threaded execution for OpenBLAS / OpenMP
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


def clean_text(text):
    """
    Standardize text: lowercase, strip URLs, encode exclamations,
    strip non-letters, and normalize spaces.
    Must remain consistent with inference preprocessing in predict.py.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'!', ' exclamationmark ', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def evaluate_or_train(retrain=False):
    """
    Evaluates the Fake Review model on the test split.
    If retrain=True, retrains and persists model & vectorizer artifacts.
    """
    data_path = os.path.join("data", "fake reviews dataset.csv")
    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Training dataset '{data_path}' not found!")

    print(f"Loading dataset from '{data_path}'...")
    # Using engine='python' to avoid C-parser memory allocation limits with long multiline quotes
    try:
        df = pd.read_csv(data_path, engine='python')
    except Exception:
        df = pd.read_csv(data_path)

    print(f"Loaded dataset dimensions: {df.shape[0]} rows, {df.shape[1]} columns")
    print("\nRaw Label Distribution:")
    print(df['label'].value_counts())

    # Map labels:
    # CG (Computer-Generated / Fake) -> 1 (Suspicious)
    # OR (Original / Human-Written)   -> 0 (Genuine)
    label_map = {'CG': 1, 'OR': 0}
    df['numeric_label'] = df['label'].map(label_map)
    df = df.dropna(subset=['numeric_label', 'text_'])

    print(f"Valid rows after dropping NA: {len(df)}")
    print("Mapped Class Distribution (0=Genuine, 1=Suspicious):")
    print(df['numeric_label'].value_counts())

    print("\nPreprocessing review text...")
    df['cleaned_text'] = df['text_'].apply(clean_text)

    X = df['cleaned_text']
    y = df['numeric_label'].astype(int)

    # 80/20 Stratified Split ensures identical class proportions in train & test
    print("Splitting train/test sets (80% train, 20% test, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model_path = os.path.join(models_dir, "logistic_model.pkl")
    vectorizer_path = os.path.join(models_dir, "tfidf_vectorizer.pkl")

    if not retrain and os.path.exists(model_path) and os.path.exists(vectorizer_path):
        print("\nLoading existing trained model & vectorizer for evaluation...")
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)
        X_test_tfidf = vectorizer.transform(X_test)
    else:
        print("\nExtracting TF-IDF features (max_features=15000, n-grams=(1,2), sublinear_tf=True)...")
        vectorizer = TfidfVectorizer(
            max_features=15000,
            ngram_range=(1, 2),
            stop_words='english',
            sublinear_tf=True
        )
        # Prevent data leakage: fit vectorizer strictly on training data
        X_train_tfidf = vectorizer.fit_transform(X_train)
        X_test_tfidf = vectorizer.transform(X_test)

        print("Fitting Logistic Regression classifier (C=2.0, max_iter=1000)...")
        model = LogisticRegression(C=2.0, max_iter=1000, random_state=42)
        model.fit(X_train_tfidf, y_train)

        # Save artifacts
        joblib.dump(model, model_path)
        joblib.dump(vectorizer, vectorizer_path)
        print(f"Saved trained model to '{model_path}'")
        print(f"Saved vectorizer to '{vectorizer_path}'")

    # Evaluate on independent test set
    y_pred = model.predict(X_test_tfidf)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)

    # Sanity check: ensure model does not predict only a single class
    unique_preds = np.unique(y_pred)
    if len(unique_preds) < 2:
        print("\n" + "!" * 60)
        print("WARNING: Model predicted only a single class across all test samples!")
        print("Check class balance and feature representation.")
        print("!" * 60)
    else:
        print("\nIntegrity Check: Model predicts both classes dynamically across the test set.")

    print("\n" + "=" * 60)
    print("            MODEL EVALUATION ON INDEPENDENT TEST SPLIT")
    print("=" * 60)
    print(f"Accuracy:  {acc * 100:.2f}%")
    print(f"Precision: {prec * 100:.2f}%")
    print(f"Recall:    {rec * 100:.2f}%")
    print(f"F1-Score:  {f1 * 100:.2f}%")
    print("\nConfusion Matrix (Rows=True, Columns=Predicted):")
    print(f"               Pred Genuine (0)   Pred Suspicious (1)")
    print(f"True Genuine     {cm[0][0]:<18} {cm[0][1]}")
    print(f"True Suspicious  {cm[1][0]:<18} {cm[1][1]}")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine (OR)", "Suspicious (CG)"]))
    print("=" * 60)
    print("\nNote: Retraining is only recommended when supported by evaluation evidence.")

    return {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "confusion_matrix": cm
    }


if __name__ == "__main__":
    import sys
    should_retrain = "--retrain" in sys.argv
    evaluate_or_train(retrain=should_retrain)
