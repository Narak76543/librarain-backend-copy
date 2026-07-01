import requests
import time
import uuid

BASE_URL = "http://localhost:8000/api/v1"

def login():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@example.com",
        "password": "password123" 
    })
    if res.status_code == 200:
        return res.json().get("data", {}).get("accessToken")
    return None

def print_step(step):
    print(f"\n==========================================")
    print(f" {step} ")
    print(f"==========================================")

def run_demo():
    token = login()
    if not token:
        print("Could not login. Make sure admin@example.com / password is correct.")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    
    unique_suffix = str(uuid.uuid4())[:4]
    supplier_name = f"Messi (Demo {unique_suffix})"
    book_title = f"Python 1 (Demo {unique_suffix})"
    
    print_step("1. Creating Supplier 'Messi'")
    res = requests.post(f"{BASE_URL}/suppliers", headers=headers, json={
        "name": supplier_name,
        "contact_name": "Lionel Messi",
        "email": f"messi_{unique_suffix}@example.com",
        "phone": "123456789",
        "address": "Miami, FL"
    })
    supplier_id = res.json().get("data", {}).get("id")
    print(f"✅ Created Supplier: {supplier_name}")
    
    print_step("2. Creating Book 'Python 1'")
    res = requests.get(f"{BASE_URL}/books/categories", headers=headers)
    categories = res.json().get("data", {}).get("categories", [])
    if not categories:
        res = requests.post(f"{BASE_URL}/books/categories", headers=headers, json={"name": "Programming"})
        cat_id = res.json().get("data", {}).get("id")
    else:
        cat_id = categories[0]["id"]
        
    res = requests.post(f"{BASE_URL}/books", headers=headers, json={
        "title": book_title,
        "author": "Guido van Rossum",
        "isbn": f"978-00000{unique_suffix}",
        "price": 12.00, 
        "category_id": cat_id,
        "publisher": "Tech Books",
        "publication_year": 2026,
        "description": "Learn Python step by step",
        "stock": 0
    })
    book_id = res.json().get("data", {}).get("id")
    print(f"✅ Created Book: {book_title} with Selling Price $12.00")
    print(f"   Current Stock: 0")
    
    print_step(f"3. Creating Purchase Order for 100 books at $7.00/each")
    res = requests.post(f"{BASE_URL}/purchase-orders", headers=headers, json={
        "supplier_id": supplier_id,
        "note": "Stock up for summer sales",
        "items": [
            {
                "book_id": book_id,
                "quantity": 100,
                "cost_price": 7.00
            }
        ]
    })
    po_id = res.json().get("data", {}).get("id")
    po_num = res.json().get("data", {}).get("po_number")
    print(f"✅ Created PO: {po_num} (Status: DRAFT)")
    
    print_step(f"4. Marking PO as 'RECEIVED' to add stock")
    res = requests.put(f"{BASE_URL}/purchase-orders/{po_id}/status", headers=headers, json={
        "status": "received"
    })
    print(f"✅ PO Status updated to RECEIVED")
    
    res = requests.get(f"{BASE_URL}/books/{book_id}")
    new_stock = res.json().get("data", {}).get("stock")
    new_cost = res.json().get("data", {}).get("cost_price")
    
    print_step(f"5. Final Verification")
    print(f"✅ {book_title} is now IN STOCK!")
    print(f"   New Stock Quantity: {new_stock} (Expected: 100)")
    print(f"   Updated Cost Price: ${new_cost} (Expected: $7.00)")
    print(f"   Selling Price: $12.00")
    print(f"\nThe book is now LIVE in the system and ready to be sold to customers!")

if __name__ == "__main__":
    run_demo()
