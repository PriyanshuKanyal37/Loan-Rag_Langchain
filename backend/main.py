import bleach
import logging
import unicodedata
from pathlib import Path
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

from backend.ai_pipeline import retrieve_docs, run_credit_chain, generate_targeted_queries, enhanced_retrieve_docs

# ---------- SETUP ----------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Loan Intelligence Assistant API")

# CORS Configuration - Allow production frontend
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

# Add production frontend URL if in production
if ENVIRONMENT == "production":
    frontend_url = os.getenv("FRONTEND_URL", "https://loan-rag-frontend.onrender.com")
    allowed_origins.append(frontend_url)
    # Allow all origins in production (you can restrict this later)
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if ENVIRONMENT != "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DATA MODELS ----------
class FormType(str, Enum):
    purchase = "purchase_application"
    refinance = "refinance_application"
    smsf_purchase = "smsf_loan_purchase"
    construction = "construction_loan"
    cashout_refinance = "cashout_refinance"
    commercial = "commercial_property_loan"


FORM_TYPE_LABELS = {
    FormType.purchase: "Purchase Application",
    FormType.refinance: "Refinance Application",
    FormType.smsf_purchase: "SMSF Loan - Purchase",
    FormType.construction: "Construction Loan",
    FormType.cashout_refinance: "Cash-Out Refinance",
    FormType.commercial: "Commercial Property Loan",
}

STATE_OPTIONS = ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]
YES_NO_OPTIONS = ["Yes", "No"]
PURCHASE_PROPERTY_TYPES = ["House", "Apartment", "Townhouse", "Vacant Land", "Dual Occupancy", "Other"]
PURCHASE_PURPOSE_OPTIONS = ["Owner-Occupied", "Investment"]
LOAN_REPAYMENT_OPTIONS = ["Principal & Interest (P&I)", "Interest Only (IO)"]
RESIDENCY_OPTIONS = ["Australian Citizen", "Permanent Resident", "Temporary Visa", "Non-Resident"]
EMPLOYMENT_TYPE_OPTIONS = [
    "Full-Time",
    "Part-Time",
    "Casual",
    "Contractor",
    "Self-Employed",
    "Retired",
    "Other",
]
DEPOSIT_SOURCE_OPTIONS = ["Savings", "Gift", "Equity", "Sale of Asset", "Inheritance", "Other"]
PRODUCT_FEATURE_OPTIONS = ["Offset Account", "Fixed Rate", "Variable Rate", "Redraw Facility", "Package", "Split Loan"]
REFINANCE_REASON_OPTIONS = [
    "Lower Interest Rate",
    "Debt Consolidation",
    "Equity Release",
    "Change Product/Features",
    "Other",
]
CURRENT_REPAYMENT_TYPE_OPTIONS = ["Principal & Interest", "Interest Only"]
TRUSTEE_TYPE_OPTIONS = ["Corporate Trustee", "Individual Trustees"]
SMSF_STRUCTURE_OPTIONS = ["Single Member", "Multi Member"]
LRBA_STRUCTURE_OPTIONS = ["Established", "To Be Established"]
BARE_TRUST_STATUS_OPTIONS = ["Established", "To Be Established"]
CONSTRUCTION_TYPE_OPTIONS = ["Fixed-Price Contract", "Owner-Builder"]
LAND_TITLE_STATUS_OPTIONS = ["Registered", "Unregistered"]
CONSTRUCTION_STAGE_OPTIONS = [
    "Not Started",
    "Slab Stage",
    "Frame Stage",
    "Lock-Up Stage",
    "Fixing Stage",
    "Completion Stage",
]
CONSTRUCTION_LOAN_FEATURE_OPTIONS = ["Interest-Only During Construction", "Offset Account", "Redraw"]
CASHOUT_PURPOSE_OPTIONS = [
    "Renovation",
    "Investment Property Purchase",
    "Debt Consolidation",
    "Personal Use",
    "Business Use",
    "Other",
]
FUNDS_USAGE_TYPE_OPTIONS = ["Personal", "Business"]
DEBT_TYPE_OPTIONS = ["Mortgage", "Credit Card", "Personal Loan", "Car Loan", "HECS/HELP", "Overdraft", "Other"]
CREDIT_HISTORY_OPTIONS = ["Good", "Fair", "Poor"]
COMMERCIAL_PROPERTY_TYPES = ["Retail", "Industrial", "Office", "Warehouse", "Mixed Use", "Other"]
COMMERCIAL_PURPOSE_OPTIONS = ["Owner-Occupied", "Investment"]
COMMERCIAL_BORROWER_STRUCTURE_OPTIONS = ["Individual", "Company", "Trust", "SMSF"]
BORROWER_TENANT_REL_OPTIONS = ["Related Entity", "Unrelated Tenant", "N/A (Vacant)"]
REQUESTED_CHANGES_OPTIONS = [
    "Cash Out",
    "New Loan Term",
    "Switch to IO",
    "Switch to P&I",
    "Add Offset",
    "Remove Package",
    "Other",
]

FORM_TEMPLATES = {
    FormType.purchase: {
        "label": FORM_TYPE_LABELS[FormType.purchase],
        "sections": [
            {
                "title": "A. Loan Details",
                "fields": [
                    {
                        "key": "loan_amount",
                        "label": "Loan Amount (AUD)",
                        "type": "number",
                        "placeholder": "550000.00",
                        "step": "0.01",
                        "min": 1,
                    },
                    {
                        "key": "purchase_price",
                        "label": "Purchase Price (AUD)",
                        "type": "number",
                        "placeholder": "750000.00",
                        "step": "0.01",
                        "min": 1,
                    },
                    {
                        "key": "property_type",
                        "label": "Property Type",
                        "type": "select",
                        "options": PURCHASE_PROPERTY_TYPES,
                    },
                    {
                        "key": "property_location",
                        "label": "Property Location",
                        "type": "text",
                        "placeholder": "Sydney, NSW",
                    },
                    {
                        "key": "purpose",
                        "label": "Loan Purpose",
                        "type": "select",
                        "options": PURCHASE_PURPOSE_OPTIONS,
                    },
                    {
                        "key": "loan_term_years",
                        "label": "Loan Term (years)",
                        "type": "number",
                        "placeholder": "30",
                        "min": 1,
                        "max": 40,
                        "step": "1",
                        "number_mode": "int",
                    },
                    {
                        "key": "repayment_type",
                        "label": "Repayment Type",
                        "type": "select",
                        "options": LOAN_REPAYMENT_OPTIONS,
                    },
                ],
            },
            {
                "title": "B. Applicant Details",
                "fields": [
                    {
                        "key": "applicant_names",
                        "label": "Applicant Name(s)",
                        "type": "textarea",
                        "placeholder": "John Smith; Jane Doe",
                    },
                    {
                        "key": "residency_status",
                        "label": "Residency / Visa Status",
                        "type": "select",
                        "options": RESIDENCY_OPTIONS,
                    },
                    {
                        "key": "applicant_age",
                        "label": "Applicant Age",
                        "type": "number",
                        "placeholder": "35",
                        "min": 18,
                        "max": 75,
                        "step": "1",
                        "number_mode": "int",
                    },
                ],
            },
            {
                "title": "C. Income & Employment",
                "fields": [
                    {
                        "key": "employment_type",
                        "label": "Employment Type",
                        "type": "select",
                        "options": EMPLOYMENT_TYPE_OPTIONS,
                    },
                    {
                        "key": "base_income_annual",
                        "label": "Base Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "95000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "bonus_income_annual",
                        "label": "Bonus / Commission (AUD p.a.)",
                        "type": "number",
                        "placeholder": "10000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "self_employment_income_annual",
                        "label": "Self-Employment Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "85000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "total_income_annual",
                        "label": "Total Income (AUD p.a.)",
                        "type": "calculated",
                        "formula": {
                            "type": "sum",
                            "fields": [
                                "base_income_annual",
                                "bonus_income_annual",
                                "self_employment_income_annual",
                            ],
                            "decimals": 2,
                        },
                    },
                ],
            },
            {
                "title": "D. Living Expenses & Liabilities",
                "fields": [
                    {
                        "key": "monthly_living_expenses",
                        "label": "Monthly Living Expenses (AUD)",
                        "type": "number",
                        "placeholder": "3200.00",
                        "step": "0.01",
                    },
                    {
                        "key": "existing_home_loans",
                        "label": "Existing Home Loans",
                        "type": "repeater",
                        "itemLabel": "Loan",
                        "min": 0,
                        "max": 15,
                        "fields": [
                            {
                                "key": "loan_balance",
                                "label": "Loan Balance (AUD)",
                                "type": "number",
                                "placeholder": "200000.00",
                                "step": "0.01",
                            }
                        ],
                    },
                    {
                        "key": "credit_card_limit_total",
                        "label": "Total Credit Card Limits (AUD)",
                        "type": "number",
                        "placeholder": "15000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "personal_loans_balance",
                        "label": "Personal Loans Balance (AUD)",
                        "type": "number",
                        "placeholder": "8000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "help_debt_balance",
                        "label": "HELP / HECS Debt Balance (AUD)",
                        "type": "number",
                        "placeholder": "12000.00",
                        "step": "0.01",
                    },
                ],
            },
            {
                "title": "E. Deposit & Credit Information",
                "fields": [
                    {
                        "key": "deposit_source",
                        "label": "Deposit Source",
                        "type": "select",
                        "options": DEPOSIT_SOURCE_OPTIONS,
                    },
                    {
                        "key": "first_home_buyer",
                        "label": "First Home Buyer",
                        "type": "select",
                        "options": YES_NO_OPTIONS,
                    },
                    {
                        "key": "credit_score",
                        "label": "Credit Score",
                        "type": "number",
                        "placeholder": "700",
                        "min": 0,
                        "max": 1200,
                        "step": "1",
                        "number_mode": "int",
                    },
                    {
                        "key": "credit_impairments",
                        "label": "Credit Impairments",
                        "type": "textarea",
                        "placeholder": "Paid default 2020 with Telstra.",
                    },
                ],
            },
            {
                "title": "F. Product Preferences",
                "fields": [
                    {
                        "key": "preferred_features",
                        "label": "Preferred Features",
                        "type": "multiselect",
                        "options": PRODUCT_FEATURE_OPTIONS,
                        "placeholder": "Select desired features",
                    },
                ],
            },
        ],
    },
    FormType.refinance: {
        "label": FORM_TYPE_LABELS[FormType.refinance],
        "sections": [
            {
                "title": "A. Refinance Details",
                "fields": [
                    {
                        "key": "reason_for_refinance",
                        "label": "Reason for Refinance",
                        "type": "select",
                        "options": REFINANCE_REASON_OPTIONS,
                        "placeholder": "Select the primary reason",
                    },
                    {
                        "key": "existing_lender_name",
                        "label": "Existing Lender Name",
                        "type": "text",
                        "placeholder": "Commonwealth Bank",
                    },
                    {
                        "key": "current_loan_balance",
                        "label": "Current Loan Balance (AUD)",
                        "type": "number",
                        "placeholder": "420000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "estimated_property_value",
                        "label": "Estimated Property Value (AUD)",
                        "type": "number",
                        "placeholder": "750000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "current_repayment_type",
                        "label": "Current Repayment Type",
                        "type": "select",
                        "options": LOAN_REPAYMENT_OPTIONS,
                    },
                    {
                        "key": "current_loan_term_years",
                        "label": "Current Loan Term (years)",
                        "type": "number",
                        "placeholder": "30",
                        "min": 1,
                        "max": 40,
                        "step": "1",
                        "number_mode": "int",
                    },
                    {
                        "key": "requested_changes",
                        "label": "Requested Changes",
                        "type": "multiselect",
                        "options": REQUESTED_CHANGES_OPTIONS,
                        "placeholder": "Select all desired changes",
                    },
                ],
            },
            {
                "title": "B. Employment & Income",
                "fields": [
                    {
                        "key": "employment_type",
                        "label": "Employment Type",
                        "type": "select",
                        "options": EMPLOYMENT_TYPE_OPTIONS,
                    },
                    {
                        "key": "base_income_annual",
                        "label": "Base Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "95000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "bonus_or_commission_annual",
                        "label": "Bonus / Commission (AUD p.a.)",
                        "type": "number",
                        "placeholder": "5000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "self_employment_income_annual",
                        "label": "Self-Employment Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "120000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "total_income_annual",
                        "label": "Total Income (AUD p.a.)",
                        "type": "calculated",
                        "formula": {
                            "type": "sum",
                            "fields": [
                                "base_income_annual",
                                "bonus_or_commission_annual",
                                "self_employment_income_annual",
                            ],
                            "decimals": 2,
                        },
                    },
                ],
            },
            {
                "title": "C. Expense Breakdown",
                "fields": [
                    {
                        "key": "monthly_living_expenses",
                        "label": "Monthly Living Expenses (AUD)",
                        "type": "number",
                        "placeholder": "3200.00",
                        "step": "0.01",
                    },
                    {
                        "key": "credit_card_limit_total",
                        "label": "Credit Card Limit Total (AUD)",
                        "type": "number",
                        "placeholder": "10000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "personal_loan_balance",
                        "label": "Personal Loan Balance (AUD)",
                        "type": "number",
                        "placeholder": "5000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "other_loan_balances",
                        "label": "Other Loan Balances (AUD)",
                        "type": "number",
                        "placeholder": "8000.00",
                        "step": "0.01",
                    },
                ],
            },
            {
                "title": "D. Credit History",
                "fields": [
                    {
                        "key": "has_credit_issues",
                        "label": "Any Credit Issues?",
                        "type": "boolean",
                    },
                    {
                        "key": "credit_impairment_details",
                        "label": "Credit Impairment Details",
                        "type": "textarea",
                        "placeholder": "Late payment in 2022, now cleared.",
                        "show_when": {"has_credit_issues": True},
                    },
                    {
                        "key": "credit_score",
                        "label": "Credit Score",
                        "type": "number",
                        "placeholder": "700",
                        "min": 0,
                        "max": 1200,
                        "step": "1",
                        "number_mode": "int",
                    },
                ],
            },
        ],
    },
    FormType.smsf_purchase: {
        "label": FORM_TYPE_LABELS[FormType.smsf_purchase],
        "sections": [
            {
                "title": "A. Property & Loan Details",
                "fields": [
                    {
                        "key": "purchase_price",
                        "label": "Purchase Price (AUD)",
                        "type": "number",
                        "placeholder": "750000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "loan_amount",
                        "label": "Loan Amount (AUD)",
                        "type": "number",
                        "placeholder": "500000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "loan_purpose",
                        "label": "Loan Purpose",
                        "type": "select",
                        "options": ["Residential Investment"],
                    },
                    {
                        "key": "estimated_yield_percent",
                        "label": "Estimated Yield (%)",
                        "type": "number",
                        "placeholder": "4.5",
                        "step": "0.1",
                        "min": 0,
                        "max": 15,
                    },
                    {
                        "key": "rental_income_potential",
                        "label": "Rental Income Potential (AUD p.a.)",
                        "type": "number",
                        "placeholder": "30000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "property_location",
                        "label": "Property Location",
                        "type": "text",
                        "placeholder": "Brisbane, QLD",
                    },
                ],
            },
            {
                "title": "B. SMSF Structure & Trustees",
                "fields": [
                    {
                        "key": "smsf_name",
                        "label": "SMSF Name",
                        "type": "text",
                        "placeholder": "ABC Super Fund",
                    },
                    {
                        "key": "smsf_structure_type",
                        "label": "SMSF Structure Type",
                        "type": "select",
                        "options": TRUSTEE_TYPE_OPTIONS,
                    },
                    {
                        "key": "trustee_details",
                        "label": "Trustee Details",
                        "type": "repeater",
                        "itemLabel": "Trustee",
                        "min": 0,
                        "max": 6,
                        "fields": [
                            {
                                "key": "name",
                                "label": "Trustee / Director Name",
                                "type": "text",
                                "placeholder": "John Smith",
                            }
                        ],
                    },
                    {
                        "key": "lrba_structure",
                        "label": "LRBA Structure",
                        "type": "select",
                        "options": LRBA_STRUCTURE_OPTIONS,
                    },
                    {
                        "key": "bare_trust_status",
                        "label": "Bare Trust Status",
                        "type": "select",
                        "options": BARE_TRUST_STATUS_OPTIONS,
                    },
                ],
            },
            {
                "title": "C. SMSF Financials",
                "fields": [
                    {
                        "key": "smsf_contribution_history_years",
                        "label": "SMSF Contribution History (years)",
                        "type": "number",
                        "placeholder": "5",
                        "min": 0,
                        "max": 50,
                        "step": "1",
                        "number_mode": "int",
                    },
                    {
                        "key": "annual_contributions",
                        "label": "Annual Contributions (AUD)",
                        "type": "number",
                        "placeholder": "30000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "available_liquidity_post_settlement",
                        "label": "Available Liquidity Post-Settlement (AUD)",
                        "type": "number",
                        "placeholder": "120000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "total_smsf_assets",
                        "label": "Total SMSF Assets (AUD)",
                        "type": "number",
                        "placeholder": "800000.00",
                        "step": "0.01",
                    },
                ],
            },
            {
                "title": "D. Compliance Checks (Optional)",
                "fields": [
                    {
                        "key": "has_financial_advice",
                        "label": "Financial Advice Obtained?",
                        "type": "boolean",
                    },
                    {
                        "key": "has_smsf_auditor",
                        "label": "SMSF Auditor Appointed?",
                        "type": "boolean",
                    },
                    {
                        "key": "smsf_auditor_name",
                        "label": "SMSF Auditor Name",
                        "type": "text",
                        "placeholder": "SuperAudit Pty Ltd",
                        "show_when": {"has_smsf_auditor": True},
                    },
                ],
            },
        ],
    },
    FormType.construction: {
        "label": FORM_TYPE_LABELS[FormType.construction],
        "sections": [
            {
                "title": "A. Property & Construction Details",
                "fields": [
                    {
                        "key": "land_purchase_price",
                        "label": "Land Purchase Price (AUD)",
                        "type": "number",
                        "placeholder": "350000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "build_cost",
                        "label": "Build Cost (AUD)",
                        "type": "number",
                        "placeholder": "400000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "estimated_completion_value",
                        "label": "Estimated Completion Value (AUD)",
                        "type": "number",
                        "placeholder": "820000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "construction_type",
                        "label": "Construction Type",
                        "type": "select",
                        "options": CONSTRUCTION_TYPE_OPTIONS,
                    },
                    {
                        "key": "land_title_status",
                        "label": "Land Title Status",
                        "type": "select",
                        "options": LAND_TITLE_STATUS_OPTIONS,
                    },
                    {
                        "key": "stage_of_construction",
                        "label": "Stage of Construction",
                        "type": "select",
                        "options": CONSTRUCTION_STAGE_OPTIONS,
                    },
                    {
                        "key": "builder_name",
                        "label": "Builder Name",
                        "type": "text",
                        "placeholder": "BuildPro Homes Pty Ltd",
                    },
                    {
                        "key": "builder_license_number",
                        "label": "Builder Licence Number",
                        "type": "text",
                        "placeholder": "QLD 123456",
                    },
                ],
            },
            {
                "title": "B. Financial Structure",
                "fields": [
                    {
                        "key": "deposit_contribution",
                        "label": "Deposit Contribution (AUD)",
                        "type": "number",
                        "placeholder": "80000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "equity_contribution",
                        "label": "Equity Contribution (AUD)",
                        "type": "number",
                        "placeholder": "100000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "total_contribution",
                        "label": "Total Contribution (AUD)",
                        "type": "calculated",
                        "formula": {
                            "type": "sum",
                            "fields": ["deposit_contribution", "equity_contribution"],
                            "decimals": 2,
                        },
                    },
                    {
                        "key": "loan_amount_requested",
                        "label": "Loan Amount Requested (AUD)",
                        "type": "number",
                        "placeholder": "550000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "loan_to_value_ratio_percent",
                        "label": "Loan-to-Value Ratio (%)",
                        "type": "calculated",
                        "suffix": "%",
                        "formula": {
                            "type": "ratio",
                            "numerator_fields": ["loan_amount_requested"],
                            "denominator_field": "estimated_completion_value",
                            "multiplier": 100,
                            "decimals": 2,
                        },
                    },
                ],
            },
            {
                "title": "C. Borrower Employment & Income",
                "fields": [
                    {
                        "key": "employment_type",
                        "label": "Employment Type",
                        "type": "select",
                        "options": EMPLOYMENT_TYPE_OPTIONS,
                    },
                    {
                        "key": "base_income_annual",
                        "label": "Base Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "95000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "bonus_or_other_income_annual",
                        "label": "Bonus / Other Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "5000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "total_income_annual",
                        "label": "Total Income (AUD p.a.)",
                        "type": "calculated",
                        "formula": {
                            "type": "sum",
                            "fields": [
                                "base_income_annual",
                                "bonus_or_other_income_annual",
                            ],
                            "decimals": 2,
                        },
                    },
                ],
            },
            {
                "title": "D. Existing Debts & Living Expenses",
                "fields": [
                    {
                        "key": "existing_home_loans_balance",
                        "label": "Existing Home Loans Balance (AUD)",
                        "type": "number",
                        "placeholder": "200000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "personal_loans_balance",
                        "label": "Personal Loans Balance (AUD)",
                        "type": "number",
                        "placeholder": "10000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "credit_card_limit_total",
                        "label": "Credit Card Limit Total (AUD)",
                        "type": "number",
                        "placeholder": "15000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "monthly_living_expenses",
                        "label": "Monthly Living Expenses (AUD)",
                        "type": "number",
                        "placeholder": "3200.00",
                        "step": "0.01",
                    },
                ],
            },
            {
                "title": "E. Loan Product Features",
                "fields": [
                    {
                        "key": "interest_only_during_construction",
                        "label": "Interest-Only During Construction",
                        "type": "boolean",
                    },
                    {
                        "key": "has_offset_account",
                        "label": "Offset Account Included",
                        "type": "boolean",
                    },
                    {
                        "key": "loan_repayment_type_post_construction",
                        "label": "Post-Construction Repayment Type",
                        "type": "select",
                        "options": LOAN_REPAYMENT_OPTIONS,
                    },
                    {
                        "key": "loan_term_years",
                        "label": "Loan Term (years)",
                        "type": "number",
                        "placeholder": "30",
                        "min": 1,
                        "max": 40,
                        "step": "1",
                        "number_mode": "int",
                    },
                ],
            },
        ],
    },
    FormType.cashout_refinance: {
        "label": FORM_TYPE_LABELS[FormType.cashout_refinance],
        "sections": [
            {
                "title": "A. Property & Loan Details",
                "fields": [
                    {
                        "key": "property_value",
                        "label": "Property Value (AUD)",
                        "type": "number",
                        "placeholder": "850000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "current_loan_balance",
                        "label": "Current Loan Balance (AUD)",
                        "type": "number",
                        "placeholder": "520000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "cash_out_amount_requested",
                        "label": "Cash-Out Amount Requested (AUD)",
                        "type": "number",
                        "placeholder": "100000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "cash_out_purpose",
                        "label": "Cash-Out Purpose",
                        "type": "select",
                        "options": CASHOUT_PURPOSE_OPTIONS,
                    },
                    {
                        "key": "fund_usage_type",
                        "label": "Fund Usage Type",
                        "type": "select",
                        "options": FUNDS_USAGE_TYPE_OPTIONS,
                    },
                    {
                        "key": "loan_to_value_ratio_percent",
                        "label": "Loan-to-Value Ratio (%)",
                        "type": "calculated",
                        "suffix": "%",
                        "formula": {
                            "type": "ratio",
                            "numerator_fields": [
                                "current_loan_balance",
                                "cash_out_amount_requested",
                            ],
                            "denominator_field": "property_value",
                            "multiplier": 100,
                            "decimals": 2,
                        },
                    },
                ],
            },
            {
                "title": "B. Employment & Income",
                "fields": [
                    {
                        "key": "employment_type",
                        "label": "Employment Type",
                        "type": "select",
                        "options": EMPLOYMENT_TYPE_OPTIONS,
                    },
                    {
                        "key": "base_income_annual",
                        "label": "Base Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "95000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "other_income_annual",
                        "label": "Other Income (AUD p.a.)",
                        "type": "number",
                        "placeholder": "12000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "total_income_annual",
                        "label": "Total Income (AUD p.a.)",
                        "type": "calculated",
                        "formula": {
                            "type": "sum",
                            "fields": [
                                "base_income_annual",
                                "other_income_annual",
                            ],
                            "decimals": 2,
                        },
                    },
                ],
            },
            {
                "title": "C. Liabilities & Credit",
                "fields": [
                    {
                        "key": "ongoing_liabilities",
                        "label": "Ongoing Liabilities (AUD per month)",
                        "type": "number",
                        "placeholder": "2000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "has_credit_issues",
                        "label": "Any Credit Issues?",
                        "type": "boolean",
                    },
                    {
                        "key": "credit_impairment_details",
                        "label": "Credit Impairment Details",
                        "type": "textarea",
                        "placeholder": "Paid default in 2021 – Telstra.",
                        "show_when": {"has_credit_issues": True},
                    },
                    {
                        "key": "credit_score",
                        "label": "Credit Score",
                        "type": "number",
                        "placeholder": "720",
                        "min": 0,
                        "max": 1200,
                        "step": "1",
                        "number_mode": "int",
                    },
                ],
            },
            {
                "title": "D. Consolidation (if applicable)",
                "fields": [
                    {
                        "key": "is_debt_consolidation_included",
                        "label": "Debt Consolidation Included?",
                        "type": "boolean",
                    },
                    {
                        "key": "consolidation_debts",
                        "label": "Consolidation Debts",
                        "type": "repeater",
                        "itemLabel": "Debt",
                        "min": 0,
                        "max": 10,
                        "show_when": {"is_debt_consolidation_included": True},
                        "fields": [
                            {
                                "key": "creditor_name",
                                "label": "Creditor Name",
                                "type": "text",
                                "placeholder": "ABC Finance",
                            },
                            {
                                "key": "balance",
                                "label": "Balance (AUD)",
                                "type": "number",
                                "placeholder": "15000.00",
                                "step": "0.01",
                            },
                            {
                                "key": "limit",
                                "label": "Limit (AUD)",
                                "type": "number",
                                "placeholder": "20000.00",
                                "step": "0.01",
                            },
                            {
                                "key": "to_be_closed",
                                "label": "To Be Closed?",
                                "type": "boolean",
                            },
                        ],
                    },
                ],
            },
            {
                "title": "E. Fund Usage & Timing",
                "fields": [
                    {
                        "key": "expected_settlement_date",
                        "label": "Expected Settlement Date",
                        "type": "date",
                    },
                    {
                        "key": "evidence_of_use_required",
                        "label": "Evidence of Use Required?",
                        "type": "boolean",
                    },
                    {
                        "key": "fund_use_details",
                        "label": "Fund Use Details",
                        "type": "textarea",
                        "placeholder": "Funds to renovate bathroom and kitchen.",
                    },
                ],
            },
        ],
    },
    FormType.commercial: {
        "label": FORM_TYPE_LABELS[FormType.commercial],
        "sections": [
            {
                "title": "A. Property & Loan Details",
                "fields": [
                    {
                        "key": "purchase_price_or_refinance_amount",
                        "label": "Purchase Price / Refinance Amount (AUD)",
                        "type": "number",
                        "placeholder": "1200000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "property_type",
                        "label": "Property Type",
                        "type": "select",
                        "options": COMMERCIAL_PROPERTY_TYPES,
                    },
                    {
                        "key": "purpose",
                        "label": "Purpose",
                        "type": "select",
                        "options": COMMERCIAL_PURPOSE_OPTIONS,
                    },
                    {
                        "key": "loan_term_years",
                        "label": "Loan Term (years)",
                        "type": "number",
                        "placeholder": "15",
                        "min": 1,
                        "max": 30,
                        "step": "1",
                        "number_mode": "int",
                    },
                    {
                        "key": "loan_amount",
                        "label": "Loan Amount (AUD)",
                        "type": "number",
                        "placeholder": "900000.00",
                        "step": "0.01",
                        "min": 0,
                    },
                    {
                        "key": "lvr_percent",
                        "label": "Loan-to-Value Ratio (%)",
                        "type": "calculated",
                        "suffix": "%",
                        "formula": {
                            "type": "ratio",
                            "numerator_fields": ["loan_amount"],
                            "denominator_field": "purchase_price_or_refinance_amount",
                            "multiplier": 100,
                            "decimals": 2,
                        },
                    },
                    {
                        "key": "valuation_available",
                        "label": "Valuation Available?",
                        "type": "boolean",
                    },
                ],
            },
            {
                "title": "B. Borrower Structure",
                "fields": [
                    {
                        "key": "borrower_entity_type",
                        "label": "Borrower Entity Type",
                        "type": "select",
                        "options": COMMERCIAL_BORROWER_STRUCTURE_OPTIONS,
                    },
                    {
                        "key": "borrower_name",
                        "label": "Borrower Name",
                        "type": "text",
                        "placeholder": "ABC Investments Pty Ltd",
                    },
                    {
                        "key": "abn_or_acn",
                        "label": "ABN / ACN",
                        "type": "text",
                        "placeholder": "ABN 12 345 678 901",
                    },
                    {
                        "key": "relationship_borrower_tenant",
                        "label": "Relationship Between Borrower & Tenant",
                        "type": "select",
                        "options": BORROWER_TENANT_REL_OPTIONS,
                    },
                ],
            },
            {
                "title": "C. Lease & Income Details",
                "fields": [
                    {
                        "key": "tenant_name",
                        "label": "Tenant Name",
                        "type": "text",
                        "placeholder": "XYZ Logistics Pty Ltd",
                    },
                    {
                        "key": "lease_term_years",
                        "label": "Lease Term (years)",
                        "type": "number",
                        "placeholder": "5",
                        "min": 0,
                        "max": 30,
                        "step": "1",
                        "number_mode": "int",
                    },
                    {
                        "key": "annual_rental_income",
                        "label": "Annual Rental Income (AUD)",
                        "type": "number",
                        "placeholder": "95000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "lease_expiry_date",
                        "label": "Lease Expiry Date",
                        "type": "date",
                    },
                    {
                        "key": "vacancy_allowance_percent",
                        "label": "Vacancy Allowance (%)",
                        "type": "number",
                        "placeholder": "5.0",
                        "step": "0.1",
                        "min": 0,
                        "max": 100,
                    },
                ],
            },
            {
                "title": "D. Business & Servicing Strength",
                "fields": [
                    {
                        "key": "business_financials_available",
                        "label": "Business Financials Available?",
                        "type": "boolean",
                    },
                    {
                        "key": "annual_business_revenue",
                        "label": "Annual Business Revenue (AUD)",
                        "type": "number",
                        "placeholder": "1500000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "net_profit_before_tax",
                        "label": "Net Profit Before Tax (AUD)",
                        "type": "number",
                        "placeholder": "220000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "annual_loan_repayments",
                        "label": "Annual Loan Repayments (AUD)",
                        "type": "number",
                        "placeholder": "180000.00",
                        "step": "0.01",
                    },
                    {
                        "key": "loan_servicing_ratio",
                        "label": "Loan Servicing Ratio (%)",
                        "type": "calculated",
                        "suffix": "%",
                        "formula": {
                            "type": "ratio",
                            "numerator_fields": ["net_profit_before_tax"],
                            "denominator_field": "annual_loan_repayments",
                            "multiplier": 100,
                            "decimals": 2,
                        },
                    },
                    {
                        "key": "exit_strategy",
                        "label": "Exit Strategy",
                        "type": "textarea",
                        "placeholder": "Sale of property after completion of lease term.",
                    },
                ],
            },
        ],
    },


}

FIELD_LABEL_LOOKUP = {
    field["key"]: field["label"]
    for template in FORM_TEMPLATES.values()
    for section in template["sections"]
    for field in section["fields"]
}

# Subfield labels for repeater fields
REPEATER_SUBFIELD_LABELS: Dict[str, Dict[str, str]] = {}
for template in FORM_TEMPLATES.values():
    for section in template["sections"]:
        for field in section["fields"]:
            if field.get("type") == "repeater":
                REPEATER_SUBFIELD_LABELS[field["key"]] = {
                    sub["key"]: sub.get("label", sub["key"]) for sub in field.get("fields", [])
                }



class Applicant(BaseModel):
    name: str = Field(..., description="Applicant full name.")
    role: Optional[str] = Field(None, description="Occupation or role.")
    employment_history: Optional[str] = Field(
        None, description="Employment tenure or stability notes."
    )
    income_details: Optional[str] = Field(
        None, description="Income breakdown (salary, bonus, allowances)."
    )
    additional_notes: Optional[str] = Field(
        None, description="Other relevant applicant details."
    )


class LoanQuery(BaseModel):
    form_type: FormType
    question: Optional[str] = Field(
        None,
        description="Optional custom question for the assistant. Defaults to a lender recommendation prompt per form type.",
    )
    applicants: List[Applicant] = Field(default_factory=list)
    form_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs representing inputs captured on the selected form.",
    )
    additional_notes: Optional[str] = Field(
        None,
        description="Any extra context or requirements not captured elsewhere.",
    )


# ---------- FUNCTIONS ----------
def serialise_applicants(applicants: List[Applicant]) -> str:
    if not applicants:
        return "Not provided."

    blocks = []
    for applicant in applicants:
        lines = [f"Name: {applicant.name}"]
        if applicant.role:
            lines.append(f"Role: {applicant.role}")
        if applicant.employment_history:
            lines.append(f"Employment: {applicant.employment_history}")
        if applicant.income_details:
            lines.append(f"Income: {applicant.income_details}")
        if applicant.additional_notes:
            lines.append(f"Notes: {applicant.additional_notes}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def serialise_form_data(form_data: Dict[str, Any]) -> str:
    if not form_data:
        return "Not provided."
    lines = []
    for key, value in form_data.items():
        if value in (None, "", []):
            continue
        label = FIELD_LABEL_LOOKUP.get(key, key.replace("_", " ").title())
        # Expand repeater arrays of objects into readable bullets
        if isinstance(value, list):
            if not value:
                continue
            if all(isinstance(v, dict) for v in value):
                sublabels = REPEATER_SUBFIELD_LABELS.get(key, {})
                for idx, item in enumerate(value, start=1):
                    parts = []
                    for sk, sv in item.items():
                        if sv in (None, "", []):
                            continue
                        sk_label = sublabels.get(sk, sk.replace("_", " ").title())
                        if isinstance(sv, bool):
                            parts.append(f"{sk_label}: {'Yes' if sv else 'No'}")
                        else:
                            parts.append(f"{sk_label}: {sv}")
                    if parts:
                        lines.append(f"- {label} [{idx}]: " + ", ".join(parts))
                continue

            normalised_items = []
            for item in value:
                if item in (None, "", []):
                    continue
                if isinstance(item, bool):
                    normalised_items.append("Yes" if item else "No")
                else:
                    normalised_items.append(str(item))

            if not normalised_items:
                continue

            lines.append(f"- {label}: {', '.join(normalised_items)}")
            continue
        if isinstance(value, bool):
            lines.append(f"- {label}: {'Yes' if value else 'No'}")
            continue
        lines.append(f"- {label}: {value}")
    return "\n".join(lines) if lines else "Not provided."


def format_docs(docs) -> str:
    if not docs:
        return ""
    formatted = []
    for idx, doc in enumerate(docs, start=1):
        header = f"[Document {idx}]"
        metadata = getattr(doc, "metadata", {}) or {}
        source = metadata.get("source")
        if source:
            header += f" (Source: {source})"
        formatted.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n".join(formatted)


def build_retrieval_query(payload: LoanQuery, question: str) -> str:
    form_descriptor = FORM_TYPE_LABELS.get(payload.form_type, payload.form_type.value)
    data_bits = " ".join(
        str(v) for v in payload.form_data.values() if isinstance(v, (str, int, float))
    )
    applicant_chunks = []
    for applicant in payload.applicants:
        applicant_chunks.extend(
            filter(
                None,
                [
                    applicant.name,
                    applicant.role,
                    applicant.income_details,
                    applicant.additional_notes,
                ],
            )
        )
    applicant_bits = " ".join(applicant_chunks)
    combined = " ".join(
        filter(
            None,
            [
                form_descriptor,
                question,
                data_bits,
                applicant_bits,
                payload.additional_notes or "",
            ],
        )
    )
    return combined.strip()


DEFAULT_FORM_QUESTIONS = {
    FormType.purchase: "Provide the best lender recommendation and product structure for the above purchase scenario.",
    FormType.refinance: "Provide the best lender recommendation and product structure for the above refinance scenario.",
    FormType.smsf_purchase: "Recommend the most suitable SMSF lender and structure for the scenario.",
    FormType.construction: "Recommend the best construction loan lender and structure for the project.",
    FormType.cashout_refinance: "Recommend the most suitable lender for the cash-out refinance request.",
    FormType.commercial: "Recommend the best commercial property lender and structure for the scenario.",
}


@app.get("/form-templates")
def get_form_templates():
    return {
        "forms": [
            {
                "id": form_type.value,
                "label": template["label"],
                "sections": template["sections"],
            }
            for form_type, template in FORM_TEMPLATES.items()
        ]
    }


def calculate_lvr(loan_amount: float, property_value: float) -> float:
    """Calculate Loan-to-Value Ratio (LVR) as a percentage."""
    if property_value <= 0:
        return 0.0
    return round((loan_amount / property_value) * 100, 2)


def calculate_dti(total_debt: float, annual_income: float) -> float:
    """
    Calculate Debt-to-Income Ratio (DTI) as a multiple (Australian standard).
    DTI = Total Debt ÷ Gross Annual Income
    Example: $450,000 debt ÷ $170,000 income = 2.65x
    """
    if annual_income <= 0:
        return 0.0
    return round(total_debt / annual_income, 2)


@app.post("/ask")
def ask_structured(payload: LoanQuery):
    # Log received form data for debugging
    logging.info("="*50)
    logging.info("RECEIVED REQUEST - Form Type: %s", payload.form_type.value)
    logging.info("Number of form fields received: %d", len(payload.form_data))
    logging.info("Form data keys: %s", list(payload.form_data.keys()))

    # Log each form field with its value
    for key, value in payload.form_data.items():
        value_type = type(value).__name__
        if isinstance(value, (list, dict)):
            logging.info("  - %s (%s): %s", key, value_type, value)
        else:
            logging.info("  - %s (%s): %s", key, value_type, value)
    logging.info("="*50)

    question = payload.question or DEFAULT_FORM_QUESTIONS.get(
        payload.form_type, "Recommend the best lender and structure for the scenario provided."
    )

    # TWO-STAGE RAG: Generate targeted queries using AI
    logging.info("Stage 1: Generating targeted queries for enhanced retrieval...")
    queries = generate_targeted_queries(payload.form_data, payload.form_type.value)
    logging.info("Generated %d targeted queries:", len(queries))
    for idx, query in enumerate(queries, 1):
        logging.info("  Query %d: %s", idx, query)

    # TWO-STAGE RAG: Enhanced multi-query retrieval with deduplication
    logging.info("Stage 2: Retrieving documents using multi-query approach...")
    docs = enhanced_retrieve_docs(queries, k_per_query=4)
    docs_text = format_docs(docs)
    logging.info("Retrieved %d unique documents after deduplication", len(docs))
    logging.info("Docs preview:\n%s", docs_text[:1000])

    # Pre-calculate LVR and DTI for the AI
    # Different forms use different field names - check all possibilities
    loan_amount = float(
        payload.form_data.get("loan_amount") or  # Purchase, SMSF
        payload.form_data.get("current_loan_balance") or  # Refinance (base amount)
        payload.form_data.get("construction_loan_amount") or  # Construction
        payload.form_data.get("loan_amount_requested") or  # Commercial
        0
    )

    property_value = float(
        payload.form_data.get("property_value") or  # Purchase, SMSF
        payload.form_data.get("purchase_price") or  # Purchase
        payload.form_data.get("estimated_property_value") or  # Refinance
        payload.form_data.get("security_property_value") or  # Commercial
        payload.form_data.get("estimated_completion_value") or  # Construction
        0
    )

    # For refinance with debt consolidation, calculate the TOTAL new loan amount
    form_type_val = payload.form_type.value
    if form_type_val in ["refinance", "cashout_refinance"]:
        # Check if consolidating debts
        reason = str(payload.form_data.get("reason_for_refinance", "")).lower()
        is_consolidating = "debt" in reason or "consolidat" in reason

        if is_consolidating:
            # Total new loan = current balance + debts being consolidated + cash out
            current_balance = float(payload.form_data.get("current_loan_balance") or 0)
            cc_to_consolidate = float(payload.form_data.get("credit_card_limit_total") or 0)
            pl_to_consolidate = float(payload.form_data.get("personal_loans_balance") or 0)
            cash_out = 0.0  # Can add if there's a cash_out_amount field

            loan_amount = current_balance + cc_to_consolidate + pl_to_consolidate + cash_out
            logging.info("REFINANCE CONSOLIDATION: Calculated total new loan: $%.2f (Current: $%.2f + CC: $%.2f + PL: $%.2f)",
                        loan_amount, current_balance, cc_to_consolidate, pl_to_consolidate)

    lvr = calculate_lvr(loan_amount, property_value)

    # Calculate DTI if we have income and debt data
    # Try different income field names across different forms
    annual_income = float(
        payload.form_data.get("total_income_annual") or
        payload.form_data.get("total_income") or
        payload.form_data.get("combined_income_annual") or
        payload.form_data.get("annual_rental_income") or  # SMSF/Commercial
        payload.form_data.get("annual_business_revenue") or  # Commercial
        payload.form_data.get("net_profit_before_tax") or  # Commercial
        0
    )

    # Calculate TOTAL DEBT for DTI calculation (Australian standard)
    # DTI = Total Debt ÷ Annual Income
    #
    # CRITICAL: For refinance with consolidation, loan_amount already includes consolidated debts

    # Get all potential debts
    credit_card_debt = float(
        payload.form_data.get("credit_card_limit_total") or
        payload.form_data.get("credit_card_limit") or 0
    )
    personal_loan_debt = float(payload.form_data.get("personal_loans_balance") or 0)
    car_loan_debt = float(payload.form_data.get("car_loan_balance") or 0)
    other_loan_debt = float(payload.form_data.get("other_loan_balance") or 0)
    help_debt = float(payload.form_data.get("help_debt_balance") or 0)

    # Check if this is a refinance with debt consolidation
    is_refinance = form_type_val in ["refinance", "cashout_refinance"]

    if is_refinance:
        reason = str(payload.form_data.get("reason_for_refinance", "")).lower()
        is_consolidating = "debt" in reason or "consolidat" in reason

        if is_consolidating:
            # loan_amount already calculated above to include consolidated debts
            # Only add debts NOT being consolidated (like HECS)
            total_debt = loan_amount + help_debt
            logging.info("REFINANCE WITH CONSOLIDATION: Total debt = $%.2f (loan includes CC + PL)",
                        total_debt)
        else:
            # Not consolidating, add all existing debts
            total_debt = loan_amount + credit_card_debt + personal_loan_debt + car_loan_debt + other_loan_debt + help_debt
            logging.info("REFINANCE WITHOUT CONSOLIDATION: Total debt = $%.2f",
                        total_debt)
    else:
        # FOR PURCHASE/CONSTRUCTION/COMMERCIAL/SMSF: Add new loan + all existing debts
        total_debt = loan_amount + credit_card_debt + personal_loan_debt + car_loan_debt + other_loan_debt + help_debt
        logging.info("NON-REFINANCE (%s): Total debt = $%.2f",
                    form_type_val, total_debt)

    dti = calculate_dti(total_debt, annual_income) if annual_income > 0 else 0.0

    logging.info("CORRECTED METRICS - LVR: %.2f%%, DTI: %.2fx (Annual Income: $%.2f, Total Debt: $%.2f)",
                 lvr, dti, annual_income, total_debt)

    chain_input = {
        "form_label": FORM_TYPE_LABELS.get(payload.form_type, payload.form_type.value),
        "question": question,
        "applicants_block": serialise_applicants(payload.applicants),
        "details_block": serialise_form_data(payload.form_data),
        "additional_notes": payload.additional_notes or "None.",
        "policy_context": docs_text or "No relevant documents retrieved.",
        "lvr": f"{lvr:.2f}%",
        "dti": f"{dti:.2f}x",  # DTI is a multiple, not a percentage
        "loan_amount": f"${loan_amount:,.2f}",
        "property_value": f"${property_value:,.2f}",
    }

    logging.info("Serialized form data for AI:\n%s", chain_input["details_block"])

    answer_html, doc_metadata = run_credit_chain(chain_input, docs)
    normalised_html = unicodedata.normalize("NFKC", answer_html)
    normalised_html = normalised_html.replace("", "-").replace("–", "-").replace("—", "-").replace("•", "-")
    safe_html = bleach.clean(
        normalised_html,
        tags=[
            "p", "br", "hr", "strong", "em", "code",
            "ul", "ol", "li", "blockquote",
            "h1", "h2", "h3", "h4",
            "table", "thead", "tbody", "tr", "th", "td",
        ],
        attributes={
            "a": ["href", "title"],
            "td": ["colspan", "rowspan", "align"],
            "th": ["colspan", "rowspan", "align"],
        },
        protocols=["http", "https"],
        strip=True,
    )
    return {
        "form_type": payload.form_type.value,
        "query": question,
        "response_markdown": normalised_html,
        "response_html": safe_html,
        "documents_used": len(docs),
        "documents": doc_metadata,
    }






