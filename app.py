import os
import requests # Upstream API call karne ke liye
from flask import Flask, jsonify, request # request (no 's') React se aane wala data hai
from supabase import create_client, Client
import io # SDE Jargon: For In-Memory Buffers
from flask import send_file # File client tak bhejne ke liye
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
 
app = Flask(__name__)

# --- CONFIGURATION (SDE Jargon: Environment Variables & Constants) ---
# Real world mein hum .env use karte hain, but for now we keep it here cleanly.
SUPABASE_URL = "https://ypvrdfovohfygwuabcmn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlwdnJkZm92b2hmeWd3dWFiY21uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI0NTE4NTMsImV4cCI6MjA4ODAyNzg1M30.HADVNabQr358RXhnMTrNTSdt4ri7IpJ3fsAFxUXgaPY" # Tumhari actual key
METAL_API_KEY = "ad66332144eddde2b0d4808865ba103f" # Upstream API key
GST_MULTIPLIER = 1.03  # SDE Jargon: Constant for 3% GST (100% + 3%)

# --- DATABASE CONNECTION (Graceful Degradation) ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"WARNING: Could not connect to Supabase: {e}")
except Exception as e:
    supabase = None

# --- HELPER FUNCTIONS (Separation of Concerns) ---
def get_live_gold_rate():
    """
    Fetches the live gold rate from MetalPriceAPI.
    Returns the rate per gram in INR.
    """
    # SDE JARGON: Correct Endpoint URL (Not the dashboard HTML page)
    url = "https://api.metalpriceapi.com/v1/latest"

    # Payload for the GET request
    params = {
        "api_key": METAL_API_KEY,
        "base": "XAU",       # Base = Gold (1 troy ounce)
        "currencies": "INR"  # Target = Indian Rupees
    }

    try: 
        # API Request with Timeout (requests library)
        response = requests.get(url, params=params, timeout=5) #wait untile get response or 5second timeout

        # Checking the Response Object's status_code property
        if response.status_code == 200: #validation
            # SDE JARGON: Unmarshalling / Parsing the JSON payload
            data = response.json()
            
            per_ounce_rate_inr = data['rates']['INR']  # INR per 1 troy ounce of gold
            per_gram_rate = per_ounce_rate_inr / 31.103
            
            print(f"SUCCESS: Live rate fetched -> ₹{per_gram_rate:.2f}/gram")
            return per_gram_rate
            
        else:
            print(f"UPSTREAM ERROR: API returned status {response.status_code}")
            return 6250.0 # Fallback value

    except requests.exceptions.RequestException as e:
        print(f"NETWORK EXCEPTION: Could not fetch live rate -> {e}")
        return 6250.0 # Fallback value


# --- API ENDPOINTS (Routing) ---
@app.route('/')
def home():
    return jsonify({
        "status": "Server is running",
        "supabase_connected": supabase is not None
    })

@app.route('/api/calculate', methods=['POST'])
def calculate_and_save():
    try:
        # 1. Parse Data from React Client
        data = request.get_json() # Here we use Flask's 'request'
        if not data:
            return jsonify({"status": "Error", "message": "No JSON body provided."}), 400

        name = data.get('name')
        phone = data.get('phone')
        address = data.get('address')
        weight = float(data.get('weight', 0))

        # Fail Fast Validation
        if not name or not phone or not address:
            return jsonify({"status": "Error", "message": "name, phone, and address are required"}), 400
        
        # 2. Business Logic Execution
        rate = get_live_gold_rate()
        total = (weight * rate) + (weight * 500) # Weight * Rate + Making charges
        grand_total = total * GST_MULTIPLIER     # Math logic fixed!

        # 3. Data Persistence (Supabase DAL)
        if supabase is None:
            return jsonify({"status": "Error", "message": "Database disconnected."}), 503

        customer_data = {
            "name": name,
            "phone": phone,
            "address": address
        }

        # Inserting into Supabase
        supabase.table("customers").insert(customer_data).execute()

        # 4. Final Response to Client
        return jsonify({
            "status": "Success",
            "message": f"Bill for {name} saved in Supabase!",
            "live_rate_applied": round(rate, 2),
            "bill_amount": round(grand_total, 2)
        })

    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


#--- PDF GENERATION SERVICE ----
#def create_invoice_pdf(customer_name,weight, total_amount):
    "Generates a PDF invoice completely in RAM (MEMORY) using io.BytesIO."
    "returns the raw PDF data buffer."

    # 1. Create an IN-memory Buffer (RAM main jagah banai)
    buffer = io.BytesIO()

    # 2. Setup canvas (Drawing Board)
    c = canvas.Canvas(buffer, pagesize=A4)

    # 3. Draw elements (X,Y Coordinates)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(200,800, "JEWELRY INVOICE") #Title top bar

    c.setFont("Helvetica", 14)
    c.drawString(50,750, f"Customer Name: {customer_name}")
    c.drawString(50,720, f"Gold Weight: {weight}")
    c.drawString(50,690, f"Grand Total: {total_amount}")

    # 4. Line Draw kar rhe hai design ke liye
    c.line(50,670,500,670)

    c.drawString(50,640,f"Thank you for yout Business!")

    # 4. save the drawing and close canvas
    c.showPage()
    c.save()

    # 5. SDE Jargon: Reset the buffer pointer to the beginning
    # (Memory mein data likhne ke baad, cursor end mein chala jata hai, usee shuru mai lana padta hai padhne ke liye)
    buffer.seek(0)

    return buffer


# --- PDF GENERATION SERVICE (UPGRADED) ---
def create_invoice_pdf(customer_name, phone, weight, live_rate):
    """
    Generates a professional B2B Jewelry invoice in RAM.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # --- MATH RE-CALCULATION FOR INVOICE ---
    metal_value = weight * live_rate
    making_charges = weight * 500
    subtotal = metal_value + making_charges
    gst_amount = subtotal * 0.03
    grand_total = subtotal + gst_amount

    # --- HEADER SECTION ---
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, 800, "ASHISH JEWELERS (B2B)")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, 785, "The Most Trusted Gold Wholesaler")
    c.drawString(50, 770, "GSTIN: 22AAAAA0000A1Z5")

    # --- CUSTOMER DETAILS ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 720, f"Billed To: {customer_name}")
    c.setFont("Helvetica", 12)
    c.drawString(50, 700, f"Phone: {phone}")

    # --- TABLE HEADER ---
    # c.line(x1, y1, x2, y2) -> Straight line draw karta hai
    c.line(50, 670, 550, 670)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 650, "Description")
    c.drawString(300, 650, "Weight & Rate")
    c.drawString(450, 650, "Amount (INR)")
    c.line(50, 640, 550, 640)

    # --- BILLING ITEMS ---
    c.setFont("Helvetica", 12)
    
    # Item 1: Gold Value
    c.drawString(50, 610, "22K Gold Ornament")
    c.drawString(300, 610, f"{weight}g @ Rs.{live_rate:.2f}/g")
    c.drawString(450, 610, f"{metal_value:.2f}")

    # Item 2: Making Charges
    c.drawString(50, 580, "Making Charges")
    c.drawString(300, 580, "Fixed (Rs. 500/g)")
    c.drawString(450, 580, f"{making_charges:.2f}")

    # Item 3: GST
    c.drawString(50, 550, "GST (3%)")
    c.drawString(300, 550, "-")
    c.drawString(450, 550, f"{gst_amount:.2f}")

    c.line(50, 530, 550, 530)

    # --- GRAND TOTAL ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(300, 500, "Grand Total:")
    c.drawString(450, 500, f"Rs. {grand_total:.2f}")

    # --- FOOTER ---
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 100, "Thank you for doing business with Ashish Jewelers.")
    c.drawString(50, 85, "This is a computer-generated invoice and does not require a signature.")

    # Save to buffer
    c.showPage()
    c.save()
    buffer.seek(0)
    
    return buffer

@app.route('/api/test-pdf', methods=['GET'])
def test_pdf():
    # SDE Jargon: Mock Data injection
    pdf_buffer = create_invoice_pdf(
        customer_name="Ramesh Retailer",
        phone="+91-9876543210",
        weight=12.5,
        live_rate=6300.50
    )
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="Professional_Invoice.pdf",
        mimetype='application/pdf'
    )

    #--- NEW TEST ROUTE---
#@app.route('/api/test-pdf', methods=['GET','POST'])
#def test_pdf():
        # Abhi hum dummy data use kar rhe hai test ke liye
        #dummy_name = "Ashish SDE"
        #dummy_weight = 15.5
        #dummy_total = 105000.00

        # PDF function ko call kiya
       # pdf_buffer = create_invoice_pdf(dummy_name,dummy_weight,dummy_total)

        # Flask ka send_file use karke client ko memory se hi file bhej di
        #return send_file(
           # pdf_buffer,
           # as_attachment=True,
            # download_name="Invoice_Ashish.pdf",
           # mimetype='application/pdf'
       # )

if __name__ == '__main__':
    app.run(debug=True, port=5000)