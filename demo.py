"""
Demo script for Contract Clause Extractor API.

This script demonstrates end-to-end usage of the API:
1. Register/Login to get JWT token
2. Upload a contract document (PDF, DOCX, or TXT)
3. Extract clauses using LLM
4. Retrieve the extraction results
5. List all extractions

Usage:
    python demo.py <path_to_contract_file>

Example:
    python demo.py samples/sample_contract.txt
"""
import sys
import requests
import json
import time
from pathlib import Path
from datetime import datetime


BASE_URL = "http://localhost:8000"
# Demo user credentials
DEMO_EMAIL = f"demo_{int(datetime.now().timestamp())}@example.com"
DEMO_USERNAME = f"demo_{int(datetime.now().timestamp())}"
DEMO_PASSWORD = "demopass123"


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def check_health():
    """Check if the API is running."""
    print_header("1. Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        print("✓ API is healthy!")
        print(json.dumps(response.json(), indent=2))
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ API is not reachable: {str(e)}")
        print("\nMake sure the API is running:")
        print("  docker-compose up")
        return False


def register_and_login():
    """Register a demo user and get JWT token."""
    print_header("2. Register and Login")

    # Try to register
    print(f"Registering demo user: {DEMO_EMAIL}")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": DEMO_EMAIL,
                "username": DEMO_USERNAME,
                "password": DEMO_PASSWORD
            },
            timeout=10
        )

        if response.status_code == 201:
            print("✓ User registered successfully!")
        elif response.status_code == 400:
            print("ℹ User already exists, proceeding to login...")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"Registration note: {str(e)}")

    # Login to get token
    print(f"Logging in as: {DEMO_USERNAME}")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": DEMO_USERNAME,
                "password": DEMO_PASSWORD
            },
            timeout=10
        )
        response.raise_for_status()

        token_data = response.json()
        token = token_data["access_token"]
        print("✓ Login successful!")
        print(f"  Token: {token[:50]}...")
        return token

    except requests.exceptions.RequestException as e:
        print(f"✗ Login failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def upload_contract(file_path: str, token: str):
    """Upload a contract document and extract clauses."""
    print_header("3. Upload Contract and Extract Clauses")

    if not Path(file_path).exists():
        print(f"✗ File not found: {file_path}")
        return None

    print(f"Uploading: {file_path}")

    try:
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f)}
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{BASE_URL}/api/extract",
                files=files,
                headers=headers,
                timeout=60  # Give LLM time to process
            )
            response.raise_for_status()

        result = response.json()
        print(f"\n✓ Successfully extracted clauses!")
        print(f"  Extraction ID: {result['id']}")
        print(f"  Filename: {result['filename']}")
        print(f"  Status: {result['status']}")
        print(f"  Total Clauses: {len(result['clauses'])}")

        print("\nExtracted Clauses:")
        for idx, clause in enumerate(result['clauses'], 1):
            print(f"\n  [{idx}] {clause['title']}")
            print(f"      Type: {clause['clause_type']}")
            summary = clause.get('extra_data', {}).get('summary', 'N/A')
            if summary and len(summary) > 100:
                summary = summary[:100] + "..."
            print(f"      Summary: {summary}")

        return result['id']

    except requests.exceptions.RequestException as e:
        print(f"\n✗ Upload failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def get_extraction(extraction_id: str, token: str):
    """Retrieve a specific extraction by ID."""
    print_header("4. Retrieve Extraction by ID")

    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/extractions/{extraction_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        result = response.json()
        print(f"✓ Retrieved extraction: {extraction_id}")
        print(f"  Filename: {result['filename']}")
        print(f"  File Type: {result['file_type']}")
        print(f"  File Size: {result['file_size']} bytes")
        print(f"  Status: {result['status']}")
        print(f"  Created: {result['created_at']}")
        print(f"  Total Clauses: {len(result['clauses'])}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"✗ Retrieval failed: {str(e)}")
        return None


def list_extractions(token: str, limit: int = 10):
    """List all extractions with pagination."""
    print_header("5. List All Extractions")

    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/api/extractions",
            params={"skip": 0, "limit": limit},
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        result = response.json()
        print(f"✓ Found {result['total']} total extractions")
        print(f"  Showing {len(result['extractions'])} extractions:\n")

        for idx, extraction in enumerate(result['extractions'], 1):
            print(f"  [{idx}] {extraction['filename']}")
            print(f"      ID: {extraction['id']}")
            print(f"      Status: {extraction['status']}")
            print(f"      Clauses: {len(extraction['clauses'])}")
            print(f"      Created: {extraction['created_at']}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"✗ List failed: {str(e)}")
        return None


def main():
    """Main demo function."""
    print("\n" + "=" * 80)
    print("  Contract Clause Extractor - Demo Script")
    print("=" * 80)

    # Check if file path provided
    if len(sys.argv) < 2:
        print("\nUsage: python demo.py <path_to_contract_file>")
        print("\nExample:")
        print("  python demo.py sample_contract.pdf")
        print("\nNote: Make sure the API is running (docker-compose up)")
        sys.exit(1)

    file_path = sys.argv[1]

    # Step 1: Health check
    if not check_health():
        sys.exit(1)

    time.sleep(1)

    # Step 2: Register and login
    token = register_and_login()
    if not token:
        sys.exit(1)

    time.sleep(1)

    # Step 3: Upload contract
    extraction_id = upload_contract(file_path, token)
    if not extraction_id:
        sys.exit(1)

    time.sleep(1)

    # Step 4: Retrieve extraction
    get_extraction(extraction_id, token)

    time.sleep(1)

    # Step 5: List all extractions
    list_extractions(token)

    print_header("Demo Complete!")
    print("✓ All API endpoints tested successfully!\n")


if __name__ == "__main__":
    main()
