import os
import re

# Set single-threaded execution for OpenBLAS / OpenMP to ensure stability across platforms
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import joblib


def clean_text(text):
    """
    Standardize review text for inference and training:
    - Lowercase
    - Remove URL patterns
    - Expand exclamation marks to token representations
    - Remove non-alphabetic characters
    - Normalize whitespace
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'!', ' exclamationmark ', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class FakeReviewClassifier:
    """
    Product Review Classifier utilizing TF-IDF feature extraction
    and Logistic Regression.
    """

    def __init__(
        self,
        model_path="models/logistic_model.pkl",
        vectorizer_path="models/tfidf_vectorizer.pkl"
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model artifact missing at '{model_path}'. "
                "Please run `train_model.py` to train and save the model."
            )
        if not os.path.exists(vectorizer_path):
            raise FileNotFoundError(
                f"TF-IDF vectorizer artifact missing at '{vectorizer_path}'. "
                "Please run `train_model.py` to extract features and save the vectorizer."
            )

        try:
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load ML artifacts from disk: {exc}"
            ) from exc

    def predict(self, review_text):
        """
        Classifies a single review string.
        Returns prediction, probability-based confidence, and cleaned text.
        """
        if review_text is None or not isinstance(review_text, str) or not review_text.strip():
            raise ValueError("Review text cannot be empty or invalid.")

        cleaned = clean_text(review_text)
        features = self.vectorizer.transform([cleaned])

        pred_label = int(self.model.predict(features)[0])  # 0: Genuine, 1: Suspicious
        probabilities = self.model.predict_proba(features)[0]  # [prob_0, prob_1]

        confidence = float(probabilities[pred_label])
        prediction_str = "Suspicious" if pred_label == 1 else "Genuine"

        return {
            "review_text": review_text,
            "cleaned_text": cleaned,
            "prediction": prediction_str,
            "is_suspicious": bool(pred_label == 1),
            "confidence": round(confidence * 100, 2),
            "raw_probability": round(confidence, 4),
            "explanation": (
                "Confidence reflects the classifier's predicted probability "
                "for the assigned class, which is distinct from model test accuracy."
            )
        }

    def predict_batch(self, review_texts):
        """
        Performs vectorized inference on a list of review texts for high performance.
        Returns a list of prediction dictionaries.
        """
        if not review_texts:
            return []

        cleaned_texts = []
        valid_indices = []

        for idx, text in enumerate(review_texts):
            if isinstance(text, str) and text.strip():
                cleaned = clean_text(text)
                cleaned_texts.append(cleaned)
                valid_indices.append(idx)

        if not cleaned_texts:
            return []

        features = self.vectorizer.transform(cleaned_texts)
        preds = self.model.predict(features)
        probs = self.model.predict_proba(features)

        results = []
        for i, original_idx in enumerate(valid_indices):
            pred_label = int(preds[i])
            conf = float(probs[i][pred_label])
            prediction_str = "Suspicious" if pred_label == 1 else "Genuine"

            results.append({
                "review_text": review_texts[original_idx],
                "cleaned_text": cleaned_texts[i],
                "prediction": prediction_str,
                "is_suspicious": bool(pred_label == 1),
                "confidence": round(conf * 100, 2),
                "raw_probability": round(conf, 4),
                "explanation": (
                    "Confidence reflects the classifier's predicted probability "
                    "for the assigned class, which is distinct from model test accuracy."
                )
            })

        return results


if __name__ == "__main__":
    import sys

    try:
        classifier = FakeReviewClassifier()
        test_str = (
            "This is the best blender in the entire universe! I’ve been blending every "
            "single meal since I bought it last week — smoothies, soups, even ice cream! "
            "It works faster than a rocket and makes everything taste like magic. "
            "I don’t know how I ever lived without it. If you don’t buy this right now, "
            "you’re missing out on the greatest invention in human history!"
        )
        if len(sys.argv) > 1:
            test_str = " ".join(sys.argv[1:])
        res = classifier.predict(test_str)
        print("Single Prediction Result:")
        for k, v in res.items():
            print(f"  {k}: {v}")

        print("\nBatch Prediction Test (2 samples):")
        batch_res = classifier.predict_batch([
            "Great wireless mouse, battery lasts 3 days as advertised.",
            "BUY NOW CLICK HERE FREE IPHONE WINNER 1000% BEST PRODUCT EVER!!"
        ])
        for idx, r in enumerate(batch_res, 1):
            print(f"  Sample {idx}: {r['prediction']} ({r['confidence']}%)")

    except Exception as e:
        print(f"Classifier error: {e}")
