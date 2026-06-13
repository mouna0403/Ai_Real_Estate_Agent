
import streamlit as st
from Ai_Real_Estate_Agent.utils.agent import ask

st.set_page_config(
    page_title="AI Real Estate Agent - Île-de-France",
    page_icon="🏠",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Text color for all text */
    .stMarkdown, .stText, .stTitle, div, p, span, label {
        color: #1a1a2e !important;
    }
    
    /* Chat message bubbles */
    .chat-message {
        padding: 1rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        display: flex;
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* User message */
    .user-message {
        background-color: #e3f2fd;
        color: #1a1a2e !important;
        justify-content: flex-end;
        border-radius: 18px 18px 4px 18px;
    }
    
    .user-message div, .user-message strong, .user-message p {
        color: #1a1a2e !important;
    }
    
    /* Agent message */
    .agent-message {
        background-color: #f5f5f5;
        color: #1a1a2e !important;
        justify-content: flex-start;
        border-radius: 18px 18px 18px 4px;
        border-left: 3px solid #2c7da0;
    }
    
    .agent-message div, .agent-message strong, .agent-message p {
        color: #1a1a2e !important;
    }
    
    /* Input field */
    .stTextInput > div > div > input {
        border-radius: 25px;
        border: 1px solid #ccc;
        background-color: #ffffff;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        color: #1a1a2e !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #999;
    }
    
    /* Button */
    .stButton > button {
        background-color: #2c7da0;
        color: white !important;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: 500;
        border: none;
    }
    
    .stButton > button:hover {
        background-color: #1f5e7a;
        color: white !important;
    }
    
    /* Title */
    .title {
        text-align: center;
        color: #1a1a2e !important;
        margin-bottom: 2rem;
    }
    
    .title h1, .title p {
        color: #1a1a2e !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #fafafa;
    }
    
    [data-testid="stSidebar"] * {
        color: #1a1a2e !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #2c7da0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Title
st.markdown('<div class="title"><h1>🏠 AI Real Estate Agent</h1><p>Île-de-France Property Expert</p></div>', unsafe_allow_html=True)

# Chat container
chat_container = st.container()

# Display chat history
with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message" style="margin-left: auto; max-width: 80%;">
                <div>
                    <strong>Vous</strong><br>
                    {msg["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message agent-message" style="margin-right: auto; max-width: 80%;">
                <div>
                    <strong>🏠 Agent</strong><br>
                    {msg["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

# Input at bottom
with st.container():
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "Votre question",
            placeholder="Ex: Estimez un appartement de 50m² à Paris...",
            key="input",
            label_visibility="collapsed"
        )
    with col2:
        send_button = st.button("Envoyer →", use_container_width=True)

# Handle input
if send_button and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.spinner("L'agent analyse votre demande..."):
        response = ask(user_input)
        if response is None:
            response = "Désolé, je n'ai pas pu traiter votre demande. Pouvez-vous reformuler votre question ?"
    
    st.session_state.messages.append({"role": "agent", "content": response})
    st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("### 🎮 Contrôles")
    if st.button("🗑️ Effacer la conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 💡 Suggestions")
    suggestions = [
        "Estimez un appartement de 50m² à Paris",
        "Prix d'une maison de 90m² à Versailles",
        "Transports à Neuilly-sur-Seine",
        "Espaces verts à Créteil"
    ]
    for sugg in suggestions:
        if st.button(f"📌 {sugg}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": sugg})
            with st.spinner("L'agent analyse votre demande..."):
                response = ask(sugg)
                if response is None:
                    response = "Désolé, je n'ai pas pu traiter votre demande."
            st.session_state.messages.append({"role": "agent", "content": response})
            st.rerun()
    
    st.markdown("---")
    st.markdown("### ℹ️ À propos")
    st.markdown("Agent spécialisé en estimation immobilière et analyse territoriale en Île-de-France.")