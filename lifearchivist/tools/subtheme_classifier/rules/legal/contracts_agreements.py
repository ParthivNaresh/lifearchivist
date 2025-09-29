"""
Legal > Contracts and Agreements subtheme rules.

Defines precise, production-ready patterns for:
- Lease Agreement
- Employment Agreement
- Service Contract
- Purchase Agreement
- NDA

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Lease Agreement - Residential and commercial lease agreements
LEASE_AGREEMENT = SubthemeRule(
    name="lease_agreement",
    display_name="Lease Agreement",
    parent_theme="Legal",
    subtheme_category="Contracts and Agreements",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core lease patterns
        (
            r"(?:residential|commercial)\s*lease\s*agreement",
            0.95,
            "lease_agreement_header",
        ),
        (r"rental\s*agreement", 0.93, "rental_agreement_header"),
        (r"lease\s*(?:contract|agreement)", 0.92, "lease_contract"),
        (r"tenancy\s*agreement", 0.91, "tenancy_agreement"),
        (r"landlord\s*and\s*tenant", 0.90, "landlord_tenant"),
        # Lease-specific terms
        (r"monthly\s*rent:?\s*\$?[\d,]+(?:\.\d{2})?", 0.89, "monthly_rent"),
        (r"security\s*deposit:?\s*\$?[\d,]+(?:\.\d{2})?", 0.88, "security_deposit"),
        (r"lease\s*term:?\s*\d+\s*(?:months?|years?)", 0.87, "lease_term"),
        (r"(?:lessor|landlord):?\s*[A-Z][a-z]+", 0.86, "lessor_name"),
        (r"(?:lessee|tenant):?\s*[A-Z][a-z]+", 0.86, "lessee_name"),
        # Property details
        (r"premises\s*(?:located\s*at|address)", 0.85, "premises_location"),
        (r"property\s*address:?\s*.+", 0.84, "property_address"),
        (r"unit\s*(?:number|#):?\s*[A-Z0-9]+", 0.83, "unit_number"),
        # Lease clauses
        (r"rent\s*(?:payment|due)\s*(?:on|by)", 0.84, "rent_payment_terms"),
        (r"late\s*(?:fee|charge|penalty)", 0.83, "late_fee_clause"),
        (r"pet\s*(?:policy|deposit|agreement)", 0.82, "pet_policy"),
        (r"maintenance\s*(?:and|&)\s*repairs?", 0.82, "maintenance_clause"),
        (r"termination\s*(?:clause|notice)", 0.83, "termination_clause"),
    ],
    definitive_phrases={
        # Core lease phrases
        "lease agreement": 0.95,
        "rental agreement": 0.93,
        "residential lease": 0.92,
        "commercial lease": 0.92,
        "tenancy agreement": 0.91,
        "month-to-month lease": 0.90,
        "fixed-term lease": 0.89,
        # Parties
        "landlord and tenant": 0.90,
        "lessor and lessee": 0.89,
        "property owner": 0.86,
        "property manager": 0.85,
        # Lease terms
        "monthly rent": 0.88,
        "security deposit": 0.87,
        "first and last month": 0.86,
        "lease term": 0.86,
        "lease period": 0.85,
        "rental period": 0.85,
        # Property terms
        "leased premises": 0.87,
        "rental property": 0.86,
        "property address": 0.85,
        # Clauses
        "rent is due": 0.85,
        "late payment": 0.84,
        "eviction notice": 0.84,
        "quiet enjoyment": 0.83,
        "right of entry": 0.83,
        "subletting prohibited": 0.82,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Lease sections
        (r"premises:?\s*", 0.48),
        (r"term\s*of\s*lease:?\s*", 0.46),
        (r"rent:?\s*", 0.45),
        (r"utilities:?\s*", 0.42),
        (r"parking:?\s*", 0.40),
        # Legal clauses
        (r"governing\s*law:?\s*", 0.42),
        (r"entire\s*agreement:?\s*", 0.40),
        (r"severability:?\s*", 0.38),
        (r"notices:?\s*", 0.38),
        # Restrictions
        (r"use\s*of\s*premises:?\s*", 0.42),
        (r"prohibited\s*activities:?\s*", 0.40),
        (r"alterations:?\s*", 0.38),
        # Signatures
        (r"landlord\s*signature", 0.38),
        (r"tenant\s*signature", 0.38),
        (r"witness", 0.35),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Lease terms
        "lease",
        "rental",
        "rent",
        "tenant",
        "landlord",
        "lessor",
        "lessee",
        "tenancy",
        "occupancy",
        "premises",
        "property",
        "apartment",
        "unit",
        # Financial terms
        "deposit",
        "payment",
        "monthly",
        "fee",
        "utilities",
        "maintenance",
        # Legal terms
        "agreement",
        "contract",
        "term",
        "notice",
        "termination",
        "eviction",
        "sublease",
        "assignment",
        "renewal",
        "extension",
        # Property terms
        "residential",
        "commercial",
        "address",
        "bedroom",
        "bathroom",
        "parking",
        "storage",
        "amenities",
        # Conditions
        "condition",
        "inspection",
        "damage",
        "repair",
        "cleaning",
        "wear",
        "tear",
    },
    filename_patterns={
        "lease": 0.75,
        "rental": 0.73,
        "lease_agreement": 0.78,
        "rental_agreement": 0.76,
        "tenancy": 0.72,
        "apartment": 0.68,
        "residential": 0.70,
        "commercial": 0.70,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Employment patterns
        r"employment\s*agreement",
        r"job\s*offer",
        r"salary",
        r"benefits\s*package",
        # Service contract patterns
        r"scope\s*of\s*(?:work|services)",
        r"deliverables",
        r"milestone",
        r"consulting\s*agreement",
        # Purchase patterns
        r"purchase\s*price",
        r"bill\s*of\s*sale",
        r"warranty",
        # NDA patterns
        r"confidential\s*information",
        r"non-disclosure",
        r"proprietary",
    },
    exclude_phrases={
        "employment agreement",
        "service agreement",
        "purchase agreement",
        "non-disclosure agreement",
        "loan agreement",
    },
)

# Employment Agreement - Employment contracts and offer letters
EMPLOYMENT_AGREEMENT = SubthemeRule(
    name="employment_agreement",
    display_name="Employment Agreement",
    parent_theme="Legal",
    subtheme_category="Contracts and Agreements",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core employment patterns
        (r"employment\s*(?:agreement|contract)", 0.95, "employment_agreement_header"),
        (r"offer\s*(?:of\s*)?employment", 0.93, "offer_of_employment"),
        (r"job\s*offer\s*letter", 0.92, "job_offer_letter"),
        (r"employment\s*terms\s*and\s*conditions", 0.91, "employment_terms"),
        (
            r"(?:employer|company)\s*and\s*(?:employee|individual)",
            0.89,
            "employer_employee",
        ),
        # Compensation patterns
        (r"(?:annual|base)\s*salary:?\s*\$?[\d,]+", 0.90, "salary_amount"),
        (r"compensation:?\s*\$?[\d,]+", 0.88, "compensation"),
        (r"hourly\s*(?:rate|wage):?\s*\$?[\d,]+", 0.87, "hourly_rate"),
        (r"signing\s*bonus:?\s*\$?[\d,]+", 0.86, "signing_bonus"),
        (r"stock\s*options?", 0.85, "stock_options"),
        # Employment terms
        (r"start\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.88, "start_date"),
        (r"position:?\s*[A-Z][a-z]+", 0.86, "position_title"),
        (r"job\s*title:?\s*[A-Z][a-z]+", 0.86, "job_title"),
        (r"(?:full|part)[\s-]time\s*(?:employment|position)", 0.85, "employment_type"),
        # Employment clauses
        (r"at[\s-]will\s*employment", 0.87, "at_will_employment"),
        (r"non[\s-]compete\s*(?:agreement|clause)", 0.88, "non_compete"),
        (r"non[\s-]solicitation\s*(?:agreement|clause)", 0.86, "non_solicitation"),
        (r"confidentiality\s*(?:agreement|clause)", 0.85, "confidentiality_clause"),
        (r"termination\s*(?:clause|provisions?)", 0.84, "termination_clause"),
    ],
    definitive_phrases={
        # Core employment phrases
        "employment agreement": 0.95,
        "employment contract": 0.94,
        "offer letter": 0.92,
        "job offer": 0.91,
        "offer of employment": 0.93,
        "terms of employment": 0.90,
        # Parties
        "employer and employee": 0.89,
        "company and individual": 0.87,
        "hiring manager": 0.85,
        # Compensation
        "base salary": 0.88,
        "annual salary": 0.88,
        "hourly wage": 0.86,
        "compensation package": 0.87,
        "benefits package": 0.86,
        "paid time off": 0.84,
        "health insurance": 0.83,
        # Employment terms
        "start date": 0.86,
        "job title": 0.85,
        "job description": 0.84,
        "reporting to": 0.83,
        "probationary period": 0.84,
        # Clauses
        "at-will employment": 0.87,
        "non-compete agreement": 0.88,
        "non-solicitation": 0.86,
        "intellectual property": 0.85,
        "severance package": 0.84,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Employment sections
        (r"position\s*description:?\s*", 0.46),
        (r"duties\s*and\s*responsibilities:?\s*", 0.48),
        (r"compensation\s*and\s*benefits:?\s*", 0.48),
        (r"work\s*schedule:?\s*", 0.42),
        (r"reporting\s*structure:?\s*", 0.40),
        # Benefits
        (r"vacation:?\s*", 0.40),
        (r"sick\s*leave:?\s*", 0.38),
        (r"401k:?\s*", 0.38),
        (r"insurance:?\s*", 0.38),
        # Legal sections
        (r"governing\s*law:?\s*", 0.38),
        (r"arbitration:?\s*", 0.36),
        (r"entire\s*agreement:?\s*", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Employment terms
        "employment",
        "employee",
        "employer",
        "job",
        "offer",
        "hire",
        "position",
        "role",
        "title",
        "department",
        "team",
        # Compensation
        "salary",
        "wage",
        "compensation",
        "pay",
        "bonus",
        "commission",
        "benefits",
        "insurance",
        "vacation",
        "pto",
        "401k",
        "equity",
        # Legal terms
        "agreement",
        "contract",
        "terms",
        "conditions",
        "at-will",
        "terminate",
        "termination",
        "severance",
        "notice",
        # Restrictions
        "non-compete",
        "non-solicitation",
        "confidential",
        "proprietary",
        "intellectual",
        "property",
        "invention",
    },
    filename_patterns={
        "employment": 0.75,
        "offer": 0.72,
        "offer_letter": 0.76,
        "employment_agreement": 0.78,
        "job_offer": 0.74,
        "contract": 0.68,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Lease patterns
        r"monthly\s*rent",
        r"security\s*deposit",
        r"landlord",
        r"tenant",
        # Service patterns
        r"scope\s*of\s*services",
        r"deliverables",
        r"milestone",
        r"invoice",
        # Purchase patterns
        r"purchase\s*price",
        r"bill\s*of\s*sale",
        # Pure NDA patterns
        r"solely\s*for\s*the\s*purpose\s*of\s*evaluating",
        r"mutual\s*non-disclosure",
    },
    exclude_phrases={
        "lease agreement",
        "service agreement",
        "purchase agreement",
        "consulting agreement",
    },
)

# Service Contract - Service agreements and consulting contracts
SERVICE_CONTRACT = SubthemeRule(
    name="service_contract",
    display_name="Service Contract",
    parent_theme="Legal",
    subtheme_category="Contracts and Agreements",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core service patterns
        (r"service\s*(?:agreement|contract)", 0.95, "service_agreement_header"),
        (r"consulting\s*(?:agreement|contract)", 0.93, "consulting_agreement"),
        (r"professional\s*services\s*agreement", 0.92, "professional_services"),
        (r"vendor\s*(?:agreement|contract)", 0.91, "vendor_agreement"),
        (r"contractor\s*agreement", 0.90, "contractor_agreement"),
        (r"independent\s*contractor", 0.89, "independent_contractor"),
        # Scope patterns
        (r"scope\s*of\s*(?:work|services)", 0.90, "scope_of_work"),
        (r"statement\s*of\s*work", 0.89, "statement_of_work"),
        (r"deliverables:?\s*", 0.87, "deliverables_section"),
        (r"services\s*to\s*be\s*(?:provided|performed)", 0.86, "services_provided"),
        # Payment patterns
        (r"(?:hourly|daily)\s*rate:?\s*\$?[\d,]+", 0.88, "hourly_rate"),
        (r"project\s*fee:?\s*\$?[\d,]+", 0.87, "project_fee"),
        (r"retainer:?\s*\$?[\d,]+", 0.86, "retainer_fee"),
        (r"milestone\s*payment", 0.85, "milestone_payment"),
        (r"invoice\s*(?:terms|schedule)", 0.84, "invoice_terms"),
        # Timeline patterns
        (r"project\s*timeline", 0.85, "project_timeline"),
        (
            r"completion\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            0.84,
            "completion_date",
        ),
        (r"milestone\s*(?:dates?|schedule)", 0.83, "milestone_schedule"),
    ],
    definitive_phrases={
        # Core service phrases
        "service agreement": 0.95,
        "service contract": 0.94,
        "consulting agreement": 0.93,
        "professional services": 0.92,
        "vendor agreement": 0.91,
        "contractor agreement": 0.90,
        "master service agreement": 0.91,
        "msa": 0.88,
        # Parties
        "service provider": 0.89,
        "client and contractor": 0.88,
        "vendor and customer": 0.87,
        "consultant and client": 0.88,
        # Scope terms
        "scope of work": 0.90,
        "scope of services": 0.90,
        "statement of work": 0.89,
        "sow": 0.87,
        "deliverables": 0.86,
        "project requirements": 0.85,
        # Payment terms
        "payment terms": 0.86,
        "hourly rate": 0.85,
        "project fee": 0.85,
        "net 30": 0.83,
        "net 60": 0.83,
        "upon completion": 0.84,
        # Performance terms
        "service level agreement": 0.87,
        "sla": 0.85,
        "performance standards": 0.84,
        "acceptance criteria": 0.84,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Service sections
        (r"services:?\s*", 0.48),
        (r"responsibilities:?\s*", 0.46),
        (r"timeline:?\s*", 0.44),
        (r"milestones?:?\s*", 0.44),
        (r"payment\s*schedule:?\s*", 0.46),
        # Terms
        (r"term\s*and\s*termination:?\s*", 0.42),
        (r"warranties:?\s*", 0.40),
        (r"indemnification:?\s*", 0.40),
        (r"limitation\s*of\s*liability:?\s*", 0.38),
        # Legal
        (r"governing\s*law:?\s*", 0.38),
        (r"dispute\s*resolution:?\s*", 0.36),
        (r"entire\s*agreement:?\s*", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Service terms
        "service",
        "services",
        "consulting",
        "consultant",
        "contractor",
        "vendor",
        "provider",
        "professional",
        "freelance",
        # Scope terms
        "scope",
        "deliverable",
        "milestone",
        "project",
        "task",
        "requirement",
        "specification",
        "timeline",
        "deadline",
        # Payment terms
        "payment",
        "invoice",
        "rate",
        "fee",
        "retainer",
        "expense",
        "reimbursement",
        "billing",
        "hourly",
        "fixed",
        # Legal terms
        "agreement",
        "contract",
        "terms",
        "conditions",
        "warranty",
        "indemnity",
        "liability",
        "termination",
        "breach",
    },
    filename_patterns={
        "service": 0.74,
        "consulting": 0.73,
        "service_agreement": 0.77,
        "consulting_agreement": 0.76,
        "vendor": 0.71,
        "contractor": 0.72,
        "sow": 0.70,
        "msa": 0.71,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Lease patterns
        r"monthly\s*rent",
        r"security\s*deposit",
        r"landlord",
        # Employment patterns
        r"employee\s*benefits",
        r"annual\s*salary",
        r"w-?2\s*form",
        r"at-will\s*employment",
        # Purchase patterns
        r"purchase\s*price",
        r"bill\s*of\s*sale",
        r"transfer\s*of\s*ownership",
        # NDA patterns
        r"solely\s*for\s*the\s*purpose\s*of\s*evaluating",
        r"confidential\s*information\s*only",
    },
    exclude_phrases={
        "lease agreement",
        "employment agreement",
        "purchase agreement",
        "non-disclosure agreement",
    },
)

# Purchase Agreement - Sales contracts and purchase orders
PURCHASE_AGREEMENT = SubthemeRule(
    name="purchase_agreement",
    display_name="Purchase Agreement",
    parent_theme="Legal",
    subtheme_category="Contracts and Agreements",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core purchase patterns
        (r"purchase\s*(?:agreement|contract)", 0.95, "purchase_agreement_header"),
        (r"sales\s*(?:agreement|contract)", 0.94, "sales_agreement"),
        (r"bill\s*of\s*sale", 0.93, "bill_of_sale"),
        (r"purchase\s*order", 0.91, "purchase_order"),
        (r"(?:buyer|purchaser)\s*and\s*(?:seller|vendor)", 0.90, "buyer_seller"),
        (r"asset\s*purchase\s*agreement", 0.89, "asset_purchase"),
        # Price and payment patterns
        (r"purchase\s*price:?\s*\$?[\d,]+(?:\.\d{2})?", 0.90, "purchase_price"),
        (r"total\s*(?:price|amount):?\s*\$?[\d,]+(?:\.\d{2})?", 0.88, "total_price"),
        (r"down\s*payment:?\s*\$?[\d,]+", 0.87, "down_payment"),
        (r"payment\s*terms:?\s*", 0.86, "payment_terms"),
        (r"closing\s*date:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", 0.85, "closing_date"),
        # Item/property descriptions
        (r"(?:item|property)\s*description:?\s*", 0.86, "item_description"),
        (r"serial\s*number:?\s*[A-Z0-9\-]+", 0.84, "serial_number"),
        (r"model\s*(?:number|#):?\s*[A-Z0-9\-]+", 0.83, "model_number"),
        (r"quantity:?\s*\d+", 0.82, "quantity"),
        # Transfer and warranty patterns
        (r"transfer\s*of\s*(?:title|ownership)", 0.88, "transfer_of_ownership"),
        (r"warranty\s*(?:period|terms)", 0.85, "warranty_terms"),
        (r"as[\s-]is\s*(?:condition|basis)", 0.84, "as_is_condition"),
        (r"condition\s*of\s*(?:goods|property)", 0.83, "condition_of_goods"),
    ],
    definitive_phrases={
        # Core purchase phrases
        "purchase agreement": 0.95,
        "sales agreement": 0.94,
        "sales contract": 0.93,
        "bill of sale": 0.93,
        "purchase order": 0.91,
        "purchase contract": 0.92,
        "asset purchase": 0.89,
        # Parties
        "buyer and seller": 0.90,
        "purchaser and vendor": 0.89,
        "seller agrees": 0.86,
        "buyer agrees": 0.86,
        # Price terms
        "purchase price": 0.90,
        "sale price": 0.89,
        "total amount": 0.86,
        "payment due": 0.85,
        "earnest money": 0.84,
        "deposit amount": 0.84,
        # Transfer terms
        "transfer of ownership": 0.88,
        "transfer of title": 0.88,
        "delivery date": 0.85,
        "closing date": 0.85,
        "possession date": 0.84,
        # Condition terms
        "as is": 0.84,
        "warranty included": 0.83,
        "no warranty": 0.83,
        "condition of sale": 0.84,
        "inspection period": 0.83,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Purchase sections
        (r"description\s*of\s*(?:goods|property):?\s*", 0.48),
        (r"purchase\s*price:?\s*", 0.48),
        (r"payment\s*method:?\s*", 0.44),
        (r"delivery\s*terms:?\s*", 0.44),
        (r"closing\s*conditions:?\s*", 0.42),
        # Warranty sections
        (r"warranties\s*and\s*representations:?\s*", 0.42),
        (r"disclaimer:?\s*", 0.38),
        (r"limitation\s*of\s*liability:?\s*", 0.38),
        # Legal sections
        (r"governing\s*law:?\s*", 0.38),
        (r"risk\s*of\s*loss:?\s*", 0.36),
        (r"entire\s*agreement:?\s*", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Purchase terms
        "purchase",
        "sale",
        "sales",
        "buy",
        "sell",
        "buyer",
        "seller",
        "vendor",
        "purchaser",
        "acquisition",
        # Item terms
        "goods",
        "property",
        "asset",
        "item",
        "product",
        "merchandise",
        "equipment",
        "vehicle",
        "real estate",
        # Financial terms
        "price",
        "payment",
        "deposit",
        "earnest",
        "closing",
        "escrow",
        "financing",
        "cash",
        "installment",
        # Legal terms
        "agreement",
        "contract",
        "bill",
        "transfer",
        "title",
        "ownership",
        "warranty",
        "condition",
        "inspection",
        "delivery",
    },
    filename_patterns={
        "purchase": 0.75,
        "sales": 0.74,
        "purchase_agreement": 0.78,
        "sales_agreement": 0.77,
        "bill_of_sale": 0.76,
        "purchase_order": 0.74,
        "po": 0.68,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Lease patterns
        r"monthly\s*rent",
        r"security\s*deposit",
        r"lease\s*term",
        r"landlord",
        # Employment patterns
        r"employment\s*agreement",
        r"annual\s*salary",
        r"employee\s*benefits",
        # Service patterns
        r"scope\s*of\s*services",
        r"consulting\s*services",
        r"hourly\s*rate",
        # NDA patterns
        r"confidential\s*information",
        r"non-disclosure",
    },
    exclude_phrases={
        "lease agreement",
        "employment agreement",
        "service agreement",
        "non-disclosure agreement",
    },
)

# NDA - Non-disclosure and confidentiality agreements
NDA = SubthemeRule(
    name="nda",
    display_name="NDA",
    parent_theme="Legal",
    subtheme_category="Contracts and Agreements",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core NDA patterns
        (r"non[\s-]?disclosure\s*agreement", 0.95, "nda_header"),
        (r"confidentiality\s*agreement", 0.94, "confidentiality_agreement"),
        (r"nda", 0.92, "nda_abbreviation"),
        (r"mutual\s*non[\s-]?disclosure", 0.91, "mutual_nda"),
        (r"confidential\s*disclosure\s*agreement", 0.90, "cda"),
        # Confidentiality patterns
        (r"confidential\s*information", 0.88, "confidential_information"),
        (r"proprietary\s*information", 0.87, "proprietary_information"),
        (r"trade\s*secrets?", 0.86, "trade_secrets"),
        (r"(?:disclosing|receiving)\s*party", 0.89, "party_designation"),
        # Purpose patterns
        (r"for\s*the\s*purpose\s*of\s*evaluating", 0.87, "evaluation_purpose"),
        (r"business\s*relationship", 0.85, "business_relationship"),
        (r"potential\s*(?:transaction|partnership)", 0.84, "potential_transaction"),
        # Obligation patterns
        (r"shall\s*(?:not\s*)?disclose", 0.86, "disclosure_obligation"),
        (r"maintain\s*(?:in\s*)?confidence", 0.85, "maintain_confidence"),
        (r"protect\s*(?:the\s*)?confidentiality", 0.84, "protect_confidentiality"),
        (r"use\s*solely\s*for", 0.83, "use_restriction"),
    ],
    definitive_phrases={
        # Core NDA phrases
        "non-disclosure agreement": 0.95,
        "nondisclosure agreement": 0.95,
        "confidentiality agreement": 0.94,
        "nda": 0.92,
        "mutual nda": 0.91,
        "unilateral nda": 0.90,
        "confidential disclosure agreement": 0.90,
        "cda": 0.88,
        # Parties
        "disclosing party": 0.89,
        "receiving party": 0.89,
        "recipient": 0.86,
        "discloser": 0.86,
        # Confidentiality terms
        "confidential information": 0.90,
        "proprietary information": 0.88,
        "trade secrets": 0.87,
        "sensitive information": 0.85,
        "non-public information": 0.85,
        # Obligations
        "shall not disclose": 0.87,
        "maintain in confidence": 0.86,
        "protect confidentiality": 0.85,
        "hold in confidence": 0.85,
        "keep confidential": 0.85,
        # Purpose
        "for the purpose of": 0.84,
        "evaluating a potential": 0.83,
        "business relationship": 0.83,
        # Duration
        "term of agreement": 0.82,
        "survival period": 0.81,
        "remains confidential": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # NDA sections
        (r"definition\s*of\s*confidential\s*information:?\s*", 0.48),
        (r"purpose:?\s*", 0.44),
        (r"obligations:?\s*", 0.46),
        (r"exceptions:?\s*", 0.44),
        (r"term:?\s*", 0.42),
        # Exceptions
        (r"publicly\s*(?:available|known)", 0.42),
        (r"independently\s*developed", 0.40),
        (r"rightfully\s*received", 0.40),
        (r"required\s*by\s*law", 0.38),
        # Legal sections
        (r"governing\s*law:?\s*", 0.38),
        (r"return\s*of\s*(?:information|materials):?\s*", 0.40),
        (r"no\s*license:?\s*", 0.36),
        (r"remedies:?\s*", 0.36),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # NDA terms
        "nda",
        "confidential",
        "confidentiality",
        "non-disclosure",
        "nondisclosure",
        "proprietary",
        "secret",
        "sensitive",
        # Party terms
        "disclosing",
        "receiving",
        "party",
        "recipient",
        "discloser",
        # Information terms
        "information",
        "data",
        "materials",
        "documents",
        "knowledge",
        "trade",
        "secrets",
        "know-how",
        "intellectual",
        # Obligation terms
        "disclose",
        "protect",
        "maintain",
        "safeguard",
        "restrict",
        "prohibit",
        "prevent",
        "unauthorized",
        # Legal terms
        "agreement",
        "contract",
        "obligation",
        "breach",
        "remedy",
        "injunction",
        "damages",
        "term",
        "survival",
    },
    filename_patterns={
        "nda": 0.78,
        "confidentiality": 0.76,
        "non_disclosure": 0.77,
        "nondisclosure": 0.77,
        "confidential": 0.72,
        "cda": 0.74,
        "mutual_nda": 0.76,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Lease patterns
        r"monthly\s*rent",
        r"security\s*deposit",
        r"landlord",
        # Employment patterns (unless part of employment NDA)
        r"annual\s*salary",
        r"job\s*title",
        r"employee\s*benefits",
        # Service patterns
        r"scope\s*of\s*services",
        r"deliverables",
        r"milestone\s*payment",
        # Purchase patterns
        r"purchase\s*price",
        r"bill\s*of\s*sale",
        r"transfer\s*of\s*title",
    },
    exclude_phrases={
        "lease agreement",
        "employment agreement",  # Unless it's an employment NDA
        "service agreement",
        "purchase agreement",
    },
)

# Export rules
CONTRACTS_AGREEMENTS_SUBTHEME_RULES: List[SubthemeRule] = [
    LEASE_AGREEMENT,
    EMPLOYMENT_AGREEMENT,
    SERVICE_CONTRACT,
    PURCHASE_AGREEMENT,
    NDA,
]

CONTRACTS_AGREEMENTS_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in CONTRACTS_AGREEMENTS_SUBTHEME_RULES
}
