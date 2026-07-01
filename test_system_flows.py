import requests
import json
import uuid



BASE_URL = "http://localhost:8000/api/v1"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "password123"

def print_step(msg):
    print(f"\n==========================================")
    print(f" {msg} ")
    print(f"==========================================")

def get_auth_headers():
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=5)
    if res.status_code != 200:
        raise Exception(f"Admin login failed: {res.text}")
    token = res.json().get("data", {}).get("accessToken")
    return {"Authorization": f"Bearer {token}"}

def main():
    headers = get_auth_headers()
    
    unique_id = str(uuid.uuid4())[:8]

    # 1. Create Supplier
    print_step("1. Creating Supplier")
    res = requests.post(f"{BASE_URL}/suppliers/", headers=headers, json={
        "name": f"Test Supplier {unique_id}",
        "email": f"supplier_{unique_id}@test.com",
        "phone": "0123456789",
        "address": "123 Supplier St"
    })
    supplier = res.json().get("data", {})
    supplier_id = supplier.get("id")
    print(f"Created Supplier: {supplier.get('name')} (ID: {supplier_id})")

    # 2. Create Category & Book
    print_step("2. Creating Category and Book")
    res = requests.post(f"{BASE_URL}/categories/", headers=headers, json={
        "name": f"Test Category {unique_id}",
        "slug": f"test-cat-{unique_id}"
    })
    cat_id = res.json().get("data", {}).get("id")

    res = requests.post(f"{BASE_URL}/books/", headers=headers, json={
        "title": f"Test Book {unique_id}",
        "author": "Test Author",
        "isbn": f"ISBN-{unique_id}",
        "price": 25.00,
        "stock": 0,
        "category_id": cat_id
    })
    book = res.json().get("data", {})
    book_id = book.get("id")
    print(f"Created Book: {book.get('title')} (Stock: 0)")

    # 3. Create PO & Receive It (Increase Stock)
    print_step("3. Creating and Receiving Purchase Order")
    try:
        po_res = requests.post(f"{BASE_URL}/purchase-orders", headers=headers, json={
            "supplier_id": supplier_id,
            "note": "Testing PO flow",
            "items": [
                {
                    "book_id": book_id,
                    "quantity": 10,
                    "cost_price": 15.00
                }
            ]
        }, timeout=5)
        print("PO Create status:", po_res.status_code)
        if po_res.status_code != 201:
            print("Error details:", po_res.text)
        po = po_res.json().get("data", {})
        po_id = po.get("id")
        print(f"Created PO: {po.get('po_number')} (Status: DRAFT)")
    except Exception as e:
        print("Exception occurred during PO creation:", e)
        return

    # Update to ordered
    requests.put(f"{BASE_URL}/purchase-orders/{po_id}/status", headers=headers, json={"status": "ordered"})
    # Update to received
    requests.put(f"{BASE_URL}/purchase-orders/{po_id}/status", headers=headers, json={"status": "received"})
    
    # Check book stock
    res = requests.get(f"{BASE_URL}/books/{book_id}")
    print(f"Book Stock after PO Received: {res.json().get('data', {}).get('stock')} (Expected: 10)")

    # 4. Stock Adjustment (Decrease Stock)
    print_step("4. Stock Adjustment")
    requests.post(f"{BASE_URL}/inventory/adjust", headers=headers, json={
        "book_id": book_id,
        "quantity_adjusted": -2,
        "reason": "Damaged"
    })
    res = requests.get(f"{BASE_URL}/books/{book_id}")
    print(f"Book Stock after Adjustment: {res.json().get('data', {}).get('stock')} (Expected: 8)")

    # 6. Customer Checkout
    print_step("6. Customer Order")
    cust_email = f"cust_{unique_id}@test.com"
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": "Test Customer",
        "email": cust_email,
        "password": "password123"
    })
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": cust_email, "password": "password123"})
    cust_token = res.json().get("data", {}).get("accessToken")
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    requests.post(f"{BASE_URL}/cart/items", headers=cust_headers, json={"book_id": book_id, "quantity": 3})
    res = requests.post(f"{BASE_URL}/orders/", headers=cust_headers, json={
        "shipping_address": "Test Address",
        "payment_method": "cash_on_delivery"
    })
    order_id = res.json().get("data", {}).get("id")
    print(f"Customer placed order (ID: {order_id}) for 3 books.")

    requests.patch(f"{BASE_URL}/admin/orders/{order_id}/status", headers=headers, json={"status": "delivered"})
    print("Admin marked order as DELIVERED.")

    res = requests.get(f"{BASE_URL}/books/{book_id}")
    print(f"Book Stock after Sale: {res.json().get('data', {}).get('stock')} (Expected: 5)")

    # 5. Check Stock Movement
    print_step("5. Check Stock Movement Log")
    res = requests.get(f"{BASE_URL}/inventory/movements?book_id={book_id}", headers=headers)
    movements = res.json().get("data", {}).get("movements", [])
    for mov in movements:
        print(f"- Type: {mov['transaction_type']} | Qty: {mov['quantity']} | Current Stock: {mov['current_stock']}")

    # 7. Check Reports
    print_step("7. Check Financial Reports (Spend and Sale)")
    res = requests.get(f"{BASE_URL}/admin/reports/daily", headers=headers)
    rep = res.json().get("data", {})
    kpis = rep.get("kpis", {})
    print(f"Today's Sales Revenue : ${kpis.get('total_revenue', 0)}")
    print(f"Today's Profit        : ${kpis.get('total_profit', 0)}")
    
    print("\n--- Test Flow Completed Successfully! ---")

if __name__ == "__main__":
    main()
