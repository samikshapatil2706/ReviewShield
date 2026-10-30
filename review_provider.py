import os
import ipaddress
from urllib.parse import urlsplit
import requests


def get_allowed_hosts():
    raw = os.getenv("ALLOWED_PRODUCT_HOSTS", "amazon.in,amazon.com,flipkart.com")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def is_provider_configured():
    """
    Checks whether the review provider endpoint and API key environment variables are set.
    """
    endpoint = os.getenv("REVIEW_PROVIDER_ENDPOINT", "").strip()
    api_key = os.getenv("REVIEW_PROVIDER_API_KEY", "").strip()
    return bool(endpoint and api_key)


def get_provider_status():
    """
    Returns non-sensitive metadata about provider configuration status.
    """
    endpoint = os.getenv("REVIEW_PROVIDER_ENDPOINT", "").strip()
    api_key = os.getenv("REVIEW_PROVIDER_API_KEY", "").strip()
    return {
        "configured": bool(endpoint and api_key),
        "endpoint_set": bool(endpoint),
        "api_key_set": bool(api_key),
        "allowed_hosts": sorted(list(get_allowed_hosts()))
    }


def validate_product_url(product_url):
    """
    Strict URL validation to protect against Server-Side Request Forgery (SSRF):
    - HTTPS scheme required
    - No embedded user credentials
    - Port restricted to standard HTTPS (443 or omitted)
    - IP addresses and localhost strictly rejected
    - Hostname must match allowed product retail domains
    """
    if not isinstance(product_url, str) or not product_url.strip():
        raise ValueError("Please provide a valid, non-empty product URL.")

    product_url = product_url.strip()
    if len(product_url) > 2048:
        raise ValueError("Product URL exceeds maximum permitted length (2048 characters).")

    parsed = urlsplit(product_url)

    if parsed.scheme != "https":
        raise ValueError("Security violation: Only secure HTTPS URLs (https://) are accepted.")

    if parsed.username or parsed.password:
        raise ValueError("Security violation: Embedded URL credentials are not allowed.")

    if parsed.port and parsed.port != 443:
        raise ValueError("Security violation: Non-standard ports are prohibited.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Invalid product URL: Missing hostname.")

    # Prevent SSRF via IP addresses (loopback, private ranges, link-local, cloud metadata 169.254.169.254)
    try:
        ip = ipaddress.ip_address(hostname)
        raise ValueError(f"Security violation: IP addresses ({ip}) cannot be targeted directly.")
    except ValueError as e:
        if "Security violation" in str(e):
            raise
        # Not an IP address, proceed with domain verification

    # Block common local/internal hostnames
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0"} or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ValueError("Security violation: Internal or local hostnames are strictly disallowed.")

    allowed_hosts = get_allowed_hosts()
    is_allowed = any(
        hostname == allowed or hostname.endswith("." + allowed)
        for allowed in allowed_hosts
    )

    if not is_allowed:
        hosts_str = ", ".join(sorted(allowed_hosts))
        raise ValueError(
            f"The domain '{hostname}' is not authorized. "
            f"Permitted retail domains: {hosts_str}."
        )

    return product_url


def fetch_reviews(product_url, limit=50):
    """
    Retrieves genuine product reviews via an authorized third-party review provider API.
    Does NOT perform unauthorized website scraping or bypass anti-bot measures.
    Reads credentials strictly from environment variables.
    """
    # 1. Strictly validate URL and prevent SSRF first
    validated_url = validate_product_url(product_url)
    clamped_limit = min(max(int(limit), 1), 50)

    # 2. Check provider credentials
    endpoint = os.getenv("REVIEW_PROVIDER_ENDPOINT", "").strip()
    api_key = os.getenv("REVIEW_PROVIDER_API_KEY", "").strip()

    if not endpoint or not api_key:
        raise RuntimeError(
            "Review Provider API is not configured. Live review collection requires an authorized "
            "review data provider (e.g., Rainforest API, Octoparse, or an official retail partner API). "
            "Set REVIEW_PROVIDER_ENDPOINT and REVIEW_PROVIDER_API_KEY environment variables to enable this feature. "
            "In the meantime, you can use the Bulk Review Analysis (CSV upload) to analyze reviews."
        )

    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ReviewShield-MLBC/2.0"
            },
            json={
                "product_url": validated_url,
                "limit": clamped_limit
            },
            timeout=15
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise requests.RequestException(
            f"Review provider API request failed: {exc}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("Review provider API returned a non-JSON response.") from exc

    raw_reviews = payload.get("reviews", [])
    if not isinstance(raw_reviews, list):
        raise ValueError("Invalid response format from review provider API.")

    cleaned_reviews = []
    for item in raw_reviews[:clamped_limit]:
        if isinstance(item, dict):
            txt = item.get("text") or item.get("review_text") or item.get("body")
            if isinstance(txt, str) and txt.strip():
                cleaned_reviews.append(txt.strip())
        elif isinstance(item, str) and item.strip():
            cleaned_reviews.append(item.strip())

    if not cleaned_reviews:
        raise ValueError("No customer reviews were found for this product URL via the provider API.")

    return cleaned_reviews
