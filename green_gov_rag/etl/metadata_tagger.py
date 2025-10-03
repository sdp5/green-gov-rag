"""Automated Metadata Tagging using LangChain.

This module provides LLM-powered metadata extraction for ESG/NGER documents,
automating the tagging process to ensure consistent categorization.
"""

from __future__ import annotations

from typing import Any

from langchain.chains import create_tagging_chain_pydantic
from langchain.docstore.document import Document
from langchain.document_transformers import OpenAIMetadataTagger
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class ESGMetadata(BaseModel):
    """ESG metadata schema for automated tagging."""

    emission_scopes: list[str] = Field(
        description=(
            "Emission scopes covered in this document. Options: "
            "scope_1 (direct emissions from owned sources), "
            "scope_2 (indirect emissions from purchased energy), "
            "scope_3 (indirect emissions in value chain)"
        ),
        default_factory=list,
    )

    scope_3_categories: list[str] = Field(
        description=(
            "Scope 3 categories if applicable. Options: "
            "purchased_goods_services, capital_goods, fuel_energy_activities, "
            "upstream_transport, waste_generated, business_travel, "
            "employee_commuting, upstream_leased_assets, downstream_transport, "
            "processing_sold_products, use_of_sold_products, end_of_life_treatment, "
            "downstream_leased_assets, franchises, investments"
        ),
        default_factory=list,
    )

    greenhouse_gases: list[str] = Field(
        description=(
            "Greenhouse gases mentioned. Options: "
            "CO2, CH4, N2O, SF6, HFCs, PFCs, NF3"
        ),
        default_factory=list,
    )

    frameworks: list[str] = Field(
        description=(
            "ESG frameworks or standards referenced. Options: "
            "NGER, ISSB, GHG_Protocol, GRI, TCFD, CDP, Safeguard_Mechanism"
        ),
        default_factory=list,
    )

    consolidation_method: str | None = Field(
        description=(
            "Consolidation approach for emissions accounting. Options: "
            "operational_control, equity_share, financial_control, or null if not specified"
        ),
        default=None,
    )

    methodology_type: str | None = Field(
        description=(
            "Type of methodology described. Options: "
            "calculation, reporting, verification, or null if not specified"
        ),
        default=None,
    )

    activity_types: list[str] = Field(
        description=(
            "Activity types covered. Examples: "
            "fuel_combustion, electricity_consumption, fugitive_emissions, "
            "refrigerant_use, transport, waste, supply_chain, etc."
        ),
        default_factory=list,
    )

    facility_types: list[str] = Field(
        description=(
            "Facility or organization types this applies to. Examples: "
            "coal_mine, power_station, manufacturing, all, large_emitters, etc."
        ),
        default_factory=list,
    )

    industry_applicability: list[str] = Field(
        description=(
            "Industries this document applies to (ANZSIC codes or names). "
            "Examples: B0600 (Coal Mining), C1700 (Manufacturing), D2610 (Electricity), etc."
        ),
        default_factory=list,
    )

    regulatory_authority: str | None = Field(
        description=(
            "Regulatory authority or organization that issued/enforces this. "
            "Examples: Clean Energy Regulator, NSW EPA, Victorian EPA, IFRS Foundation, etc."
        ),
        default=None,
    )

    reportable_under_nger: bool | None = Field(
        description="Whether this is reportable under NGER (true/false or null if not specified)",
        default=None,
    )


class DocumentMetadata(BaseModel):
    """General document metadata schema."""

    jurisdiction: str | None = Field(
        description="Jurisdiction level: federal, state, or local",
        default=None,
    )

    category: str | None = Field(
        description=(
            "Document category: environment, planning, legislation, regulation, "
            "guidelines, policy, building, etc."
        ),
        default=None,
    )

    topic: str | None = Field(
        description=(
            "Specific topic: emissions_reporting, biodiversity, tree_management, "
            "climate_change, vegetation_management, etc."
        ),
        default=None,
    )

    region: str | None = Field(
        description="Geographic region: Australia, New South Wales, Victoria, South Australia, etc.",
        default=None,
    )


class MetadataTagger:
    """LLM-powered metadata tagger for automatic document categorization."""

    def __init__(self, model_name: str = "gpt-4", temperature: float = 0.0):
        """Initialize metadata tagger.

        Args:
        ----
            model_name: OpenAI model to use for tagging
            temperature: Model temperature (0 for deterministic)

        """
        from langchain.chat_models import ChatOpenAI

        self.llm: Any = ChatOpenAI(model=model_name, temperature=temperature)  # type: ignore[misc]

        # Create tagging chains
        self.esg_tagger = create_tagging_chain_pydantic(ESGMetadata, self.llm)
        self.doc_tagger = create_tagging_chain_pydantic(DocumentMetadata, self.llm)

    def tag_esg_metadata(self, text: str) -> dict[str, Any]:
        """Extract ESG metadata from document text.

        Args:
        ----
            text: Document text to analyze

        Returns:
        -------
            Dict of ESG metadata

        """
        result = self.esg_tagger.run(text)
        return result.dict(exclude_none=True)

    def tag_document_metadata(self, text: str) -> dict[str, Any]:
        """Extract general document metadata from text.

        Args:
        ----
            text: Document text to analyze

        Returns:
        -------
            Dict of document metadata

        """
        result = self.doc_tagger.run(text)
        return result.dict(exclude_none=True)

    def tag_document(self, document: Document, include_esg: bool = True) -> Document:
        """Tag a LangChain Document with metadata.

        Args:
        ----
            document: LangChain Document to tag
            include_esg: Whether to extract ESG metadata

        Returns:
        -------
            Document with enriched metadata

        """
        text = document.page_content

        # Extract general metadata
        doc_metadata = self.tag_document_metadata(text)

        # Merge with existing metadata
        for key, value in doc_metadata.items():
            if value is not None:
                document.metadata[key] = value

        # Extract ESG metadata if requested
        if include_esg:
            esg_metadata = self.tag_esg_metadata(text)
            if esg_metadata:
                document.metadata["esg_metadata"] = esg_metadata

        return document

    def tag_documents(
        self,
        documents: list[Document],
        include_esg: bool = True,
    ) -> list[Document]:
        """Tag multiple documents with metadata.

        Args:
        ----
            documents: List of LangChain Documents
            include_esg: Whether to extract ESG metadata

        Returns:
        -------
            List of Documents with enriched metadata

        """
        return [self.tag_document(doc, include_esg) for doc in documents]


class CustomPromptTagger:
    """Metadata tagger with custom prompts for specific use cases."""

    def __init__(self, model_name: str = "gpt-4", temperature: float = 0.0):
        """Initialize custom prompt tagger.

        Args:
        ----
            model_name: OpenAI model to use
            temperature: Model temperature

        """
        from langchain.chat_models import ChatOpenAI

        self.llm: Any = ChatOpenAI(model=model_name, temperature=temperature)  # type: ignore[misc]

    def extract_scope_3_categories(self, text: str) -> list[str]:
        """Extract Scope 3 categories from text using custom prompt.

        Args:
        ----
            text: Document text

        Returns:
        -------
            List of Scope 3 category names

        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an ESG expert analyzing emissions reporting documents. "
                    "Extract Scope 3 emission categories mentioned in the text.",
                ),
                (
                    "human",
                    "Analyze this text and list all Scope 3 categories mentioned. "
                    "Use these exact category names:\n"
                    "- purchased_goods_services (Category 1)\n"
                    "- capital_goods (Category 2)\n"
                    "- fuel_energy_activities (Category 3)\n"
                    "- upstream_transport (Category 4)\n"
                    "- waste_generated (Category 5)\n"
                    "- business_travel (Category 6)\n"
                    "- employee_commuting (Category 7)\n"
                    "- upstream_leased_assets (Category 8)\n"
                    "- downstream_transport (Category 9)\n"
                    "- processing_sold_products (Category 10)\n"
                    "- use_of_sold_products (Category 11)\n"
                    "- end_of_life_treatment (Category 12)\n"
                    "- downstream_leased_assets (Category 13)\n"
                    "- franchises (Category 14)\n"
                    "- investments (Category 15)\n\n"
                    "Text: {text}\n\n"
                    "Return only the category names as a comma-separated list.",
                ),
            ],
        )

        chain: Any = prompt | self.llm
        response = chain.invoke({"text": text})

        # Parse response
        return [cat.strip() for cat in response.content.split(",") if cat.strip()]

    def identify_regulatory_framework(self, text: str) -> dict[str, Any]:
        """Identify regulatory framework and compliance requirements.

        Args:
        ----
            text: Document text

        Returns:
        -------
            Dict with framework, regulator, and compliance info

        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a regulatory compliance expert analyzing environmental documents.",
                ),
                (
                    "human",
                    "Analyze this text and identify:\n"
                    "1. Regulatory framework (NGER, ISSB, GHG Protocol, GRI, etc.)\n"
                    "2. Regulatory authority (Clean Energy Regulator, EPA, etc.)\n"
                    "3. Whether it's reportable under NGER (yes/no)\n"
                    "4. Emission scopes covered (scope_1, scope_2, scope_3)\n\n"
                    "Text: {text}\n\n"
                    "Format your response as JSON with keys: frameworks, regulator, "
                    "reportable_under_nger, emission_scopes",
                ),
            ],
        )

        chain: Any = prompt | self.llm
        _response = chain.invoke({"text": text})

        # In production, parse JSON response properly
        # For now, return structured dict
        return {
            "frameworks": [],
            "regulator": None,
            "reportable_under_nger": None,
            "emission_scopes": [],
        }


class ESGOpenAITagger:
    """Wrapper for OpenAIMetadataTagger with ESG-specific schemas."""

    def __init__(self):
        """Initialize ESG metadata tagger with predefined schemas."""
        # ESG Metadata Schema
        self.esg_schema = {
            "properties": {
                "emission_scope": {
                    "type": "string",
                    "enum": ["scope_1", "scope_2", "scope_3"],
                    "description": "Which emission scope this section covers",
                },
                "scope_3_categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "purchased_goods_services",
                            "capital_goods",
                            "fuel_energy_activities",
                            "upstream_transport",
                            "waste_generated",
                            "business_travel",
                            "employee_commuting",
                            "upstream_leased_assets",
                            "downstream_transport",
                            "processing_sold_products",
                            "use_of_sold_products",
                            "end_of_life_treatment",
                            "downstream_leased_assets",
                            "franchises",
                            "investments",
                        ],
                    },
                    "description": "Scope 3 categories covered (only if emission_scope is scope_3)",
                },
                "greenhouse_gases": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["CO2", "CH4", "N2O", "SF6", "HFCs", "PFCs", "NF3"],
                    },
                    "description": "Greenhouse gases mentioned in this section",
                },
                "calculation_method": {
                    "type": "string",
                    "description": "Calculation methodology described (if any)",
                },
                "consolidation_approach": {
                    "type": "string",
                    "enum": [
                        "operational_control",
                        "equity_share",
                        "financial_control",
                    ],
                    "description": "Consolidation approach for emissions accounting",
                },
                "industry_applicability": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ANZSIC industry codes this applies to",
                },
                "regulatory_authority": {
                    "type": "string",
                    "description": "Which regulator enforces this",
                },
                "frameworks": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "NGER",
                            "ISSB",
                            "GHG_Protocol",
                            "GRI",
                            "TCFD",
                            "Safeguard_Mechanism",
                        ],
                    },
                    "description": "ESG frameworks or standards referenced",
                },
            },
            "required": ["emission_scope"],
        }

        # Document Metadata Schema
        self.doc_schema = {
            "properties": {
                "jurisdiction": {
                    "type": "string",
                    "enum": ["federal", "state", "local"],
                    "description": "Jurisdiction level of the document",
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "environment",
                        "planning",
                        "legislation",
                        "regulation",
                        "guidelines",
                        "policy",
                    ],
                    "description": "Document category",
                },
                "topic": {
                    "type": "string",
                    "description": "Specific topic covered (e.g., emissions_reporting, biodiversity)",
                },
                "region": {
                    "type": "string",
                    "description": "Geographic region (state or territory name)",
                },
            },
        }

        # Initialize OpenAI taggers
        self.esg_tagger = OpenAIMetadataTagger(self.esg_schema)  # type: ignore[misc]
        self.doc_tagger = OpenAIMetadataTagger(self.doc_schema)  # type: ignore[misc]

    def tag_esg_metadata(self, documents: list[Document]) -> list[Document]:
        """Tag documents with ESG metadata.

        Args:
        ----
            documents: List of LangChain Documents

        Returns:
        -------
            Documents with ESG metadata added

        """
        return list(self.esg_tagger.transform_documents(documents))

    def tag_document_metadata(self, documents: list[Document]) -> list[Document]:
        """Tag documents with general metadata.

        Args:
        ----
            documents: List of LangChain Documents

        Returns:
        -------
            Documents with general metadata added

        """
        return list(self.doc_tagger.transform_documents(documents))

    def tag_all(self, documents: list[Document]) -> list[Document]:
        """Tag documents with both ESG and general metadata.

        Args:
        ----
            documents: List of LangChain Documents

        Returns:
        -------
            Fully tagged documents

        """
        # First tag with general metadata
        docs = self.tag_document_metadata(documents)

        # Then tag with ESG metadata
        return self.tag_esg_metadata(docs)


# Example usage
if __name__ == "__main__":
    # Sample document text
    sample_text = """
    This guideline provides methods for calculating Scope 1 emissions from coal mining
    operations, including fugitive emissions of methane (CH4) and carbon dioxide (CO2).
    Facilities must report under NGER if emissions exceed 25,000 tonnes CO2-e annually.
    The Clean Energy Regulator enforces these requirements using operational control
    consolidation approach.
    """

    # Initialize tagger
    tagger = MetadataTagger(model_name="gpt-3.5-turbo")

    # Extract ESG metadata
    esg_metadata = tagger.tag_esg_metadata(sample_text)
    print("ESG Metadata:", esg_metadata)

    # Create document and tag it
    doc = Document(page_content=sample_text, metadata={"title": "Sample Doc"})
    tagged_doc = tagger.tag_document(doc)
    print("\nTagged Document Metadata:", tagged_doc.metadata)

    print("\n" + "=" * 60)
    print("Using ESGOpenAITagger:")
    print("=" * 60)

    # Use OpenAI tagger
    openai_tagger = ESGOpenAITagger()

    # Tag multiple documents
    documents = [
        Document(
            page_content=sample_text,
            metadata={"title": "NGER Coal Mining Guideline"},
        ),
        Document(
            page_content="""
            ISSB requires disclosure of Scope 3 emissions across all 15 categories,
            including upstream transport and downstream product use. Companies must
            report using equity share or operational control consolidation.
            """,
            metadata={"title": "ISSB Scope 3 Requirements"},
        ),
    ]

    tagged_docs = openai_tagger.tag_all(documents)

    for i, doc in enumerate(tagged_docs, 1):
        print(f"\nDocument {i}: {doc.metadata.get('title')}")
        print(f"Metadata: {doc.metadata}")
