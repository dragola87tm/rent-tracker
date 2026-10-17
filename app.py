import streamlit as st
from supabase import create_client, Client

# Initialize Supabase Connection
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Skyrim Theme UI Customization via CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #1a1612;
        color: #d4c4a8;
        font-family: 'Georgia', serif;
    }
    h1, h2, h3 {
        color: #dfb76c !important;
        text-shadow: 2px 2px #000000;
    }
    .stButton>button {
        background-color: #4a3b2c;
        color: #dfb76c;
        border: 1px solid #dfb76c;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚔️ The Hold's Rental Ledger")

# Simple Authentication State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = "Steward"

if not st.session_state.logged_in:
    st.subheader("Identify Yourself to the Guard")
    username = st.text_input("Username (Email)")
    password = st.text_input("Password", type="password")
    
    if st.button("Enter Whiterun"):
        try:
            # Authenticate via Supabase
            res = supabase.auth.sign_in_with_password({"email": username, "password": password})
            st.session_state.logged_in = True
            
            # Fetch user role (Jarl vs Steward)
            user_id = res.user.id
            profile = supabase.table("user_profiles").select("role").eq("id", user_id).execute()
            st.session_state.user_role = profile.data[0]["role"] if profile.data else "Steward"
            st.rerun()
        except Exception as e:
            st.error("You committed crimes against Skyrim and her people! (Invalid Credentials)")
else:
    st.sidebar.markdown(f"**Current Rank:** {st.session_state.user_role}")
    if st.sidebar.button("Leave Hold (Logout)"):
        st.session_state.logged_in = False
        st.rerun()

    # --- MAIN LEDGER INTERFACE ---
    tabs = ["📋 View Ledger", "🪙 Update Rent", "👑 Jarl's Court (Admin)"]
    active_tab = st.tabs(tabs)

    # TAB 1: VIEW LEDGER
    with active_tab[0]:
        st.subheader("Current Asset Allocations")
        data = supabase.table("rentals").select("*").execute()
        if data.data:
            st.table(data.data)
        else:
            st.info("The ledger is empty. No houses or barrels are currently leased.")

    # TAB 2: UPDATE RENT (Accessible by Stewards and Jarls)
    with active_tab[1]:
        st.subheader("Amend Rental Agreements")
        # Form to add/update properties
        with st.form("rent_form"):
            prop_name = st.text_input("Property Name (e.g., Proudspire Manor / Riften Barrel #4)")
            prop_type = st.selectbox("Asset Type", ["House", "Barrel"])
            tenant = st.text_input("Tenant Name")
            gold = st.number_input("Rent (Gold Pieces)", min_value=0, step=50)
            paid = st.checkbox("Paid for this Month")
            
            if st.form_submit_button("Seal Agreement with Wax"):
                supabase.table("rentals").insert({
                    "property_name": prop_name,
                    "property_type": prop_type,
                    "current_tenant": tenant,
                    "rent_amount": gold,
                    "is_paid": paid
                }).execute()
                st.success("Ledger updated successfully!")
                st.rerun()

    # TAB 3: MASTER USER CONTROLS (Jarl Only)
    with active_tab[2]:
        st.subheader("The Jarl's Decree")
        if st.session_state.user_role != "Jarl":
            st.error("Stop right there! You do not have the Jarl's authority to access these chambers.")
        else:
            st.warning("Master Controls: Banish Users from the Hold")
            # Fetch all standard stewards
            stewards = supabase.table("user_profiles").select("id, username").eq("role", "Steward").execute()
            
            if stewards.data:
                steward_dict = {user["username"]: user["id"] for user in stewards.data}
                target_user = st.selectbox("Select Steward to Banish", list(steward_dict.keys()))
                
                if st.button("Behead / Banish User"):
                    # 1. Delete from profile table
                    supabase.table("user_profiles").delete().eq("id", steward_dict[target_user]).execute()
                    # 2. Delete from Supabase Auth Engine
                    supabase.auth.admin.delete_user(steward_dict[target_user])
                    st.success(f"{target_user} has been stripped of their titles and exiled.")
                    st.rerun()
            else:
                st.info("No subordinate stewards found in the Hold.")
