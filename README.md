# Jewelry B2B Billing & Automation System

## Project Overview

This is a robust **Python-based backend service** designed to automate the dynamic billing process for the jewelry industry. It bridges the gap between manual calculations and digital invoicing by integrating **live market data** with a **persistence layer**.

---

## Core Objectives

- **Dynamic Valuation:** Automate metal pricing by fetching real-time **XAU (Gold)** rates via external REST APIs.
- **Precision Billing:** Elimination of human error in calculating **GST (3%)**, making charges, and weight-based aggregates.
- **Document Automation:** Generating professional, computer-generated **PDF invoices** dynamically in-memory *(In-Memory Buffer)*.
- **Data Persistence:** Securely logging customer transactions and metadata using a relational database *(Supabase/PostgreSQL)*.

---

## Technical Stack (SDE Architecture)

| Component | Technology |
|---|---|
| **Language** | Python 3.x |
| **Framework** | Flask (Micro-framework for API Routing and Request/Response management) |
| **Database** | Supabase (PostgreSQL-as-a-Service) for Data Access Layer (DAL) |
| **I/O & Networking** | `requests` library for synchronous Upstream API communication |
| **Document Engine** | ReportLab for programmable PDF generation |

---

## System Architecture & Data Flow

The system follows a strict **Separation of Concerns (SoC)** principle:

1. **Endpoint Trigger:** The React/Next.js frontend dispatches a JSON payload to the `/api/calculate` **POST** route.
2. **Input Validation (Fail-Fast):** The backend validates the payload immediately. If critical data (Name, Phone, Weight) is missing, it returns a `400 Bad Request`.
3. **Upstream Integration:** The system executes a synchronous **GET** request to the MetalPriceAPI with a **5-second timeout** to fetch live rates.
4. **Business Logic Layer:** The engine calculates:
   - $Metal\ Value = Weight \times Live\ Rate$
   - $Making\ Charges = Weight \times 500$
   - $GST = Subtotal \times 3\%$
5. **Persistence Layer:** Transactional data is pushed to the `customers` table in Supabase.
6. **Document Streaming:** An in-memory PDF is generated using a `BytesIO` buffer and streamed to the client.

---

## Key SDE Features Implemented

- **Graceful Degradation:** Integrated fallback mechanisms to use a default rate if the external API is unreachable.
- **Fault Tolerance:** Comprehensive `try-except` blocks to handle network exceptions and database connection timeouts.
- **Liveness Probes:** A root `/` route implemented for cloud platform health monitoring.

---

## How to Run Locally

### 1. Setup Virtual Environment

```bash
python -m venv venv
source venv/Scripts/activate  # Git Bash
```

### 2. Install Dependencies

```bash
pip install Flask requests supabase reportlab
```

### 3. Run Application

```bash
python app.py
```
