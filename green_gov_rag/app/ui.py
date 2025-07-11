# Streamlit logic (text UI + map + results)

import streamlit as st

from green_gov_rag.app.map import folium_static, render_map


def main():
    st.title("GreenGovRAG - Environmental Policy Assistant")

    # Select LGA from dropdown
    lgas = ["Adelaide", "Port Adelaide Enfield", "Unley"]  # ideally load dynamically
    selected_lga = st.selectbox("Select Local Government Area (LGA):", lgas)

    folium_map = render_map(selected_lga)
    folium_static(folium_map)

    query = st.text_input("Ask about environmental regulations:")

    if query and st.button("Ask"):
        # Placeholder for RAG answer
        st.info(f"Querying RAG system for: {query} in {selected_lga}")


if __name__ == "__main__":
    main()
