# ReviewShield ML & Blockchain — Product Review Spam & Fraud Detection

An academic mini-project demonstrating **Machine Learning for Text Spam Classification** combined with an **Application-Level Blockchain Ledger for Cryptographic Integrity & Tamper Evidence**.

---

## 1. Project Overview

E-commerce platforms frequently encounter fraudulent, computer-generated, and incentivized fake reviews that distort buyer decisions. Simultaneously, centralized databases can suffer from undetected manual edits or data tampering.

**ReviewShield ML & Blockchain** addresses both challenges through a dual-layer architecture:
1. **Machine Learning Layer:** Extracts n-gram TF-IDF representations from product review text and applies a trained Logistic Regression classifier to determine if a review is **Genuine** or **Suspicious**, providing a probability-based confidence score.
2. **Blockchain Integrity Layer:** Generates a deterministic SHA-256 cryptographic digest (digital fingerprint) of each submitted review and classification decision, appending it to a chronologically linked block in an application blockchain. Any subsequent alteration of stored records in SQLite triggers an immediate cryptographic mismatch alert upon verification.

> **Key Distinction for Academic Viva:**  
> **Machine learning identifies suspicious text patterns based on training distributions; blockchain does not classify text, but provides an immutable audit trail proving whether stored review records have been altered post-classification.**

---

## 2. System Architecture & Features

### Core Modules
* **`app.py`** — Flask web application providing web interfaces, CSV analysis endpoints, history, and verification routes.
* **`predict.py`** — Feature extraction and inference logic via `FakeReviewClassifier`, supporting single review inference and high-throughput batch inference (`predict_batch`).
* **`train_model.py`** — Model training and rigorous evaluation pipeline on Kaggle dataset (40,432 reviews) reporting accuracy, precision, recall, F1, and confusion matrix.
* **`database.py`** — SQLite database operations with backward-compatible migrations, idempotent batch inserts, and tamper/restore testing routines.
* **`blockchain.py`** — Application-level SHA-256 linked blockchain (genesis block, sequential linking, batch minting, and cryptographic verification).
* **`review_provider.py`** — Authorized external review API client featuring comprehensive Server-Side Request Forgery (SSRF) defense, domain allowlisting, and environment credential management.
* **`docs/PROVIDER_SETUP.md`** — Step-by-step setup documentation for authorized e-commerce review providers.
* **`static/sample_reviews.csv`** — Pre-packaged 20-sample review dataset for 1-click viva demonstrations.

---

## 3. Preserved Routes & Capabilities

All existing project routes and behaviors are strictly preserved:

| Route | Method | Purpose |
| :--- | :--- | :--- |
| `/` | `GET` | Home page for single review analysis and live URL analysis |
| `/check` | `POST` | Single review check: ML classification + SQLite storage + Blockchain block minting |
| `/analyze-csv` / `/bulk` | `GET`, `POST` | **New Feature:** Bulk Review Analysis via CSV upload (up to 1,000 reviews, 5 MB limit) |
| `/save-batch-db` | `POST` | Idempotent saving of analyzed CSV batches to SQLite database |
| `/record-batch-blockchain` | `POST` | Optional batch recording of analyzed reviews to the application blockchain |
| `/export-analysis-csv` | `POST` | Download analyzed batch results as a clean CSV file |
| `/sample-csv` | `GET` | Download sample CSV for quick viva testing |
| `/analyze-product-url` | `POST` | Product URL analysis via authorized provider API with strict SSRF protection |
| `/history` | `GET` | Review history table with source badges (Single/CSV) and blockchain status |
| `/ledger` | `GET` | Immutable blockchain ledger displaying linked SHA-256 blocks |
| `/verify/<review_id>` | `GET` | Cryptographic verification of SQLite review text against blockchain block |
| `/tamper/<review_id>` | `POST` | Demonstration feature: Simulates unauthorized database modification |
| `/restore/<review_id>` | `POST` | Demonstration feature: Restores review to original authentic state |

---

## 4. Machine Learning Model & Evaluation

The classifier is trained on the Kaggle Fake Reviews Dataset comprising **40,432 labeled product reviews**:
* **`OR` (Original / Genuine):** 20,216 samples (Mapped to label `0`)
* **`CG` (Computer Generated / Suspicious):** 20,216 samples (Mapped to label `1`)

### Preprocessing Pipeline:
1. Lowercasing
2. URL pattern removal
3. Exclamation mark normalization (`!` $\rightarrow$ ` exclamationmark `)
4. Non-alphabetic character stripping
5. Whitespace normalization
6. Sublinear TF-IDF feature extraction (15,000 max features, unigrams and bigrams, English stop words)

### Empirical Evaluation Results (Independent 20% Test Split — 8,087 Reviews):
```text
============================================================
            MODEL EVALUATION ON INDEPENDENT TEST SPLIT
============================================================
Accuracy:  90.31%
Precision: 90.73%
Recall:    89.78%
F1-Score:  90.25%

Confusion Matrix (Rows=True, Columns=Predicted):
               Pred Genuine (0)   Pred Suspicious (1)
True Genuine     3673               371
True Suspicious  413                3630

Detailed Classification Report:
                 precision    recall  f1-score   support

   Genuine (OR)       0.90      0.91      0.90      4044
Suspicious (CG)       0.91      0.90      0.90      4043

       accuracy                           0.90      8087
      macro avg       0.90      0.90      0.90      8087
   weighted avg       0.90      0.90      0.90      8087
============================================================
```

> **Viva Note on Confidence vs. Accuracy:**  
> The confidence percentage displayed in the UI represents the model's posterior probability (via `predict_proba`) for the assigned class. It measures how strongly the TF-IDF feature vector aligns with the class hyperplane in Logistic Regression, not absolute factual accuracy.

---

## 5. Bulk Review Analysis Using CSV

The new Bulk Review Analysis feature provides high-throughput processing:
1. **Upload Constraints:** Up to 1,000 reviews per file; file size restricted to 5 MB.
2. **Flexible Column Recognition:** Supports both `text_` (Kaggle dataset format) and `review_text` (standard CSV format), as well as `review` and `text`.
3. **Robust Cleansing:** Auto-detects UTF-8, UTF-8-BOM, and Latin-1; filters empty or whitespace-only rows with a reported counter.
4. **Vectorized Inference:** Uses `predict_batch` to classify hundreds of reviews in milliseconds.
5. **Interactive UI:**
   - Summary stat cards (Total Analyzed, Genuine Count & %, Suspicious Count & %, Average Confidence).
   - Filter pills (`All`, `Genuine`, `Suspicious`).
   - Live search box to filter reviews by keyword.
   - Client-side pagination (10, 25, 50, 100 per page).
   - Export Analyzed Results to CSV.
   - Optional 1-click database saving and blockchain minting.
   - Strict XSS protection: review texts are escaped safely and never rendered as executable HTML.

---

## 6. Product URL Analysis & SSRF Security

The `/analyze-product-url` endpoint implements enterprise-grade security controls:
* **SSRF Defense:** Only HTTPS URLs are permitted. Direct IP addresses (including cloud metadata `169.254.169.254` and private networks `10.x`, `192.168.x`), localhost, and non-standard ports (e.g., `:8080`, `:22`) are strictly blocked.
* **Domain Allowlist:** Restricts requests to authorized e-commerce domains (`amazon.in`, `amazon.com`, `flipkart.com`).
* **Authorized Provider API:** Rather than performing fragile or unauthorized web scraping, ReviewShield connects to an authorized third-party Review Provider API using environment credentials (`REVIEW_PROVIDER_ENDPOINT` and `REVIEW_PROVIDER_API_KEY`).
* **Graceful Fallback:** If the provider is not configured, the UI clearly displays the unconfigured status and guides users to the Bulk CSV Upload feature.

---

## 7. How to Run the Project

### Prerequisites
* Python 3.11+ (Python 3.12 / 3.13 / 3.14 compatible)
* Required packages: `flask`, `scikit-learn`, `joblib`, `pandas`, `numpy`, `requests`

### Step 1: Start the Web Application
```powershell
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

### Step 2: Run Evaluation on Test Data
```powershell
python train_model.py
```
Outputs the full confusion matrix, precision, recall, and F1-score on the independent test set.

### Step 3: Run Prediction Smoke Test
```powershell
python test_predict.py
```

---

## 8. College Project Viva Demonstration Guide

Follow this step-by-step walkthrough during your evaluation:

1. **Demonstrate Single Review Classification (`/`):**
   - Click the **"✓ Genuine (Mouse)"** sample button and click **"Classify & Record to Blockchain"**.
   - Show the result: `Genuine Review`, high confidence percentage, preprocessed cleaned text, and the minted blockchain block index & SHA-256 hash.
   - Click the **"⚠️ Suspicious (Promo Spam)"** sample button to demonstrate classification of spam/incentivized review text.
2. **Demonstrate Bulk Review Analysis (`/analyze-csv`):**
   - Click **"📥 Download Test Sample CSV"** or upload `static/sample_reviews.csv`.
   - Leave *"Automatically save analysis batch to SQLite database"* checked.
   - Click **"Analyze CSV Reviews"**.
   - Show the metric cards: Total Analyzed (20), Genuine count, Suspicious count, and Average Confidence.
   - Use the filter buttons (`All`, `Genuine`, `Suspicious`) and type in the live search box.
   - Click **"Export CSV"** to demonstrate downloading the analyzed dataset.
3. **Demonstrate Blockchain Integrity & Tamper Detection (`/history`):**
   - Open **Review History**.
   - Click **"🔒 Verify"** on any review: Show the green **"Blockchain Verification Succeeded: Integrity Intact"** alert with matching SHA-256 hashes.
   - Click **"⚠️ Tamper"** on that review: Show how SQLite text is altered with `[TAMPERED DATA]`.
   - Notice the red alert: **"🚨 DATA TAMPERING DETECTED! Cryptographic Mismatch"**. Explain to the examiner that recalculating the SHA-256 hash from the modified SQLite row produces a hash that does not match the block hash recorded at submission.
   - Click **"↩️ Restore"** and show that the record returns to verified status.
4. **Inspect the Blockchain Ledger (`/ledger`):**
   - Show the sequential chain of blocks, from Genesis Block #0 to the latest minted block.
   - Explain how `previous_hash` cryptographically links each block to the preceding block.
