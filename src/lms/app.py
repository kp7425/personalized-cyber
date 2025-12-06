import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from src.lms.utils.api_client import APIClient

st.set_page_config(
    page_title="Security Awareness LMS",
    page_icon="🛡️",
    layout="wide"
)

# Mock Auth for Demo
if 'user' not in st.session_state:
    st.session_state.user = {
        'id': 'demo-user-123',
        'email': 'alice@example.org',
        'name': 'Alice Engineer',
        'role': 'Developer'
    }

user = st.session_state.user

# Sidebar
st.sidebar.title("🛡️ Security LMS")
st.sidebar.info(f"Logged in as: **{user['name']}**")
page = st.sidebar.radio("Navigation", ["Dashboard", "My Training", "Team View"])

# --- DASHBOARD ---
if page == "Dashboard":
    st.title("My Security Risk Profile")
    
    # Fetch risk score
    try:
        # In real app, we'd call the risk scorer API
        # response = APIClient.post("risk-scorer", "/score", {"user_id": user['id']})
        # scores = response.json().get('scores', {})
        
        # Taking mock data for visual demo since services aren't running yet
        scores = {
            'overall_risk_score': 0.65,
            'git_risk_score': 0.8,
            'iam_risk_score': 0.2,
            'security_incident_score': 0.1,
            'training_gap_score': 0.4
        }
    except Exception as e:
         st.error(f"Failed to fetch risk profile: {e}")
         scores = {}

    # Top Level Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Risk", f"{scores.get('overall_risk_score', 0):.2f}", delta="-0.05", delta_color="inverse")
    with col2:
        st.metric("Git Risk", f"{scores.get('git_risk_score', 0):.2f}", delta="+0.1", delta_color="inverse")
    with col3:
        st.metric("IAM Risk", f"{scores.get('iam_risk_score', 0):.2f}", delta="0.0")
    with col4:
        st.metric("Training Gap", f"{scores.get('training_gap_score', 0):.2f}", delta="-0.1", delta_color="normal")

    st.markdown("### 📊 Risk Breakdown & Recent Incidents")
    col1, col2 = st.columns(2)
    
    with col1:
         st.info(f"**Git Anomalies**: {scores.get('git_risk_score', 0.0):.2f}")
         # Mock breakdown for demo visualization
         risks = []
         if scores.get('git_risk_score', 0) > 0.3: risks.append("Secrets Detected (env)")
         if scores.get('iam_risk_score', 0) > 0.4: risks.append("Privileged Cloud Access")
         if scores.get('security_incident_score', 0) > 0.2: risks.append("Vulnerable Dependency")
         
         if not risks:
             st.success("No critical anomalies detected.")
         else:
             for r in risks:
                 st.warning(f"⚠️ {r}")

    with col2:
         st.info(f"**Training Gap**: {scores.get('training_gap_score', 0.0):.2f}")
         st.metric("Modules Overdue", scores.get('training_modules_overdue', 0))

    # Chart
    risk_data = pd.DataFrame({
        'Category': ['Git', 'IAM', 'Incidents', 'Training'],
        'Score': [
            scores.get('git_risk_score', 0),
            scores.get('iam_risk_score', 0),
            scores.get('security_incident_score', 0),
            scores.get('training_gap_score', 0)
        ]
    })
    
    fig = px.bar(risk_data, x='Category', y='Score', color='Score', 
                 range_y=[0, 1], color_continuous_scale='RdYlGn_r', title="Risk Breakdown")
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent Activity
    st.subheader("Recent Risk Events")
    st.table(pd.DataFrame([
        {"Date": "2023-12-01", "Event": "Secret committed to repo-frontend", "Severity": "High"},
        {"Date": "2023-11-28", "Event": "Force push to main", "Severity": "Medium"},
        {"Date": "2023-11-15", "Event": "Training 'Phishing 101' overdue", "Severity": "Low"},
    ]))


# --- TRAINING ---
elif page == "My Training":
    st.title("Personalized Training")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Recommended Modules")
        # Fetch recommendations
        try:
            # response = APIClient.post("training-recommender", "/recommend", {"user_id": user['id']})
            # modules = response.json().get('recommended_modules', [])
             modules = ["Managing Secrets in Git", "Secure Coding Fundamentals"]
        except:
            modules = []
            
        for mod in modules:
            with st.expander(f"📚 {mod}", expanded=True):
                st.write("Based on your recent git activity, we recommend this short module.")
                if st.button(f"Start Module: {mod}"):
                    st.session_state.current_module = mod
                    # Call LLM to generate content
                    # response = APIClient.post("llm-gateway", "/generate", {
                    #    "messages": [{"role": "user", "content": f"Teach me about {mod}"}]
                    # })
                    st.info("Generating personalized content with AI... (Mock: Content would appear here)")
    
    with col2:
        st.subheader("Progress")
        st.progress(0.7)
        st.write("70% Complete for Q4")


# --- TEAM VIEW ---
elif page == "Team View":
    st.title("Team Risk Overview")
    st.write("Manager view logic here...")

