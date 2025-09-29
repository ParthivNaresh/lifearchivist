"""
Legal > Estate and Family subtheme rules.

Defines precise, production-ready patterns for:
- Will
- Power of Attorney
- Trust Document
- Divorce Document
- Marriage Certificate

These rules use the SubthemeRule data structure with a cascade-friendly layout.
"""

from typing import Dict, List

from lifearchivist.tools.subtheme_classifier.rules.base import SubthemeRule

# Will - Last will and testament, codicils, estate plans
WILL = SubthemeRule(
    name="will",
    display_name="Will",
    parent_theme="Legal",
    subtheme_category="Estate and Family",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core will patterns (highly distinctive)
        (r"last\s*will\s*and\s*testament", 0.95, "last_will_testament"),
        (r"(?:this\s*is\s*)?(?:the\s*)?last\s*will\s*of", 0.93, "last_will_of"),
        (
            r"i[,\s]+[A-Z][a-z]+.*being\s*of\s*sound\s*mind",
            0.92,
            "sound_mind_declaration",
        ),
        (r"testamentary\s*(?:document|instrument)", 0.90, "testamentary_document"),
        (r"codicil\s*to\s*(?:the\s*)?(?:last\s*)?will", 0.89, "codicil"),
        # Testator patterns (unique to wills)
        (r"testator:?\s*[A-Z][a-z]+", 0.88, "testator_name"),
        (r"testatrix:?\s*[A-Z][a-z]+", 0.88, "testatrix_name"),
        (r"i\s*hereby\s*(?:revoke|declare)", 0.87, "hereby_declare"),
        (r"revoke\s*all\s*(?:prior|former)\s*wills", 0.86, "revoke_prior_wills"),
        # Beneficiary and bequest patterns
        (r"(?:i\s*)?(?:give|devise|bequeath)", 0.87, "bequest_language"),
        (r"beneficiar(?:y|ies):?\s*", 0.86, "beneficiary_designation"),
        (r"residuary\s*estate", 0.85, "residuary_estate"),
        (r"(?:specific|general)\s*bequest", 0.84, "bequest_type"),
        # Executor patterns (will-specific)
        (r"(?:i\s*)?(?:appoint|nominate).*executor", 0.88, "executor_appointment"),
        (r"personal\s*representative", 0.86, "personal_representative"),
        (
            r"executor\s*(?:of\s*(?:this\s*)?(?:my\s*)?(?:estate|will))",
            0.85,
            "executor_designation",
        ),
        # Will execution patterns
        (r"witness(?:ed|es)\s*(?:signature|by)", 0.84, "witness_signature"),
        (
            r"signed\s*(?:and\s*)?sealed\s*(?:and\s*)?delivered",
            0.83,
            "signed_sealed_delivered",
        ),
        (r"in\s*witness\s*whereof", 0.83, "in_witness_whereof"),
    ],
    definitive_phrases={
        # Core will phrases (highly distinctive)
        "last will and testament": 0.95,
        "last will": 0.93,
        "testament": 0.90,
        "codicil": 0.89,
        "testamentary": 0.88,
        # Testator phrases
        "sound mind": 0.89,
        "sound mind and body": 0.88,
        "testator": 0.87,
        "testatrix": 0.87,
        "hereby revoke": 0.86,
        "prior wills": 0.85,
        # Distribution phrases
        "i give and bequeath": 0.88,
        "devise and bequeath": 0.87,
        "residuary estate": 0.86,
        "remainder of my estate": 0.85,
        "distribute my estate": 0.84,
        "estate planning": 0.83,
        # Executor phrases
        "executor of my estate": 0.87,
        "executor of this will": 0.87,
        "personal representative": 0.86,
        "estate administrator": 0.85,
        "appoint as executor": 0.85,
        # Legal phrases specific to wills
        "probate": 0.84,
        "letters testamentary": 0.83,
        "intestate succession": 0.82,
        "per stirpes": 0.82,
        "per capita": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Will sections
        (r"article\s*[IVX]+:?\s*", 0.45),
        (r"bequests:?\s*", 0.48),
        (r"specific\s*gifts:?\s*", 0.46),
        (r"residuary\s*clause:?\s*", 0.46),
        (r"executor\s*powers:?\s*", 0.44),
        # Family references
        (r"(?:spouse|wife|husband):?\s*", 0.42),
        (r"children:?\s*", 0.42),
        (r"descendants:?\s*", 0.40),
        (r"heirs:?\s*", 0.40),
        # Legal formalities
        (r"witnesses:?\s*", 0.42),
        (r"notary:?\s*", 0.38),
        (r"attestation\s*clause:?\s*", 0.40),
        (r"self-proving\s*affidavit:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Will-specific primary terms
        "will",
        "testament",
        "testamentary",
        "codicil",
        "testator",
        "testatrix",
        "probate",
        "estate",
        # Distribution terms
        "bequeath",
        "devise",
        "inherit",
        "inheritance",
        "beneficiary",
        "heir",
        "legatee",
        "bequest",
        "legacy",
        "residuary",
        # Executor terms
        "executor",
        "executrix",
        "administrator",
        "personal",
        "representative",
        # Family terms (will context)
        "spouse",
        "children",
        "descendants",
        "issue",
        "surviving",
        "predeceased",
        "per stirpes",
        "per capita",
        # Legal terms specific to wills
        "witness",
        "attestation",
        "revoke",
        "supersede",
        "void",
        "contest",
        "undue",
        "influence",
        "capacity",
    },
    filename_patterns={
        "will": 0.78,
        "last_will": 0.80,
        "testament": 0.75,
        "codicil": 0.74,
        "estate_plan": 0.72,
        "lwt": 0.70,  # Last Will & Testament abbreviation
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Power of Attorney patterns
        r"attorney[\s-]in[\s-]fact",
        r"principal\s*grants",
        r"healthcare\s*decisions",
        r"financial\s*decisions",
        # Trust patterns
        r"trustee\s*shall",
        r"trust\s*estate",
        r"revocable\s*trust",
        r"trust\s*agreement",
        # Divorce patterns
        r"dissolution\s*of\s*marriage",
        r"custody\s*arrangement",
        r"spousal\s*support",
        # Marriage patterns
        r"marriage\s*certificate",
        r"prenuptial\s*agreement",
        r"marriage\s*license",
    },
    exclude_phrases={
        "power of attorney",
        "living will",
        "trust agreement",
        "divorce decree",
        "marriage certificate",
    },
)

# Power of Attorney - Financial POA, healthcare POA, living wills, advance directives
POWER_OF_ATTORNEY = SubthemeRule(
    name="power_of_attorney",
    display_name="Power of Attorney",
    parent_theme="Legal",
    subtheme_category="Estate and Family",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core POA patterns (highly distinctive)
        (r"(?:durable\s*)?power\s*of\s*attorney", 0.95, "power_of_attorney_header"),
        (r"(?:medical|healthcare)\s*power\s*of\s*attorney", 0.94, "healthcare_poa"),
        (r"(?:financial|general)\s*power\s*of\s*attorney", 0.93, "financial_poa"),
        (r"advance\s*(?:healthcare\s*)?directive", 0.92, "advance_directive"),
        (r"living\s*will", 0.91, "living_will"),
        (r"healthcare\s*proxy", 0.90, "healthcare_proxy"),
        # Principal and agent patterns (POA-specific)
        (r"principal:?\s*[A-Z][a-z]+", 0.89, "principal_name"),
        (r"attorney[\s-]in[\s-]fact:?\s*[A-Z][a-z]+", 0.88, "attorney_in_fact"),
        (
            r"(?:i|principal)\s*(?:hereby\s*)?(?:appoint|designate)",
            0.87,
            "appointment_language",
        ),
        (r"agent\s*(?:is\s*)?authorized\s*to", 0.86, "agent_authorization"),
        # Authority grant patterns
        (r"(?:grant|give).*(?:full\s*)?authority", 0.87, "grant_authority"),
        (r"act\s*(?:on\s*)?(?:my|principal'?s?)\s*behalf", 0.86, "act_on_behalf"),
        (
            r"make\s*(?:healthcare|medical|financial)\s*decisions",
            0.85,
            "decision_authority",
        ),
        (r"effective\s*(?:immediately|upon)", 0.84, "effective_clause"),
        # Healthcare-specific patterns
        (r"life[\s-]sustaining\s*(?:treatment|measures)", 0.86, "life_sustaining"),
        (r"end[\s-]of[\s-]life\s*(?:care|decisions)", 0.85, "end_of_life"),
        (r"medical\s*treatment\s*(?:decisions|preferences)", 0.84, "medical_treatment"),
        (r"do\s*not\s*resuscitate", 0.83, "dnr"),
        # Durability patterns
        (r"(?:remains?|continue)\s*in\s*effect", 0.84, "remains_in_effect"),
        (r"(?:mental\s*)?incapacit(?:y|ation)", 0.83, "incapacity"),
        (r"(?:durable|survives?)\s*(?:disability|incapacity)", 0.83, "durable_clause"),
    ],
    definitive_phrases={
        # Core POA phrases
        "power of attorney": 0.95,
        "durable power of attorney": 0.94,
        "healthcare power of attorney": 0.93,
        "financial power of attorney": 0.93,
        "living will": 0.91,
        "advance directive": 0.92,
        "healthcare proxy": 0.90,
        # Party designations
        "attorney-in-fact": 0.90,
        "attorney in fact": 0.90,
        "principal": 0.87,
        "agent": 0.85,
        "healthcare agent": 0.86,
        "financial agent": 0.86,
        # Authority phrases
        "grant authority": 0.87,
        "act on my behalf": 0.86,
        "act on behalf of": 0.86,
        "make decisions": 0.84,
        "full authority": 0.85,
        "limited authority": 0.84,
        # Healthcare-specific phrases
        "medical decisions": 0.85,
        "healthcare decisions": 0.85,
        "life-sustaining treatment": 0.84,
        "end-of-life care": 0.84,
        "artificial nutrition": 0.83,
        "do not resuscitate": 0.83,
        "comfort care": 0.82,
        # Durability phrases
        "survives incapacity": 0.84,
        "remains in effect": 0.83,
        "mental incapacity": 0.83,
        "becomes effective": 0.82,
        "springing power": 0.82,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # POA sections
        (r"powers\s*granted:?\s*", 0.48),
        (r"specific\s*powers:?\s*", 0.46),
        (r"limitations:?\s*", 0.44),
        (r"effective\s*date:?\s*", 0.44),
        (r"termination:?\s*", 0.42),
        # Healthcare sections
        (r"medical\s*treatment:?\s*", 0.44),
        (r"life[\s-]support:?\s*", 0.42),
        (r"organ\s*donation:?\s*", 0.40),
        (r"burial\s*instructions:?\s*", 0.38),
        # Financial sections
        (r"banking\s*transactions:?\s*", 0.42),
        (r"real\s*estate:?\s*", 0.40),
        (r"investments:?\s*", 0.40),
        (r"tax\s*matters:?\s*", 0.38),
        # Legal formalities
        (r"witnesses:?\s*", 0.40),
        (r"notarization:?\s*", 0.38),
        (r"acknowledgment:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # POA-specific primary terms
        "power",
        "attorney",
        "poa",
        "proxy",
        "agent",
        "principal",
        "attorney-in-fact",
        "directive",
        "living",
        # Authority terms
        "authority",
        "authorize",
        "grant",
        "appoint",
        "designate",
        "behalf",
        "act",
        "represent",
        "decisions",
        # Healthcare terms (POA context)
        "healthcare",
        "medical",
        "health",
        "treatment",
        "life-sustaining",
        "resuscitate",
        "dnr",
        "comfort",
        "hospice",
        "palliative",
        # Financial terms (POA context)
        "financial",
        "banking",
        "transactions",
        "assets",
        "property",
        "investments",
        "accounts",
        # Durability terms
        "durable",
        "incapacity",
        "disability",
        "incompetent",
        "effective",
        "springing",
        "immediate",
        "survives",
    },
    filename_patterns={
        "poa": 0.78,
        "power_of_attorney": 0.80,
        "power_attorney": 0.78,
        "living_will": 0.76,
        "advance_directive": 0.75,
        "healthcare_proxy": 0.74,
        "dpoa": 0.72,  # Durable POA
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Will patterns
        r"last\s*will\s*and\s*testament",
        r"bequeath",
        r"residuary\s*estate",
        r"testator",
        # Trust patterns
        r"trust\s*agreement",
        r"trustee\s*powers",
        r"trust\s*corpus",
        r"beneficiaries\s*of\s*(?:the\s*)?trust",
        # Divorce patterns
        r"dissolution\s*of\s*marriage",
        r"custody\s*arrangement",
        r"child\s*support",
        # Marriage patterns
        r"marriage\s*certificate",
        r"prenuptial\s*agreement",
    },
    exclude_phrases={
        "last will",
        "trust agreement",
        "divorce decree",
        "marriage certificate",
        "prenuptial agreement",
    },
)

# Trust Document - Living trusts, revocable trusts, trust amendments
TRUST_DOCUMENT = SubthemeRule(
    name="trust_document",
    display_name="Trust Document",
    parent_theme="Legal",
    subtheme_category="Estate and Family",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core trust patterns (highly distinctive)
        (r"(?:revocable|irrevocable)\s*(?:living\s*)?trust", 0.95, "trust_type"),
        (r"trust\s*agreement", 0.93, "trust_agreement"),
        (r"declaration\s*of\s*trust", 0.92, "declaration_of_trust"),
        (r"trust\s*indenture", 0.90, "trust_indenture"),
        (r"(?:living|inter\s*vivos)\s*trust", 0.91, "living_trust"),
        (r"trust\s*amendment", 0.89, "trust_amendment"),
        # Trust party patterns (trust-specific)
        (r"(?:grantor|settlor|trustor):?\s*[A-Z][a-z]+", 0.89, "grantor_name"),
        (r"trustee:?\s*[A-Z][a-z]+", 0.88, "trustee_name"),
        (r"(?:successor|alternate)\s*trustee", 0.87, "successor_trustee"),
        (r"beneficiar(?:y|ies)\s*of\s*(?:the\s*)?trust", 0.86, "trust_beneficiaries"),
        # Trust property patterns
        (r"trust\s*(?:property|estate|corpus|res)", 0.87, "trust_property"),
        (r"(?:transfer|convey)\s*to\s*(?:the\s*)?trust", 0.86, "transfer_to_trust"),
        (r"trust\s*assets", 0.85, "trust_assets"),
        (r"schedule\s*[A-Z]\s*(?:property|assets)", 0.84, "property_schedule"),
        # Trust administration patterns
        (
            r"trustee\s*(?:shall\s*)?(?:have\s*)?(?:the\s*)?power",
            0.86,
            "trustee_powers",
        ),
        (r"fiduciary\s*(?:duty|duties|responsibility)", 0.85, "fiduciary_duty"),
        (r"distribute\s*(?:trust\s*)?(?:income|principal)", 0.84, "distribution_terms"),
        (
            r"(?:during|after)\s*(?:grantor'?s?|settlor'?s?)\s*(?:lifetime|death)",
            0.83,
            "timing_provisions",
        ),
        # Revocability patterns
        (r"(?:may|can)\s*(?:be\s*)?(?:revoked|amended)", 0.85, "revocability"),
        (r"right\s*to\s*(?:revoke|amend|modify)", 0.84, "modification_rights"),
        (r"restatement\s*of\s*trust", 0.83, "trust_restatement"),
    ],
    definitive_phrases={
        # Core trust phrases
        "trust agreement": 0.94,
        "revocable trust": 0.93,
        "irrevocable trust": 0.93,
        "living trust": 0.92,
        "inter vivos trust": 0.91,
        "declaration of trust": 0.92,
        "trust amendment": 0.90,
        "trust restatement": 0.89,
        # Party designations
        "grantor": 0.89,
        "settlor": 0.89,
        "trustor": 0.88,
        "trustee": 0.88,
        "successor trustee": 0.87,
        "co-trustee": 0.86,
        "trust beneficiary": 0.86,
        # Trust property phrases
        "trust estate": 0.87,
        "trust corpus": 0.87,
        "trust res": 0.86,
        "trust property": 0.86,
        "trust assets": 0.85,
        "funded trust": 0.84,
        # Administration phrases
        "trustee powers": 0.86,
        "fiduciary duty": 0.85,
        "trust administration": 0.85,
        "discretionary distributions": 0.84,
        "mandatory distributions": 0.84,
        "spendthrift provision": 0.83,
        # Legal phrases specific to trusts
        "avoid probate": 0.84,
        "pour-over will": 0.83,
        "trust protector": 0.82,
        "rule against perpetuities": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Trust sections
        (r"article\s*[IVX]+:?\s*", 0.44),
        (r"trust\s*purpose:?\s*", 0.46),
        (r"trustee\s*powers:?\s*", 0.48),
        (r"distributions:?\s*", 0.46),
        (r"trust\s*property:?\s*", 0.46),
        # Administrative sections
        (r"accounting:?\s*", 0.42),
        (r"trust\s*administration:?\s*", 0.44),
        (r"successor\s*trustees:?\s*", 0.42),
        (r"resignation:?\s*", 0.40),
        # Legal provisions
        (r"governing\s*law:?\s*", 0.38),
        (r"severability:?\s*", 0.36),
        (r"spendthrift\s*clause:?\s*", 0.40),
        (r"no\s*contest\s*clause:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Trust-specific primary terms
        "trust",
        "trustee",
        "grantor",
        "settlor",
        "trustor",
        "beneficiary",
        "fiduciary",
        "corpus",
        "res",
        # Trust types
        "revocable",
        "irrevocable",
        "living",
        "testamentary",
        "charitable",
        "special",
        "needs",
        "spendthrift",
        # Administration terms
        "administer",
        "distribute",
        "distribution",
        "principal",
        "income",
        "discretionary",
        "mandatory",
        "powers",
        # Property terms (trust context)
        "assets",
        "property",
        "estate",
        "transfer",
        "convey",
        "fund",
        "funding",
        "schedule",
        # Legal terms specific to trusts
        "probate",
        "avoid",
        "pour-over",
        "restatement",
        "amendment",
        "modification",
        "perpetuities",
    },
    filename_patterns={
        "trust": 0.78,
        "living_trust": 0.80,
        "revocable_trust": 0.78,
        "trust_agreement": 0.77,
        "trust_amendment": 0.75,
        "declaration_trust": 0.74,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Will patterns
        r"last\s*will\s*and\s*testament",
        r"i\s*.*being\s*of\s*sound\s*mind",
        r"testator",
        r"executor\s*of\s*(?:my\s*)?estate",
        # POA patterns
        r"power\s*of\s*attorney",
        r"attorney[\s-]in[\s-]fact",
        r"act\s*on\s*(?:my\s*)?behalf",
        # Divorce patterns
        r"dissolution\s*of\s*marriage",
        r"custody\s*arrangement",
        r"spousal\s*support",
        # Marriage patterns
        r"marriage\s*certificate",
        r"prenuptial\s*agreement",
    },
    exclude_phrases={
        "last will",
        "power of attorney",
        "divorce decree",
        "marriage certificate",
        "prenuptial agreement",
    },
)

# Divorce Document - Divorce decrees, separation agreements, custody orders
DIVORCE_DOCUMENT = SubthemeRule(
    name="divorce_document",
    display_name="Divorce Document",
    parent_theme="Legal",
    subtheme_category="Estate and Family",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core divorce patterns (highly distinctive)
        (r"(?:final\s*)?(?:decree|judgment)\s*of\s*divorce", 0.95, "divorce_decree"),
        (r"dissolution\s*of\s*marriage", 0.94, "dissolution_of_marriage"),
        (r"divorce\s*(?:decree|judgment|order)", 0.93, "divorce_order"),
        (r"marital\s*settlement\s*agreement", 0.92, "marital_settlement"),
        (r"(?:legal\s*)?separation\s*agreement", 0.91, "separation_agreement"),
        (r"divorce\s*petition", 0.90, "divorce_petition"),
        # Party patterns (divorce-specific)
        (r"petitioner:?\s*[A-Z][a-z]+", 0.88, "petitioner_name"),
        (r"respondent:?\s*[A-Z][a-z]+", 0.88, "respondent_name"),
        (r"(?:husband|wife)\s*and\s*(?:wife|husband)", 0.87, "husband_wife"),
        (r"irreconcilable\s*differences", 0.86, "irreconcilable_differences"),
        # Custody patterns
        (r"(?:child|children)\s*custody", 0.88, "child_custody"),
        (r"(?:joint|sole)\s*(?:legal|physical)\s*custody", 0.87, "custody_type"),
        (r"parenting\s*(?:plan|time|schedule)", 0.86, "parenting_plan"),
        (r"visitation\s*(?:rights|schedule)", 0.85, "visitation_rights"),
        (r"best\s*interests?\s*of\s*(?:the\s*)?child(?:ren)?", 0.84, "best_interests"),
        # Support patterns
        (r"child\s*support", 0.87, "child_support"),
        (r"(?:spousal\s*support|alimony)", 0.86, "spousal_support"),
        (r"support\s*(?:amount|payment):?\s*\$?[\d,]+", 0.85, "support_amount"),
        (r"maintenance\s*(?:payment|obligation)", 0.84, "maintenance"),
        # Property division patterns
        (
            r"(?:division|distribution)\s*of\s*(?:marital\s*)?(?:property|assets)",
            0.86,
            "property_division",
        ),
        (r"community\s*property", 0.85, "community_property"),
        (r"equitable\s*distribution", 0.84, "equitable_distribution"),
        (r"marital\s*(?:assets|debts)", 0.83, "marital_assets"),
    ],
    definitive_phrases={
        # Core divorce phrases
        "decree of divorce": 0.95,
        "divorce decree": 0.94,
        "dissolution of marriage": 0.94,
        "divorce judgment": 0.93,
        "marital settlement agreement": 0.92,
        "separation agreement": 0.91,
        "divorce petition": 0.90,
        # Legal status phrases
        "marriage is dissolved": 0.90,
        "legally divorced": 0.89,
        "final decree": 0.88,
        "irreconcilable differences": 0.87,
        "irretrievable breakdown": 0.86,
        # Custody phrases
        "child custody": 0.88,
        "joint custody": 0.87,
        "sole custody": 0.87,
        "legal custody": 0.86,
        "physical custody": 0.86,
        "parenting time": 0.85,
        "visitation rights": 0.85,
        # Support phrases
        "child support": 0.87,
        "spousal support": 0.86,
        "alimony": 0.86,
        "support obligation": 0.85,
        "support payments": 0.84,
        # Property phrases
        "property division": 0.86,
        "marital property": 0.85,
        "separate property": 0.84,
        "community property": 0.84,
        "equitable distribution": 0.83,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Divorce sections
        (r"grounds\s*for\s*divorce:?\s*", 0.46),
        (r"custody\s*arrangement:?\s*", 0.48),
        (r"support\s*obligations:?\s*", 0.46),
        (r"property\s*division:?\s*", 0.46),
        (r"debt\s*allocation:?\s*", 0.44),
        # Legal provisions
        (r"restraining\s*orders?:?\s*", 0.42),
        (r"attorney'?s?\s*fees:?\s*", 0.40),
        (r"modification:?\s*", 0.40),
        (r"enforcement:?\s*", 0.38),
        # Court information
        (r"case\s*(?:number|no\.):?\s*", 0.42),
        (r"court:?\s*", 0.40),
        (r"judge:?\s*", 0.38),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Divorce-specific primary terms
        "divorce",
        "dissolution",
        "separation",
        "decree",
        "judgment",
        "marital",
        "settlement",
        "custody",
        "visitation",
        # Party terms
        "petitioner",
        "respondent",
        "husband",
        "wife",
        "spouse",
        "ex-husband",
        "ex-wife",
        "former",
        # Custody terms
        "parenting",
        "child",
        "children",
        "minor",
        "dependent",
        "guardian",
        # Support terms
        "support",
        "alimony",
        "maintenance",
        "obligation",
        "payment",
        "arrears",
        "modification",
        # Property terms (divorce context)
        "property",
        "assets",
        "debts",
        "division",
        "distribution",
        "community",
        "separate",
        "equitable",
    },
    filename_patterns={
        "divorce": 0.78,
        "divorce_decree": 0.80,
        "dissolution": 0.76,
        "separation": 0.74,
        "custody": 0.72,
        "settlement": 0.70,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Will patterns
        r"last\s*will\s*and\s*testament",
        r"testator",
        r"bequeath",
        # POA patterns
        r"power\s*of\s*attorney",
        r"attorney[\s-]in[\s-]fact",
        # Trust patterns
        r"trust\s*agreement",
        r"trustee",
        r"trust\s*corpus",
        # Marriage patterns
        r"marriage\s*certificate",
        r"marriage\s*license",
        r"prenuptial\s*agreement",
        r"solemnized",
    },
    exclude_phrases={
        "last will",
        "power of attorney",
        "trust agreement",
        "marriage certificate",
        "prenuptial agreement",
    },
)

# Marriage Certificate - Marriage licenses, prenuptial agreements
MARRIAGE_CERTIFICATE = SubthemeRule(
    name="marriage_certificate",
    display_name="Marriage Certificate",
    parent_theme="Legal",
    subtheme_category="Estate and Family",
    # Primary identifiers (high confidence 0.85-0.95)
    unique_patterns=[
        # Core marriage document patterns
        (r"marriage\s*certificate", 0.95, "marriage_certificate"),
        (r"marriage\s*license", 0.94, "marriage_license"),
        (r"certificate\s*of\s*marriage", 0.93, "certificate_of_marriage"),
        (r"prenuptial\s*agreement", 0.92, "prenuptial_agreement"),
        (r"premarital\s*agreement", 0.91, "premarital_agreement"),
        (r"antenuptial\s*agreement", 0.90, "antenuptial_agreement"),
        # Marriage ceremony patterns
        (r"(?:solemnized|celebrated)\s*(?:on|this)", 0.88, "solemnized"),
        (r"united\s*in\s*(?:holy\s*)?matrimony", 0.87, "united_matrimony"),
        (r"lawfully\s*(?:joined|married)", 0.86, "lawfully_married"),
        (r"officiant:?\s*[A-Z][a-z]+", 0.85, "officiant_name"),
        # Party patterns (marriage-specific)
        (r"(?:bride|groom):?\s*[A-Z][a-z]+", 0.87, "bride_groom_name"),
        (r"party\s*(?:a|1):?\s*[A-Z][a-z]+.*party\s*(?:b|2)", 0.86, "party_ab"),
        (r"(?:husband|wife)[\s-]to[\s-]be", 0.85, "spouse_to_be"),
        # Prenuptial-specific patterns
        (r"separate\s*property", 0.86, "separate_property"),
        (r"(?:financial\s*)?disclosure", 0.85, "financial_disclosure"),
        (r"waive\s*(?:all\s*)?(?:rights?|claims?)", 0.84, "waive_rights"),
        (
            r"(?:in\s*)?(?:the\s*)?event\s*of\s*(?:divorce|death)",
            0.83,
            "event_of_divorce",
        ),
        # Legal validation patterns
        (r"witness(?:es)?:?\s*[A-Z][a-z]+", 0.84, "witnesses"),
        (r"(?:state|county)\s*of\s*[A-Z][a-z]+", 0.83, "jurisdiction"),
        (r"license\s*(?:number|#):?\s*[A-Z0-9\-]+", 0.82, "license_number"),
    ],
    definitive_phrases={
        # Core marriage phrases
        "marriage certificate": 0.95,
        "marriage license": 0.94,
        "certificate of marriage": 0.93,
        "prenuptial agreement": 0.92,
        "premarital agreement": 0.91,
        "antenuptial agreement": 0.90,
        # Ceremony phrases
        "solemnized": 0.88,
        "holy matrimony": 0.87,
        "lawfully married": 0.87,
        "joined in marriage": 0.86,
        "marriage ceremony": 0.85,
        "wedding ceremony": 0.84,
        # Party designations
        "bride and groom": 0.87,
        "husband and wife": 0.86,
        "spouse": 0.84,
        "betrothed": 0.83,
        # Prenuptial phrases
        "separate property": 0.86,
        "financial disclosure": 0.85,
        "waiver of rights": 0.84,
        "property rights": 0.83,
        "spousal support waiver": 0.83,
        # Legal phrases
        "valid marriage": 0.84,
        "legal union": 0.83,
        "matrimonial": 0.82,
        "conjugal": 0.81,
    },
    # Secondary identifiers (weighted structure patterns 0.60-0.80)
    structure_patterns=[
        # Marriage certificate sections
        (r"date\s*of\s*marriage:?\s*", 0.46),
        (r"place\s*of\s*marriage:?\s*", 0.44),
        (r"officiant:?\s*", 0.42),
        (r"witnesses:?\s*", 0.42),
        # Prenuptial sections
        (r"property\s*rights:?\s*", 0.44),
        (r"financial\s*obligations:?\s*", 0.42),
        (r"spousal\s*support:?\s*", 0.40),
        (r"debt\s*responsibility:?\s*", 0.38),
        # Legal sections
        (r"governing\s*law:?\s*", 0.36),
        (r"severability:?\s*", 0.34),
    ],
    # Tertiary identifiers (keywords and filename hints 0.40-0.70)
    keywords={
        # Marriage-specific primary terms
        "marriage",
        "wedding",
        "matrimony",
        "nuptial",
        "prenuptial",
        "premarital",
        "antenuptial",
        "certificate",
        "license",
        # Party terms
        "bride",
        "groom",
        "husband",
        "wife",
        "spouse",
        "betrothed",
        "fiancé",
        "fiancée",
        # Ceremony terms
        "ceremony",
        "solemnized",
        "officiant",
        "witness",
        "vows",
        "union",
        "matrimonial",
        # Prenuptial terms
        "separate",
        "property",
        "disclosure",
        "waiver",
        "rights",
        "obligations",
        "assets",
        "debts",
        # Legal terms (marriage context)
        "valid",
        "legal",
        "lawful",
        "binding",
        "enforceable",
    },
    filename_patterns={
        "marriage": 0.76,
        "marriage_certificate": 0.80,
        "marriage_license": 0.78,
        "prenuptial": 0.78,
        "prenup": 0.75,
        "premarital": 0.74,
    },
    # Exclusion patterns to prevent misclassification
    exclude_patterns={
        # Will patterns
        r"last\s*will\s*and\s*testament",
        r"testator",
        r"bequeath",
        # POA patterns
        r"power\s*of\s*attorney",
        r"attorney[\s-]in[\s-]fact",
        # Trust patterns
        r"trust\s*agreement",
        r"trustee",
        # Divorce patterns
        r"dissolution\s*of\s*marriage",
        r"divorce\s*decree",
        r"custody\s*arrangement",
        r"irreconcilable\s*differences",
    },
    exclude_phrases={
        "last will",
        "power of attorney",
        "trust agreement",
        "divorce decree",
        "separation agreement",
    },
)

# Export rules
ESTATE_FAMILY_SUBTHEME_RULES: List[SubthemeRule] = [
    WILL,
    POWER_OF_ATTORNEY,
    TRUST_DOCUMENT,
    DIVORCE_DOCUMENT,
    MARRIAGE_CERTIFICATE,
]

ESTATE_FAMILY_SUBTHEME_RULES_DICT: Dict[str, SubthemeRule] = {
    rule.name: rule for rule in ESTATE_FAMILY_SUBTHEME_RULES
}
