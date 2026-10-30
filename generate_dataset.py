import os
import random
import pandas as pd

# Set seed for reproducibility
random.seed(42)

# Templates for Genuine Reviews
genuine_reviews = [
    "I bought this wireless mouse two weeks ago. Battery life is decent, lasts about 3 days on heavy usage. Ergonomics are comfortable for desk work.",
    "The noise-canceling headphones work well on flights. Audio profile is slightly bass-heavy, but clear overall. Build quality feels sturdy.",
    "Decent smartphone for the price range. Screen brightness is great outdoors, though camera struggles in low light conditions.",
    "Setup was easy with the included manual. Connected to my Wi-Fi network right away. Recommending for home office setup.",
    "The keyboard switches feel tactile and responsive. Cable is braided and feels durable. Only minor downside is missing RGB backlighting.",
    "Good quality material on this backpack. Fits a 15-inch laptop securely with plenty of space for cables and notebooks.",
    "Used this blender for daily morning smoothies. It crushes ice smoothly, but motor can get quite loud.",
    "The monitor color accuracy is sharp after quick calibration. Stand is height-adjustable which helped my neck posture.",
    "The smart watch tracks steps accurately compared to my treadmill readings. Heart rate sensor is responsive during workouts.",
    "Arrived in secure packaging within 3 days. Product matches the description and performs as expected.",
    "The coffee maker brews fast and stays warm for an hour. Filter cleanup is straightforward.",
    "Solid external SSD with fast transfer speeds. Moved a 20GB video file in under a minute.",
    "The air purifier is quiet on night mode. Dust levels in bedroom noticeably reduced after a week of operation.",
    "Ergonomic chair provides good lumbar support for long working sessions. Assembly took about 30 minutes.",
    "Water bottle keeps drinks cold all day even in hot car. Seal is leakproof as advertised.",
    "The desk lamp has multiple color temperatures and brightness levels. USB charging port on base is very convenient.",
    "Good soundbar for small living room setup. Dialogue is clear in movies, though subwoofer bass could be punchier.",
    "Power bank charged my phone twice on a single charge. Compact design makes it easy to carry in pocket.",
    "Action camera records crisp 4K video. Stabilization works great while biking on rough trails.",
    "Smooth writing experience with these gel pens. Ink doesn't smudge on standard notebook paper.",
    "The bluetooth speaker connects quickly and battery lasts through an entire afternoon barbecue. Volume is surprisingly loud for its size.",
    "Laptop stand raises screen to eye level comfortably. Aluminum frame feels solid and doesn't wobble while typing.",
    "Webcam resolution is clear for Zoom meetings. Built-in microphone is acceptable, though dedicated mic is better.",
    "Cooking pan heats evenly without hot spots. Non-stick coating holds up well after two months of hand washing.",
    "Running shoes are lightweight and cushion impact nicely. Sizing runs half a size small, so consider ordering up."
]

# Templates for Suspicious / Fake Reviews (Spam, Exaggerated Hype, Clickbait, Unrealistic Hyperbole)
suspicious_reviews = [
    "BEST PRODUCT EVER IN THE WORLD!!! BUY NOW AMAZING DISCOUNTS CLICK HERE FOR FREE GIFTS AND HUGE SAVINGS!! MUST BUY TODAY!!",
    "AMAZING AMAZING AMAZING!! 1000% RECOMMENDED!! BEST SELLER WIN FREE IPHONE BY PURCHASING THIS AMAZING ITEM NOW!!",
    "DO NOT MISS THIS ONCE IN A LIFETIME DEAL!! CHEAPEST PRICE GUARANTEED VISIT WWW.SPAMOFFER.COM TO CLAIM REWARD POINTS IMMEDIATELY!",
    "Item arrived broken. Completely useless trash. Terrible seller stole my money do not buy scam scam scam seller!!",
    "Great product high quality very fast shipping I love it so much five stars highly recommended best seller product nice.",
    "BUY THIS PRODUCT NOW OR YOU WILL REGRET IT!! UNBELIEVABLE QUALITY FREE MONEY BACK GUARANTEE CLICK LINK NOW!!",
    "Works great good seller smooth transaction quick delivery top quality A+++++ seller will buy again highly recommended.",
    "SUPER FAST DELIVERY BEST QUALITY ITEM EVER MADE WOW WOW WOW SO HAPPY BUY NOW BUY NOW BUY NOW!!",
    "SCAM WARNING DO NOT BUY THIS ITEM IS TOTAL GARBAGE SELLER IS A FRAUD CHEATER CHEATER CHEATER FRAUDULENT PRODUCT!!",
    "This product cured all my problems instantly overnight! Magic results 100% real no fake guaranteed call 1800-SPAM now!",
    "EARN FREE COUPONS BY LEAVING 5 STAR REVIEW! BEST PRODUCT ON AMAZON EVERYONE MUST BUY 10 OF THESE RIGHT NOW!!",
    "Five stars very good item fantastic seller quick ship high quality good price like it very much product best.",
    "UNBELIEVABLE MIRACLE PRODUCT! CHANGE YOUR LIFE TODAY SPECIAL PROMO OFFER EXPIRING IN 5 MINUTES GO TO OUR SITE NOW!",
    "Fake product fake reviews do not trust this store money waste terrible awful horizontal garbage scam artist!!",
    "WONDERFUL AMAZING FANTASTIC SUPERB EXCELLENT MAGNIFICENT UNBELIEVABLE MAGICAL BEST ITEM EVER PROMOTIONAL OFFER!",
    "Get 90% discount right now!! Best price on the internet free shipping worldwide visit spam link in bio now!!",
    "Very nice item best quality high satisfaction 10/10 product excellent buy again recommend to all friends and family.",
    "ULTIMATE GAMING GEAR 10000 FPS BOOST NO LAG WIN EVERY GAME GUARANTEED INSTANT DOWNLOAD CHEAT CODE OFFER!",
    "DO NOT BUY TOTAL RIPOFF WORST EXPERIENCE OF MY LIFE FAKE PICTURES FAKE DESCRIPTION LIAR SELLER TERRIBLE!!",
    "CLICK HERE TO WIN $1000 GIFT CARD! LEAVE 5 STAR RATING AND CLAIM YOUR CASH PRIZE TODAY PROMO CODE WINNER!",
    # Exaggerated Fake Hype & Unrealistic Enthusiast Templates
    "This is the best product in the entire universe! Greatest invention in human history! Works faster than a rocket and makes everything taste like magic!",
    "I don't know how I ever lived without this! If you don't buy this right now you are missing out on the greatest invention ever made!",
    "ABSOLUTELY LIFE CHANGING MAGICAL INVENTION!! BEST ITEM EVER CREATED IN HUMAN HISTORY PERFECT PERFECT PERFECT!!",
    "This changed my life forever overnight! Magic results unbelievable perfection everyone in the world must buy 100 of these right now!!",
    "Works faster than a rocket! Pure magic! Mind blowing incredible unbelievable greatest purchase of my life!",
    "If you don't buy this right now you are making the biggest mistake of your life! Miracle item of the century!"
]

def generate_dataset(num_samples_per_class=400, output_path="data/reviews.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    data = []
    
    # Generate Genuine Samples (label = 0)
    for i in range(num_samples_per_class):
        base_review = random.choice(genuine_reviews)
        if random.random() < 0.3:
            second_review = random.choice(genuine_reviews)
            combined = f"{base_review} {second_review}"
        else:
            combined = base_review
        data.append({"review_text": combined, "label": 0, "label_name": "Genuine"})

    # Generate Suspicious Samples (label = 1)
    for i in range(num_samples_per_class):
        base_review = random.choice(suspicious_reviews)
        if random.random() < 0.3:
            second_review = random.choice(suspicious_reviews)
            combined = f"{base_review} {second_review}"
        else:
            combined = base_review
        data.append({"review_text": combined, "label": 1, "label_name": "Suspicious"})
        
    df = pd.DataFrame(data)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df.to_csv(output_path, index=False)
    print(f"Dataset successfully created at '{output_path}' with {len(df)} records ({num_samples_per_class} Genuine, {num_samples_per_class} Suspicious).")
    return df

if __name__ == "__main__":
    generate_dataset()
