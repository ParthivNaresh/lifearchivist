import random
from datetime import datetime

from .file_schemas import FileCategory, ContentComplexity


class ContentGenerator:
    """Generate realistic content for different file types and scenarios."""

    # Template content for different categories
    MEDICAL_TEMPLATES = [
        """Patient Medical Record
        Date: {date}
        Patient ID: {patient_id}
        
        Chief Complaint: {complaint}
        
        Vital Signs:
        - Blood Pressure: {bp}
        - Heart Rate: {hr} bpm
        - Temperature: {temp}°F
        
        Assessment:
        {assessment}
        
        Treatment Plan:
        {treatment}
        
        Follow-up: {followup}
        """,
        """Clinical Trial Report
        Study: {study_name}
        Phase: {phase}
        Date: {date}
        
        Participants: {participants}
        Duration: {duration}
        
        Results:
        {results}
        
        Conclusions:
        {conclusions}
        """
    ]

    FINANCIAL_TEMPLATES = [
        """Financial Statement
        Company: {company}
        Period: {period}
        Date: {date}
        
        Revenue: ${revenue:,}
        Expenses: ${expenses:,}
        Net Income: ${net_income:,}
        
        Assets:
        - Current: ${current_assets:,}
        - Fixed: ${fixed_assets:,}
        
        Liabilities:
        - Current: ${current_liabilities:,}
        - Long-term: ${longterm_liabilities:,}
        
        Analysis:
        {analysis}
        """,
        """Investment Portfolio Report
        Account: {account_number}
        Date: {date}
        
        Holdings:
        {holdings}
        
        Performance:
        - YTD Return: {ytd_return}%
        - Total Value: ${total_value:,}
        
        Recommendations:
        {recommendations}
        """
    ]

    TECHNICAL_TEMPLATES = [
        """Technical Documentation
        System: {system_name}
        Version: {version}
        Date: {date}
        
        Architecture:
        {architecture}
        
        Components:
        {components}
        
        API Endpoints:
        {endpoints}
        
        Configuration:
        {configuration}
        
        Deployment:
        {deployment}
        """
    ]

    @classmethod
    def generate_content(
        cls,
        category: FileCategory,
        complexity: ContentComplexity,
        word_count: int = 200
    ) -> str:
        """Generate realistic content based on category and complexity."""

        if complexity == ContentComplexity.EMPTY:
            return ""

        if complexity == ContentComplexity.SIMPLE:
            return cls._generate_simple_content(category, word_count)

        if category == FileCategory.MEDICAL:
            template = random.choice(cls.MEDICAL_TEMPLATES)
            return cls._fill_medical_template(template, complexity)

        elif category == FileCategory.FINANCIAL:
            template = random.choice(cls.FINANCIAL_TEMPLATES)
            return cls._fill_financial_template(template, complexity)

        elif category == FileCategory.TECHNICAL:
            template = random.choice(cls.TECHNICAL_TEMPLATES)
            return cls._fill_technical_template(template, complexity)

        else:
            return cls._generate_generic_content(category, complexity, word_count)

    @classmethod
    def _generate_simple_content(cls, category: FileCategory, word_count: int) -> str:
        """Generate simple content for basic testing."""
        topics = {
            FileCategory.MEDICAL: "healthcare patient treatment diagnosis",
            FileCategory.FINANCIAL: "investment banking finance money",
            FileCategory.LEGAL: "contract law legal agreement",
            FileCategory.TECHNICAL: "software code programming development",
            FileCategory.PERSONAL: "diary journal personal thoughts",
            FileCategory.RESEARCH: "study research analysis findings",
            FileCategory.GENERAL: "document information content data"
        }

        words = topics.get(category, topics[FileCategory.GENERAL]).split()
        content = f"This is a {category.value} document. "

        while len(content.split()) < word_count:
            content += f"The {random.choice(words)} is important. "

        return content

    @classmethod
    def _fill_medical_template(cls, template: str, complexity: ContentComplexity) -> str:
        """Fill medical template with realistic data."""
        from datetime import datetime

        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "patient_id": f"P{random.randint(10000, 99999)}",
            "complaint": random.choice(["Chest pain", "Headache", "Fatigue", "Shortness of breath"]),
            "bp": f"{random.randint(110, 140)}/{random.randint(70, 90)}",
            "hr": random.randint(60, 100),
            "temp": round(random.uniform(97.0, 99.5), 1),
            "assessment": "Patient presents with symptoms consistent with the chief complaint. " * (2 if complexity == ContentComplexity.COMPLEX else 1),
            "treatment": "Prescribed medication and rest. Monitor symptoms." * (2 if complexity == ContentComplexity.COMPLEX else 1),
            "followup": f"In {random.randint(1, 4)} weeks",
            "study_name": f"STUDY-{random.randint(1000, 9999)}",
            "phase": random.choice(["I", "II", "III", "IV"]),
            "participants": random.randint(50, 500),
            "duration": f"{random.randint(3, 24)} months",
            "results": "Positive outcomes observed in treatment group.",
            "conclusions": "Further research recommended."
        }

        return template.format(**data)

    @classmethod
    def _fill_financial_template(cls, template: str, complexity: ContentComplexity) -> str:
        """Fill financial template with realistic data."""
        data = {
            "company": random.choice(["Acme Corp", "Global Industries", "Tech Solutions Inc"]),
            "period": f"Q{random.randint(1, 4)} 2024",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "revenue": random.randint(1000000, 10000000),
            "expenses": random.randint(500000, 5000000),
            "net_income": random.randint(100000, 2000000),
            "current_assets": random.randint(500000, 3000000),
            "fixed_assets": random.randint(1000000, 5000000),
            "current_liabilities": random.randint(200000, 1000000),
            "longterm_liabilities": random.randint(500000, 2000000),
            "analysis": "Financial performance meets expectations." * (2 if complexity == ContentComplexity.COMPLEX else 1),
            "account_number": f"ACC{random.randint(100000, 999999)}",
            "holdings": "AAPL: 100 shares\nGOOGL: 50 shares\nMSFT: 75 shares",
            "ytd_return": round(random.uniform(-10, 30), 2),
            "total_value": random.randint(50000, 500000),
            "recommendations": "Diversify portfolio. Consider bonds."
        }

        return template.format(**data)

    @classmethod
    def _fill_technical_template(cls, template: str, complexity: ContentComplexity) -> str:
        """Fill technical template with realistic data."""
        data = {
            "system_name": random.choice(["DataProcessor", "CloudManager", "APIGateway"]),
            "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "architecture": "Microservices architecture with Docker containers",
            "components": "- API Server\n- Database\n- Cache Layer\n- Message Queue",
            "endpoints": "GET /api/data\nPOST /api/process\nDELETE /api/clear",
            "configuration": "Environment variables and config files",
            "deployment": "Kubernetes cluster with auto-scaling"
        }

        return template.format(**data)

    @classmethod
    def _generate_generic_content(
        cls,
        category: FileCategory,
        complexity: ContentComplexity,
        word_count: int
    ) -> str:
        """Generate generic content for any category."""
        paragraphs = []

        # Introduction
        paragraphs.append(
            f"This is a {category.value} document created for testing purposes. "
            f"It contains {complexity.value} content with multiple sections and topics."
        )

        # Add sections based on complexity
        if complexity in [ContentComplexity.MODERATE, ContentComplexity.COMPLEX]:
            paragraphs.append(
                f"\nSection 1: Overview\n"
                f"This section provides an overview of the {category.value} domain. "
                f"The content here is designed to test search and extraction capabilities."
            )

            paragraphs.append(
                f"\nSection 2: Details\n"
                f"Detailed information about specific aspects of {category.value}. "
                f"This includes dates like {datetime.now().strftime('%B %d, %Y')} and "
                f"references to entities and concepts."
            )

        if complexity == ContentComplexity.COMPLEX:
            paragraphs.append(
                f"\nSection 3: Analysis\n"
                f"In-depth analysis of trends and patterns in {category.value}. "
                f"Multiple data points and cross-references to other documents."
            )

            paragraphs.append(
                f"\nSection 4: Conclusions\n"
                f"Summary of findings and recommendations for future actions."
            )

        content = "\n".join(paragraphs)

        # Pad to reach word count
        while len(content.split()) < word_count:
            content += f"\nAdditional content for {category.value} testing. "

        return content
