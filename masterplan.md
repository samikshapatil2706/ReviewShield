# Masterplan — Fake Review Detection + Blockchain

## 1. App Overview

A small college mini-project that detects potentially fake/suspicious **product reviews** using traditional machine learning and then stores a tamper-evident record of the review using a simple blockchain structure.

The project is designed for a **single-user college demonstration**, not as a production or commercial review platform.

### Main flow

Product review
→ Text preprocessing
→ TF-IDF
→ Logistic Regression
→ Genuine / Suspicious + confidence
→ Generate review hash
→ Store blockchain record
→ Allow later verification

## 2. Objectives

- Demonstrate a practical use of **machine learning for text classification**.
- Demonstrate how **TF-IDF and Logistic Regression** can classify review text.
- Show the model's predicted probability as a confidence value.
- Demonstrate how hashing can identify changes to a stored review.
- Demonstrate a simple blockchain structure where blocks are linked using hashes.
- Show how ML and blockchain can work together without making either component unnecessarily complex.

## 3. Target Audience

The primary audience is the **college faculty/examiner** evaluating the mini-project.

There is no requirement for multiple real users, public deployment, or commercial-scale infrastructure.

## 4. Core Features

### A. Check Review
- User enters a product review.
- User clicks **Check Review**.
- The system preprocesses the text.
- TF-IDF converts the text into numerical features.
- Logistic Regression predicts **Genuine** or **Suspicious**.
- The application displays the prediction and model probability/confidence.
- A blockchain record is created for the submitted review.

### B. Review History
- Display previously submitted reviews.
- Show Review ID, prediction, confidence, timestamp, and relevant hash information.
- Allow a selected review to be verified against its blockchain record.

### C. Blockchain Verification
- Recalculate the hash of the current review.
- Compare it with the hash recorded in the blockchain.
- If they match, show that the record is consistent.
- If they do not match, show that the record has been modified.

### D. Simulate Tampering
A clearly labelled demonstration/testing feature can temporarily modify a selected review.

The system then recalculates its hash and demonstrates that the modified review no longer matches the original blockchain record.

This is for demonstration only and is not a normal user feature.

## 5. ML Design

### Training approach

Use a suitable **publicly available labelled product-review dataset** containing examples that can be used for genuine/fake or equivalent binary classification.

### Planned pipeline

1. Collect/load the labelled dataset.
2. Perform basic text preprocessing.
3. Convert review text into TF-IDF features.
4. Train a Logistic Regression classifier.
5. Evaluate the model using appropriate classification metrics.
6. Save the trained model and TF-IDF representation for use by the application.
7. Use the model to classify new submitted reviews.

### Basic preprocessing

Keep preprocessing intentionally simple:

- Lowercase text
- Remove unnecessary punctuation/noise
- Tokenize text
- Remove common stop words where appropriate
- Apply TF-IDF

Avoid deep-learning or transformer models because they are outside the intended scope of this mini-project.

### Important limitation

The system should present the result as a **model prediction**, not as absolute proof that a review is fake. A model trained on a particular dataset may not generalize perfectly to every type of product review.

## 6. Blockchain Design

Use a **simple application-level blockchain**, not a public cryptocurrency network.

Each block can conceptually contain:

- Block/index ID
- Review ID
- User ID
- Review hash
- Timestamp
- ML classification
- ML confidence
- Previous block hash
- Current block hash

The actual review text is kept separately rather than being stored directly in the blockchain.

### Why hashing is used

A hash acts as a fingerprint of the review. If the review changes, its calculated hash should also change.

The blockchain preserves the original hash and links blocks together, making unauthorized modification detectable.

### Important limitation

This is a **demonstration blockchain**, not a decentralized production blockchain. It does not provide the same properties as a distributed public blockchain network.

## 7. Data Storage

### Recommended: SQLite

SQLite will provide lightweight local storage for application data.

Conceptually, the database can maintain:

- Reviews
- Review metadata
- Predictions
- Confidence values
- Timestamps
- Blockchain-related references

The blockchain structure itself can also be persisted locally if needed.

No cloud database or database server is required.

## 8. User Interface

### Page 1 — Check Review

Simple interface containing:

- Product review text box
- **Check Review** button
- Prediction result
- Confidence/probability
- Blockchain record status

Example result:

> Prediction: Suspicious  
> Confidence: 87%  
> Blockchain Record: Created

### Page 2 — Review History

Show:

- Review ID
- Review text or controlled display of it
- Prediction
- Confidence
- Timestamp
- Hash/record information
- Verify action

The verification result should clearly communicate whether the current review matches the recorded hash.

## 9. High-Level Technical Stack

### Frontend / Web Interface
A lightweight Python-friendly web framework is recommended.

**Recommendation:** Flask.

- Simple for a small project.
- Easy to connect with the ML model and SQLite.
- Minimal overhead.

A larger framework such as Django is possible, but would add unnecessary structure for this mini-project.

### Machine Learning
- Python
- scikit-learn
- TF-IDF
- Logistic Regression

### Data Storage
- SQLite

### Blockchain
- Custom/simple blockchain logic implemented as an application component.
- Cryptographic hashing for record integrity.

### Deployment
Local laptop deployment is sufficient for the college demonstration.

## 10. Conceptual Data Model

### Review

- Review ID
- User ID
- Review text
- Prediction
- Confidence
- Timestamp
- Blockchain reference/hash

### Blockchain Block

- Block ID
- Review ID
- Review hash
- Timestamp
- Classification
- Confidence
- Previous block hash
- Current block hash

The relationship is conceptually:

**Review → Hash → Blockchain Block**

## 11. Security and Integrity Considerations

- Do not store unnecessary personal information.
- Use cryptographic hashing for review integrity.
- Validate review input before processing.
- Keep the blockchain verification process deterministic.
- Clearly separate ML classification from blockchain record-keeping.
- Do not claim that blockchain itself proves a review is genuine.
- Do not present the ML prediction as guaranteed truth.

## 12. Development Phases

### Phase 1 — Dataset and ML
- Select an appropriate public product-review dataset.
- Clean and inspect the data.
- Build the basic preprocessing pipeline.
- Train Logistic Regression with TF-IDF.
- Evaluate the classifier.

### Phase 2 — Application
- Create the simple web interface.
- Connect the trained ML model.
- Accept a review and display prediction/confidence.

### Phase 3 — SQLite
- Store submitted reviews and results.
- Implement review history.

### Phase 4 — Blockchain
- Create the simple block structure.
- Generate review hashes.
- Link blocks using previous/current hashes.
- Store relevant blockchain metadata.

### Phase 5 — Verification
- Recalculate review hashes.
- Compare them with recorded hashes.
- Add the controlled **Simulate Tampering** demonstration.

### Phase 6 — Testing and Demonstration
- Test genuine and suspicious examples.
- Test blockchain verification.
- Test tampering detection.
- Prepare a short demonstration explaining the ML → hash → blockchain flow.

## 13. Potential Challenges and Solutions

### Challenge: Dataset quality
**Solution:** Choose a clearly labelled public dataset and document its source and limitations.

### Challenge: ML accuracy
**Solution:** Start with TF-IDF + Logistic Regression and evaluate it properly. Avoid promising perfect detection.

### Challenge: Confidence interpretation
**Solution:** Display the classifier's predicted probability and describe it as model confidence/probability, not guaranteed truth.

### Challenge: Blockchain becoming unnecessarily complicated
**Solution:** Use a simple local blockchain rather than Ethereum, wallets, smart contracts, or public networks.

### Challenge: Demonstrating tampering
**Solution:** Include the controlled Simulate Tampering feature so the examiner can see hash mismatch directly.

### Challenge: Scope becoming too large
**Solution:** Keep the project limited to product reviews, one user, local storage, one ML model, and a simple blockchain.

## 14. Out of Scope

To keep this a true mini-project, do not initially include:

- User registration/login
- Multiple user roles
- Real cryptocurrency
- Public blockchain deployment
- Smart contracts
- Payment systems
- Mobile application
- Advanced deep-learning models
- Real-time review scraping
- Large-scale cloud deployment
- Commercial moderation system

## 15. Future Expansion

If the project is later extended, possible additions include:

- Multiple product categories
- Better NLP models
- Additional fake-review signals such as rating patterns or review frequency
- Explainable ML features
- Real blockchain networks
- Smart contracts
- Multiple users and authentication
- Admin dashboard
- Cloud deployment
- Larger and more diverse datasets

## 16. Final Demonstration Story

The complete demonstration should be understandable in a few steps:

1. Enter a product review.
2. Click **Check Review**.
3. Show the ML prediction and confidence.
4. Show that a blockchain record was created.
5. Open **Review History**.
6. Verify the review and show a successful hash match.
7. Use **Simulate Tampering**.
8. Verify again.
9. Show that the modified review produces a different hash and verification fails.

### Core message

**Machine learning detects suspicious review patterns; blockchain provides a tamper-evident record of what was submitted and what the model classified.**

This separation of responsibilities is the central idea of the project.
