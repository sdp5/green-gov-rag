# GreenGovRAG

An AI Assistant for Navigating Australian Environmental & Planning Regulations

## Project Objective

To build a generative AI-powered assistant that helps users understand and comply with complex environmental and planning regulations in Australia by combining retrieval-augmented generation (RAG) with geospatial filtering and document metadata search.

## Problem Statement

Australia’s **environmental and land use regulations** span multiple jurisdictions:

- **Federal** (e.g., EPBC Act),
- **State-level** planning laws (e.g., SA’s Planning and Design Code),
- **Local government** development controls, zoning rules, and sustainability frameworks.

These regulations are:

- Buried across **hundreds of PDF documents and HTML pages**,
- Written in **dense legal language**,
- Specific to **locations (LGAs, postcodes)** and topics like biodiversity, emissions, vegetation clearance, etc.

### As a result:

- **Developers**, **urban planners**, **council officers**, and **environmental consultants** struggle to find timely, accurate, and localised answers to key questions.

## Solution: GreenGovRAG

GreenGovRAG is an **AI assistant powered by Retrieval-Augmented Generation (RAG)** that answers user questions by retrieving relevant sections from a curated knowledge base of regulations.

It adds value by:

- Structuring and tagging regulations with **LGA/state/topic** metadata.
- Allowing **map-based filtering** (e.g., “Show rules in Adelaide”).
- Supporting **geospatial queries** (e.g., by clicking on an LGA).
- Delivering **grounded answers with source citations**.
- Wrapping the system in a clean UI with optional agent-based orchestration.

## Target Users

- 🏢 **Urban Planners / Consultants** – to quickly assess development requirements.
- 🏙️ **Local Council Sustainability Teams** – to validate project compliance.
- 🌱 **Land Developers** – to find out what’s permitted in a given area.
- 🧑‍💼 **Environmental Officers** – to locate EIA/offset guidelines by region.
- 📈 **Policymakers / Researchers** – to monitor regulatory coverage and update gaps.

### Sample Questions It Can Answer

- _“What are the native vegetation clearance rules in SA?”_
- _"What are the environmental offsets required in SA for land clearing?"_
- _“Do I need an environmental impact statement for a wind farm in regional NSW?”_
- _“Which zoning restrictions apply to industrial zones in the City of Adelaide?”_
- _“What are the renewable energy incentives for residential buildings in Victoria?”_

---
### Key Factors Supporting Relevance

> 2025 July

#### Ongoing Environmental Regulatory Reforms

The Australian government is actively overhauling its environmental laws, including the Environment Protection and Biodiversity Conservation (EPBC) Act. Efforts are underway to establish Environment Protection Australia, a new independent federal agency with expanded compliance and enforcement powers.

#### Complexity in Planning and Approval Processes

Developers and planners face challenges due to intricate and evolving regulations, leading to delays in project approvals, particularly in renewable energy sectors.

#### Adoption of AI in Government Services

Services Australia has outlined its Automation and AI Strategy 2025–27, emphasizing the use of AI to enhance service delivery and support for individuals with complex needs.

#### Demand for Accessible Regulatory Information

With the introduction of new regulations and agencies, there is a growing need for tools that can provide clear, location-specific information on environmental and planning policies to various stakeholders, including urban planners, developers, and environmental consultants.
