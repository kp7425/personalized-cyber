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

# Sidebar
st.sidebar.title("🛡️ Security LMS")

# User Selector from Database
@st.cache_data(ttl=60)
def get_users_list():
    """Fetch users from database for selector."""
    try:
        from src.base.database import Database
        Database.init_pool()
        users = Database.fetch_all("""
            SELECT 
                u.user_id,
                u.workday_id,
                u.full_name,
                u.job_title,
                u.email,
                COALESCE(r.overall_risk_score, 0) as overall_risk,
                COALESCE(r.git_risk_score, 0) as git_risk,
                COALESCE(r.iam_risk_score, 0) as iam_risk
            FROM users u
            LEFT JOIN user_risk_profiles r ON u.user_id = r.user_id
            ORDER BY r.overall_risk_score DESC NULLS LAST
            LIMIT 20
        """)
        return users if users else []
    except Exception as e:
        st.sidebar.error(f"DB: {e}")
        return []

users_list = get_users_list()

if users_list:
    user_options = {f"{u['full_name']} ({u['job_title']}) - Risk: {float(u.get('overall_risk', 0) or 0):.2f}": u for u in users_list}
    selected_user_key = st.sidebar.selectbox("👤 Select User", list(user_options.keys()))
    selected_user = user_options[selected_user_key]
    
    st.session_state.user = {
        'id': selected_user['user_id'],
        'workday_id': selected_user['workday_id'],
        'email': selected_user.get('email', ''),
        'name': selected_user['full_name'],
        'job_title': selected_user['job_title'],
        'overall_risk': float(selected_user.get('overall_risk', 0) or 0),
        'git_risk': float(selected_user.get('git_risk', 0) or 0),
        'iam_risk': float(selected_user.get('iam_risk', 0) or 0)
    }
else:
    # Fallback if no DB
    st.session_state.user = {
        'id': 'demo-user',
        'name': 'Demo User',
        'job_title': 'Developer',
        'overall_risk': 0.5,
        'git_risk': 0.5,
        'iam_risk': 0.3
    }

user = st.session_state.user

st.sidebar.info(f"Logged in as: **{user['name']}**")
st.sidebar.markdown(f"Role: {user.get('job_title', 'Unknown')}")
page = st.sidebar.radio("Navigation", ["Dashboard", "My Training", "Team View"])

# --- DASHBOARD ---
if page == "Dashboard":
    st.title("My Security Risk Profile")
    
    # Use selected user's risk scores
    scores = {
        'overall_risk_score': user.get('overall_risk', 0.5),
        'git_risk_score': user.get('git_risk', 0.5),
        'iam_risk_score': user.get('iam_risk', 0.3),
        'security_incident_score': 0.1,  # Not in our current data
        'training_gap_score': max(0, user.get('overall_risk', 0.5) - 0.2)  # Derived
    }

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
        
        # Use selected user's risk from session state
        git_risk = user.get('git_risk', 0)
        iam_risk = user.get('iam_risk', 0)
        job_role = user.get('job_title', 'Developer')
        
        # Determine recommended modules based on risk
        if git_risk > 0.5:
            modules = ["Managing Secrets in Git", "Secure Coding Fundamentals"]
        elif iam_risk > 0.5:
            modules = ["Cloud IAM Best Practices", "Principle of Least Privilege"]
        else:
            modules = ["Security Awareness Basics", "Phishing Prevention"]
        
        for mod in modules:
            with st.expander(f"📚 {mod}", expanded=True):
                risk_context = f" (Your role: {job_role}, Git Risk: {git_risk:.2f}, IAM Risk: {iam_risk:.2f})"
                st.write(f"Based on your recent activity{risk_context}, we recommend this module.")
                
                if st.button(f"Start Module: {mod}", key=f"btn_{mod}"):
                    with st.spinner("🤖 Generating personalized content via mTLS → LLM Gateway → Gemini..."):
                        try:
                            import os
                            import requests
                            from src.base.spiffe_agent import SPIFFEMTLSHandler
                            
                            # Build personalized prompt
                            prompt = f"""Write a brief educational training module about "{mod}" for a {job_role}.

Target audience: {job_role} with git risk score of {git_risk:.2f}

Include:
- A short introduction (2-3 sentences)
- 3 best practices as bullet points
- 2 quiz questions with answers

Keep it professional and under 300 words."""

                            # Get or create mTLS handler
                            if 'mtls_handler' not in st.session_state:
                                try:
                                    st.session_state.mtls_handler = SPIFFEMTLSHandler()
                                except Exception as e:
                                    st.error(f"SPIFFE init failed: {e}")
                                    st.session_state.mtls_handler = None
                            
                            mtls = st.session_state.mtls_handler
                            
                            if mtls and mtls.cert_file:
                                # Call LLM Gateway via mTLS
                                gateway_url = "https://llm-gateway-svc.security-training.svc.cluster.local:8520/generate"
                                
                                response = mtls.make_mtls_request(gateway_url, {
                                    "messages": [
                                        {"role": "system", "content": "You are a security training expert."},
                                        {"role": "user", "content": prompt}
                                    ],
                                    "config": {"temperature": 0.7, "max_tokens": 600}
                                }, timeout=60)
                                
                                if response and response.status_code == 200:
                                    result = response.json()
                                    if "content" in result:
                                        st.markdown("---")
                                        st.markdown("### 📖 Your Personalized Training")
                                        st.markdown(result["content"])
                                        st.success(f"✅ Generated via mTLS → LLM Gateway → {result.get('backend', 'Gemini')} ({result.get('model', 'gemini-2.5-flash')})")
                                    elif "error" in result:
                                        st.error(f"LLM Gateway error: {result['error']}")
                                    else:
                                        st.warning(f"Unexpected response: {result}")
                                else:
                                    st.error(f"Gateway call failed: {response.status_code if response else 'No response'}")
                            else:
                                st.error("mTLS not initialized - SPIFFE certificates not available")
                                st.info("Ensure SPIRE agent is running and workload is registered.")
                        except Exception as e:
                            st.error(f"Error generating content: {e}")
                            st.info("Check mTLS configuration and LLM Gateway connectivity.")
    
    with col2:
        st.subheader("Progress")
        st.progress(0.7)
        st.write("70% Complete for Q4")


# --- TEAM VIEW ---
elif page == "Team View":
    st.title("Team Risk Overview")
    st.markdown("*Manager dashboard showing organization security posture*")
    
    # Fetch all users with risk profiles from database
    try:
        from src.base.database import Database
        Database.init_pool()
        
        # Organization Risk Banner
        org_stats = Database.fetch_one("""
            SELECT 
                COUNT(*) as total_users,
                AVG(overall_risk_score) as avg_risk,
                MAX(overall_risk_score) as max_risk,
                SUM(CASE WHEN overall_risk_score >= 0.6 THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN overall_risk_score >= 0.8 THEN 1 ELSE 0 END) as critical_count,
                AVG(git_risk_score) as avg_git,
                AVG(iam_risk_score) as avg_iam,
                AVG(training_gap_score) as avg_training
            FROM user_risk_profiles
            WHERE overall_risk_score IS NOT NULL
        """)
        
        if org_stats and org_stats['total_users'] > 0:
            # Calculate Org Risk: R_org = 0.4×mean + 0.3×max + 0.3×(high_risk_ratio)
            R_mean = float(org_stats['avg_risk'] or 0)
            R_max = float(org_stats['max_risk'] or 0)
            high_risk_ratio = int(org_stats['high_risk_count'] or 0) / int(org_stats['total_users'])
            R_org = 0.4 * R_mean + 0.3 * R_max + 0.3 * high_risk_ratio
            
            # Org risk level
            if R_org >= 0.7:
                level, color, emoji = "CRITICAL", "red", "🚨"
            elif R_org >= 0.5:
                level, color, emoji = "HIGH", "orange", "⚠️"
            elif R_org >= 0.3:
                level, color, emoji = "MEDIUM", "#ffc107", "📊"
            else:
                level, color, emoji = "LOW", "green", "✅"
            
            # Organization Risk Header
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, {color}22, transparent); 
                        border-left: 4px solid {color}; 
                        padding: 20px; 
                        margin-bottom: 20px; 
                        border-radius: 5px;">
                <h2 style="margin:0;">{emoji} Organization Security Risk: <span style="color:{color}">{R_org:.2f}</span> ({level})</h2>
                <p style="margin:5px 0 0 0; opacity:0.8;">
                    Formula: R_org = 0.4×Avg({R_mean:.2f}) + 0.3×Max({R_max:.2f}) + 0.3×HighRiskRatio({high_risk_ratio:.2%})
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        users_data = Database.fetch_all("""
            SELECT 
                u.workday_id,
                u.full_name,
                u.email,
                u.job_title,
                u.department,
                u.job_profile,
                COALESCE(r.overall_risk_score, 0) as overall_risk,
                COALESCE(r.git_risk_score, 0) as git_risk,
                COALESCE(r.iam_risk_score, 0) as iam_risk,
                COALESCE(r.training_gap_score, 0) as training_gap
            FROM users u
            LEFT JOIN user_risk_profiles r ON u.user_id = r.user_id
            ORDER BY r.overall_risk_score DESC NULLS LAST
            LIMIT 50
        """)
        
        if users_data:
            df = pd.DataFrame(users_data)
            
            # Top metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Users", len(df))
            with col2:
                high_risk = len(df[df['overall_risk'] >= 0.6])
                st.metric("High Risk", high_risk, delta=f"{high_risk/len(df)*100:.0f}%", delta_color="inverse")
            with col3:
                avg_risk = df['overall_risk'].mean()
                st.metric("Avg Risk Score", f"{avg_risk:.2f}")
            with col4:
                critical = len(df[df['overall_risk'] >= 0.8])
                st.metric("Critical", critical, delta_color="inverse" if critical > 0 else "off")
            
            st.markdown("---")
            
            # Charts row
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Risk Distribution")
                # Categorize users
                risk_categories = []
                for score in df['overall_risk']:
                    if score >= 0.8:
                        risk_categories.append('Critical')
                    elif score >= 0.6:
                        risk_categories.append('High')
                    elif score >= 0.3:
                        risk_categories.append('Medium')
                    else:
                        risk_categories.append('Low')
                
                risk_df = pd.DataFrame({'Risk Level': risk_categories})
                risk_counts = risk_df['Risk Level'].value_counts().reindex(['Critical', 'High', 'Medium', 'Low'], fill_value=0)
                
                fig = px.pie(
                    values=risk_counts.values, 
                    names=risk_counts.index,
                    color=risk_counts.index,
                    color_discrete_map={'Critical': '#dc3545', 'High': '#fd7e14', 'Medium': '#ffc107', 'Low': '#28a745'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("👥 Risk by Role")
                role_risk = df.groupby('job_title')['overall_risk'].mean().sort_values(ascending=False)
                fig = px.bar(
                    x=role_risk.index, 
                    y=role_risk.values,
                    labels={'x': 'Role', 'y': 'Avg Risk Score'},
                    color=role_risk.values,
                    color_continuous_scale='RdYlGn_r'
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # User table
            st.subheader("👤 All Team Members")
            
            # Add training frequency column
            def get_training_freq(score):
                if score >= 0.8: return "🔴 Immediate"
                elif score >= 0.6: return "🟠 Weekly"
                elif score >= 0.3: return "🟡 Monthly"
                return "🟢 Quarterly"
            
            df['Training Freq'] = df['overall_risk'].apply(get_training_freq)
            
            # Format for display
            display_df = df[['workday_id', 'full_name', 'job_title', 'department', 'overall_risk', 'git_risk', 'iam_risk', 'Training Freq']].copy()
            display_df.columns = ['ID', 'Name', 'Role', 'Dept', 'Overall', 'Git', 'IAM', 'Training']
            
            # Color code rows
            def highlight_risk(row):
                if row['Overall'] >= 0.8:
                    return ['background-color: #ffcccc'] * len(row)
                elif row['Overall'] >= 0.6:
                    return ['background-color: #ffe6cc'] * len(row)
                elif row['Overall'] >= 0.3:
                    return ['background-color: #ffffcc'] * len(row)
                return ['background-color: #ccffcc'] * len(row)
            
            styled_df = display_df.style.apply(highlight_risk, axis=1).format({
                'Overall': '{:.2f}',
                'Git': '{:.2f}',
                'IAM': '{:.2f}'
            })
            
            st.dataframe(styled_df, use_container_width=True, height=400)
            
            # High risk users callout
            high_risk_users = df[df['overall_risk'] >= 0.7][['full_name', 'job_title', 'overall_risk']]
            if not high_risk_users.empty:
                st.subheader("⚠️ High Risk Users Requiring Immediate Attention")
                for _, u in high_risk_users.iterrows():
                    st.error(f"**{u['full_name']}** ({u['job_title']}) - Risk Score: {u['overall_risk']:.2f}")
        else:
            st.warning("No users found. Run the simulation first: `./scripts/run-simulation.sh`")
            
    except Exception as e:
        st.error(f"Error loading team data: {e}")
        st.info("Make sure the database is connected and simulation has been run.")
