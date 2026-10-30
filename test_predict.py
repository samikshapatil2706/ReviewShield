from predict import FakeReviewClassifier

classifier = FakeReviewClassifier()

review_text = "This is the best blender in the entire universe! I’ve been blending every single meal since I bought it last week — smoothies, soups, even ice cream! It works faster than a rocket and makes everything taste like magic. I don’t know how I ever lived without it. If you don’t buy this right now, you’re missing out on the greatest invention in human history!"

res = classifier.predict(review_text)

print("="*60)
print("TEST PREDICTION RESULT FOR EXAGGERATED REVIEW:")
print("Prediction:  ", res['prediction'])
print("Confidence:  ", res['confidence'], "%")
print("Cleaned Text:", res['cleaned_text'])
print("="*60)
