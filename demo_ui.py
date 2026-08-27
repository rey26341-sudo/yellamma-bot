import streamlit as st
import requests

st.set_page_config(page_title="Yellamma AI Booking Engine", page_icon="🤖", layout="wide")

st.title("🤖 Multi-Tenant AI Booking Engine")

tenants = {
    "NAX Medical Center": "medical_clinic",
    "NAX Dental Clinic": "dental_clinic",
    "NAX Physiotherapy": "physiotherapy",
    "Lustre Beauty Studio": "beauty_salon",
    "NAX Hair Salon": "hair_salon",
    "Serene Spa Retreat": "spa",
    "NAX Veterinary Clinic": "veterinary_clinic",
    "Demo Family Clinic": "clinic_demo"
}

selected_tenant_name = st.sidebar.selectbox("Select Business Niche:", list(tenants.keys()))
tenant_slug = tenants[selected_tenant_name]

if "current_slug" not in st.session_state or st.session_state.current_slug != tenant_slug:
    st.session_state.current_slug = tenant_slug
    st.session_state.messages = [
        {"role": "assistant", "content": f"Welcome to **{selected_tenant_name}**! How can I assist you today?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Type your message here..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    "http://127.0.0.1:8005/chat",
                    json={
                        "tenant_slug": tenant_slug,
                        "business_id": tenant_slug,
                        "message": user_input,
                        "session_id": "demo_user"
                    },
                    timeout=30
                )
                if res.status_code == 200:
                    data = res.json()
                    bot_reply = data.get("response") or data.get("reply") or "How can I help you further?"
                    st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                else:
                    st.error("Server error. Please try again.")
            except requests.exceptions.Timeout:
                st.warning("The service is under heavy load. Please resend your message.")
            except Exception as e:
                st.error(f"Connection failed: {e}")
