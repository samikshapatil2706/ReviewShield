import os
import io
import csv
import time
import uuid

# Set single-threaded execution for OpenBLAS / OpenMP before importing scientific libraries
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import requests
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    send_file,
    Response
)

from predict import FakeReviewClassifier
import database
from blockchain import Blockchain
import review_provider


app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "mlbc_fake_review_secret_key"
)

# 5 MB maximum upload file limit
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

# Initialize ML Classifier, Database, and Blockchain
classifier = FakeReviewClassifier()
database.init_db()
blockchain = Blockchain()


# --------------------------------------------------
# Error Handlers
# --------------------------------------------------
@app.errorhandler(413)
def request_entity_too_large(error):
    msg = "Uploaded file exceeds the maximum permitted size limit of 5 MB."
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"error": msg}), 413
    flash(msg, "error")
    return redirect(url_for("bulk_analysis")), 413


# --------------------------------------------------
# 1. Home Page: Single Review Check
# --------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    provider_status = review_provider.get_provider_status()
    return render_template("index.html", provider_status=provider_status)


# --------------------------------------------------
# 2. Check a Single Review
# --------------------------------------------------
@app.route("/check", methods=["POST"])
def check_review():
    review_text = ""

    if request.is_json:
        data = request.get_json(silent=True) or {}
        review_text = data.get("review_text", "")
    else:
        review_text = request.form.get("review_text", "")

    if not isinstance(review_text, str):
        review_text = ""

    review_text = review_text.strip()

    if not review_text:
        err_msg = "Please enter valid, non-empty review text."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err_msg}), 400

        return render_template(
            "index.html",
            error=err_msg,
            provider_status=review_provider.get_provider_status()
        ), 400

    # Run ML prediction
    try:
        result = classifier.predict(review_text)
    except Exception as exc:
        app.logger.exception("Prediction failed for single review.")
        err_msg = f"Classification error: {exc}"
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err_msg}), 500
        return render_template("index.html", error=err_msg), 500

    # Save review to SQLite database
    review_id = database.insert_review(
        review_text=result["review_text"],
        cleaned_text=result["cleaned_text"],
        prediction=result["prediction"],
        is_suspicious=result["is_suspicious"],
        confidence=result["confidence"],
        source="single",
        in_blockchain=1
    )

    result["review_id"] = review_id

    # Record review in application blockchain
    block = blockchain.add_review_block(
        review_id=review_id,
        review_text=result["review_text"],
        prediction=result["prediction"],
        confidence=result["confidence"]
    )

    result["block_index"] = block.index
    result["block_hash"] = block.current_hash

    # Return JSON for AJAX/API requests
    if (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        return jsonify(result)

    # Return HTML for normal form submissions
    return render_template(
        "index.html",
        review_text=review_text,
        result=result,
        provider_status=review_provider.get_provider_status()
    )


# --------------------------------------------------
# 3. Bulk Review Analysis Using CSV
# --------------------------------------------------
@app.route("/analyze-csv", methods=["GET", "POST"])
@app.route("/bulk", methods=["GET"])
def bulk_analysis():
    if request.method == "GET":
        return render_template("bulk.html")

    # POST request handling CSV upload
    file = request.files.get("csv_file") or request.files.get("file")
    if not file or not file.filename:
        err = "No CSV file was selected. Please choose a valid .csv file."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    if not file.filename.lower().endswith(".csv"):
        err = "Invalid file type. Only standard CSV files (.csv) are accepted."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    # Read and decode file with multiple encoding fallbacks
    try:
        raw_bytes = file.read()
    except Exception as exc:
        err = f"Failed to read uploaded file: {exc}"
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    if len(raw_bytes) == 0:
        err = "The uploaded CSV file is empty (0 bytes)."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    if len(raw_bytes) > MAX_UPLOAD_SIZE:
        err = "The uploaded CSV file exceeds the 5 MB size limit."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 413
        flash(err, "error")
        return render_template("bulk.html"), 413

    # Decode bytes safely
    decoded_text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            decoded_text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        err = "Unable to decode CSV text. Please ensure the file is saved with UTF-8 encoding."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    # Parse CSV stream
    try:
        csv_stream = io.StringIO(decoded_text)
        reader = csv.reader(csv_stream)
        rows = list(reader)
    except Exception as exc:
        err = f"Malformed CSV structure: {exc}"
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    if not rows:
        err = "The uploaded CSV file does not contain any rows."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    # Header and column detection
    header = [c.strip().lower() for c in rows[0]]
    # Check for text_ or review_text or review or text
    target_col_idx = None
    candidate_cols = ["text_", "review_text", "review", "text", "reviewtext", "reviews"]
    for cand in candidate_cols:
        if cand in header:
            target_col_idx = header.index(cand)
            break

    if target_col_idx is None:
        err = (
            "Required review column missing! The CSV must contain either a "
            "'text_' column (as in the Kaggle dataset) or a 'review_text' column."
        )
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    # Extract review texts, skipping header
    data_rows = rows[1:]
    if not data_rows:
        err = "The CSV file contains column headers but no review data rows."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    extracted_reviews = []
    skipped_empty_count = 0

    for r in data_rows:
        if target_col_idx < len(r):
            val = r[target_col_idx].strip()
            if val:
                extracted_reviews.append(val)
            else:
                skipped_empty_count += 1
        else:
            skipped_empty_count += 1

    if not extracted_reviews:
        err = "No valid, non-empty review texts were found in the specified column."
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 400
        flash(err, "error")
        return render_template("bulk.html"), 400

    # Limit to maximum 1,000 reviews per upload
    max_limit = 1000
    was_truncated = False
    if len(extracted_reviews) > max_limit:
        extracted_reviews = extracted_reviews[:max_limit]
        was_truncated = True

    # Vectorized inference using predict_batch
    try:
        results = classifier.predict_batch(extracted_reviews)
    except Exception as exc:
        app.logger.exception("Bulk inference failed.")
        err = f"Inference execution error: {exc}"
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": err}), 500
        flash(err, "error")
        return render_template("bulk.html"), 500

    total_analyzed = len(results)
    suspicious_count = sum(1 for r in results if r["is_suspicious"])
    genuine_count = total_analyzed - suspicious_count
    genuine_pct = round((genuine_count / total_analyzed) * 100, 1) if total_analyzed > 0 else 0.0
    suspicious_pct = round((suspicious_count / total_analyzed) * 100, 1) if total_analyzed > 0 else 0.0
    avg_confidence = round(sum(r["confidence"] for r in results) / total_analyzed, 1) if total_analyzed > 0 else 0.0

    batch_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    # Optional auto-saving to SQLite and Blockchain from upload form checkboxes
    save_to_db = bool(request.form.get("save_to_db"))
    record_blockchain = bool(request.form.get("record_blockchain"))

    db_saved = False
    blockchain_recorded = False

    if save_to_db:
        try:
            saved_records = database.insert_reviews_batch(
                results,
                batch_id=batch_id,
                source="csv",
                in_blockchain=1 if record_blockchain else 0
            )
            # Update results with DB review IDs
            for i, r in enumerate(results):
                if i < len(saved_records):
                    r["review_id"] = saved_records[i]["id"]
            db_saved = True

            if record_blockchain:
                blockchain.add_review_blocks_batch(saved_records)
                blockchain_recorded = True
        except Exception as exc:
            app.logger.exception("Failed to auto-save CSV results to database/blockchain.")
            flash(f"Warning: Reviews analyzed successfully, but database persistence failed: {exc}", "warning")

    summary = {
        "batch_id": batch_id,
        "total_analyzed": total_analyzed,
        "genuine_count": genuine_count,
        "genuine_pct": genuine_pct,
        "suspicious_count": suspicious_count,
        "suspicious_pct": suspicious_pct,
        "avg_confidence": avg_confidence,
        "skipped_empty_count": skipped_empty_count,
        "was_truncated": was_truncated,
        "db_saved": db_saved,
        "blockchain_recorded": blockchain_recorded
    }

    if was_truncated:
        flash("Upload contained over 1,000 reviews. Analyzed the first 1,000 reviews.", "info")

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "summary": summary,
            "results": results
        }), 200

    return render_template(
        "bulk.html",
        results=results,
        summary=summary,
        batch_id=batch_id
    )


# --------------------------------------------------
# 4. Save Analyzed Batch to Database (Idempotent)
# --------------------------------------------------
@app.route("/save-batch-db", methods=["POST"])
def save_batch_db():
    payload = request.get_json(silent=True) or {}
    batch_id = payload.get("batch_id")
    reviews = payload.get("reviews", [])

    if not batch_id or not reviews:
        return jsonify({"error": "Missing batch_id or reviews data."}), 400

    try:
        saved_records = database.insert_reviews_batch(
            reviews,
            batch_id=batch_id,
            source="csv",
            in_blockchain=0
        )
        return jsonify({
            "success": True,
            "saved_count": len(saved_records),
            "batch_id": batch_id,
            "records": [{"id": r["id"], "prediction": r["prediction"]} for r in saved_records]
        }), 200
    except Exception as exc:
        app.logger.exception("Error saving batch to database.")
        return jsonify({"error": f"Database save error: {exc}"}), 500


# --------------------------------------------------
# 5. Record Analyzed Batch to Blockchain Ledger
# --------------------------------------------------
@app.route("/record-batch-blockchain", methods=["POST"])
def record_batch_blockchain():
    payload = request.get_json(silent=True) or {}
    batch_id = payload.get("batch_id")
    reviews = payload.get("reviews", [])

    # If review records are not passed directly, look up from DB by batch_id
    if not reviews and batch_id:
        reviews = database.get_reviews_by_batch_id(batch_id)

    if not reviews:
        return jsonify({
            "error": "No reviews found to record. Please ensure the batch is saved to the database first."
        }), 400

    formatted_data = []
    for r in reviews:
        formatted_data.append({
            "review_id": r.get("id", r.get("review_id", 0)),
            "review_text": r.get("review_text", ""),
            "prediction": r.get("prediction", "Unknown"),
            "confidence": float(r.get("confidence", 0.0))
        })

    try:
        blocks = blockchain.add_review_blocks_batch(formatted_data)
        return jsonify({
            "success": True,
            "recorded_blocks_count": len(blocks),
            "first_block_index": blocks[0].index if blocks else None,
            "last_block_index": blocks[-1].index if blocks else None,
            "message": f"Successfully minted {len(blocks)} immutable blocks in the blockchain ledger."
        }), 200
    except Exception as exc:
        app.logger.exception("Error recording batch blocks to blockchain.")
        return jsonify({"error": f"Blockchain recording error: {exc}"}), 500


# --------------------------------------------------
# 6. Export Analyzed Results to CSV Download
# --------------------------------------------------
@app.route("/export-analysis-csv", methods=["POST"])
def export_analysis_csv():
    payload = request.get_json(silent=True) or {}
    results = payload.get("results", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "review_id",
        "review_text",
        "cleaned_text",
        "prediction",
        "confidence_percentage",
        "is_suspicious"
    ])

    for idx, r in enumerate(results, 1):
        writer.writerow([
            r.get("review_id", idx),
            r.get("review_text", ""),
            r.get("cleaned_text", ""),
            r.get("prediction", ""),
            r.get("confidence", ""),
            r.get("is_suspicious", "")
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=analyzed_reviews.csv"
        }
    )


# --------------------------------------------------
# 7. Download Sample CSV for Testing
# --------------------------------------------------
@app.route("/sample-csv", methods=["GET"])
def download_sample_csv():
    sample_path = os.path.join("static", "sample_reviews.csv")
    if os.path.exists(sample_path):
        return send_file(sample_path, as_attachment=True, download_name="sample_reviews.csv")
    return "Sample CSV not found.", 404


# --------------------------------------------------
# 8. Analyze Reviews from a Product URL (Safe Provider Integration)
# --------------------------------------------------
@app.route("/analyze-product-url", methods=["POST"])
def analyze_product_url():
    data = request.get_json(silent=True) or {}
    product_url = data.get("product_url", "")

    if not isinstance(product_url, str) or not product_url.strip():
        return jsonify({
            "error": "Please enter a valid product URL."
        }), 400

    try:
        # Fetch reviews from the configured review provider API
        reviews = review_provider.fetch_reviews(
            product_url.strip(),
            limit=50
        )

        if not reviews:
            return jsonify({
                "error": "No reviews were returned by the review provider."
            }), 404

        results = classifier.predict_batch(reviews)

        suspicious_count = sum(
            1 for item in results
            if item["is_suspicious"]
        )
        genuine_count = len(results) - suspicious_count

        return jsonify({
            "product_url": product_url.strip(),
            "total_reviews": len(results),
            "genuine_count": genuine_count,
            "suspicious_count": suspicious_count,
            "results": results
        }), 200

    except ValueError as exc:
        return jsonify({
            "error": str(exc)
        }), 400

    except RuntimeError as exc:
        return jsonify({
            "error": str(exc),
            "is_unconfigured": True
        }), 503

    except requests.RequestException:
        app.logger.exception("Review provider API request failed.")
        return jsonify({
            "error": "Review provider API request failed. Check provider network settings and try again."
        }), 502

    except Exception:
        app.logger.exception("Unexpected error while analyzing product reviews.")
        return jsonify({
            "error": "An unexpected error occurred while analyzing product reviews."
        }), 500


# --------------------------------------------------
# 9. Review History
# --------------------------------------------------
@app.route("/history", methods=["GET"])
def history():
    reviews = database.get_all_reviews()
    return render_template(
        "history.html",
        reviews=reviews
    )


# --------------------------------------------------
# 10. Blockchain Ledger
# --------------------------------------------------
@app.route("/ledger", methods=["GET"])
def ledger():
    chain = blockchain.get_chain()
    return render_template(
        "ledger.html",
        chain=chain
    )


# --------------------------------------------------
# 11. Verify Review Integrity
# --------------------------------------------------
@app.route("/verify/<int:review_id>", methods=["GET"])
def verify_review(review_id):
    review = database.get_review_by_id(review_id)

    if not review:
        flash(f"Review #{review_id} not found in database.", "error")
        return redirect(url_for("history"))

    verification_result = blockchain.verify_review_integrity(
        review_id,
        review["review_text"]
    )

    reviews = database.get_all_reviews()

    return render_template(
        "history.html",
        reviews=reviews,
        verification_result=verification_result
    )


# --------------------------------------------------
# 12. Tamper with a Review (Testing Feature)
# --------------------------------------------------
@app.route("/tamper/<int:review_id>", methods=["POST"])
def tamper(review_id):
    review = database.get_review_by_id(review_id)

    if review:
        tampered_text = (
            review["review_text"]
            + " [TAMPERED DATA: ALTERED AFTER BLOCKCHAIN RECORDING!]"
        )

        database.tamper_review(
            review_id,
            tampered_text
        )

    return redirect(
        url_for("verify_review", review_id=review_id)
    )


# --------------------------------------------------
# 13. Restore a Review
# --------------------------------------------------
@app.route("/restore/<int:review_id>", methods=["POST"])
def restore(review_id):
    database.restore_review(review_id)

    return redirect(
        url_for("verify_review", review_id=review_id)
    )


# --------------------------------------------------
# Start Flask Server
# IMPORTANT: Keep app.run() at the very end
# --------------------------------------------------
if __name__ == "__main__":
    print(
        "Starting ReviewShield ML & Blockchain "
        "Web Server on http://127.0.0.1:5000"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
