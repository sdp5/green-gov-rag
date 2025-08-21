import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from streamlit_folium import st_folium
from app.config import APP_TITLE, APP_DESCRIPTION, TOPIC_OPTIONS, DEFAULT_REGION_FILTER
from app.map import create_map

# Import RAG agent
from rag.agent_tools import RAGAgent

# Initialize RAG Agent (singleton for app session)
if "rag_agent" not in st.session_state:
    st.session_state.rag_agent = RAGAgent()

def render_ui():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.markdown(APP_DESCRIPTION)

    tabs = st.tabs(["Query", "Map", "Analytics", "Sources"])

    # ---------------------------
    # Query Tab
    # ---------------------------
    with tabs[0]:
        st.subheader("Ask a Policy Question")
        query_text = st.text_area("Type your question here", height=150)
        region_filter = st.selectbox("Select region", ["All", "Federal", "State", "Local"])
        topic_filter = st.multiselect("Select topics", TOPIC_OPTIONS, default=TOPIC_OPTIONS)

        if st.button("Get Answer"):
            if st.button("Get Answer"):
                if not query_text.strip():
                    st.warning("Please enter a question.")
                else:
                    st.info("Querying RAG engine...")
                    # Construct metadata_filters for RAGAgent
                    metadata_filters = {}
                    if region_filter != "All":
                        metadata_filters["region"] = region_filter
                    if topic_filter:
                        metadata_filters["topic"] = topic_filter

                    # Get answer
                    answer, sources = st.session_state.rag_agent.query(
                        query_text, metadata_filters=metadata_filters
                    )

                    # Display results
                    st.success("Answer:")
                    st.write(answer)

                    st.subheader("Sources / References")
                    for src in sources:
                        st.markdown(f"- [{src['title']}]({src['source_url']})")

    # ---------------------------
    # Map Tab
    # ---------------------------
    with tabs[1]:
        st.subheader("Interactive LGA Map")
        # Previously selected LGAs stored in session
        if "selected_lgas" not in st.session_state:
            st.session_state.selected_lgas = []

        # Render map
        lga_map = create_map(selected_lgas=st.session_state.selected_lgas)
        map_data = st_folium(lga_map, width=700, height=500)

        # Capture click event
        if map_data and map_data.get("last_active_drawing"):
            feature = map_data["last_active_drawing"]["properties"]
            clicked_lga = feature.get("LGA_NAME20")
            if clicked_lga and clicked_lga not in st.session_state.selected_lgas:
                st.session_state.selected_lgas.append(clicked_lga)

        st.write("Selected LGAs:", st.session_state.selected_lgas)

    # ---------------------------
    # Analytics Tab
    # ---------------------------
    with tabs[2]:
        st.subheader("Analytics Dashboard")

        # Load document metadata (example: from vector store or processed CSV)
        metadata_file = Path("data/processed/doc_metadata.csv")
        if metadata_file.exists():
            df = pd.read_csv(metadata_file)

            # Count documents per jurisdiction
            doc_count = df.groupby("jurisdiction").size().reset_index(name="count")
            fig1 = px.bar(doc_count, x="jurisdiction", y="count", title="Documents by Jurisdiction")
            st.plotly_chart(fig1, use_container_width=True)

            # Count documents per topic
            topic_count = df.groupby("topic").size().reset_index(name="count")
            fig2 = px.pie(topic_count, names="topic", values="count", title="Documents by Topic")
            st.plotly_chart(fig2, use_container_width=True)

            # Example: Count documents per region (if geo info available)
            region_count = df.groupby("region").size().reset_index(name="count")
            fig3 = px.bar(region_count, x="region", y="count", title="Documents by Region")
            st.plotly_chart(fig3, use_container_width=True)

        else:
            st.info("No metadata found. Run ETL to ingest documents first.")

        # Optional: Query analytics
        if "query_history" in st.session_state:
            history_df = pd.DataFrame(st.session_state.query_history)
            if not history_df.empty:
                st.markdown("### Recent Queries")
                st.dataframe(history_df)
                fig4 = px.bar(history_df.groupby("region").size().reset_index(name="queries"),
                              x="region", y="queries", title="Queries by Region")
                st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Query history not available yet.")

    # ---------------------------
    # Sources Tab
    # ---------------------------
    with tabs[3]:
        st.subheader("Policy Sources")
        # Sidebar filters
        st.sidebar.markdown("### Filter Sources")
        jurisdictions = st.sidebar.multiselect("Jurisdiction", options=df["jurisdiction"].unique(), default=df["jurisdiction"].unique())
        topics = st.sidebar.multiselect("Topic", options=df["topic"].unique(), default=df["topic"].unique())
        regions = st.sidebar.multiselect("Region", options=df["region"].unique(), default=df["region"].unique())

        # Apply filters
        filtered_df = df[
            (df["jurisdiction"].isin(jurisdictions)) &
            (df["topic"].isin(topics)) &
            (df["region"].isin(regions))
            ]

        if not filtered_df.empty:
            st.write(f"Displaying {len(filtered_df)} documents")
            for idx, row in filtered_df.iterrows():
                st.markdown(f"**Title:** {row['title']}")
                st.markdown(f"**Jurisdiction:** {row['jurisdiction']} | **Topic:** {row['topic']} | **Region:** {row['region']}")
                if "download_urls" in row and pd.notna(row["download_urls"]):
                    urls = eval(row["download_urls"])  # convert string representation of list
                    for i, url in enumerate(urls, 1):
                        st.markdown(f"[Download Part {i}]({url})")
                st.markdown("---")
        else:
            st.info("No documents match the selected filters.")
