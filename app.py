import streamlit as st
from supabase import create_client, Client
import datetime

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
    h1, h2, h3, h4 {
        color: #dfb76c !important;
        text-shadow: 2px 2px #000000;
    }
    .stButton>button {
        background-color: #4a3b2c;
        color: #dfb76c;
        border: 1px solid #dfb76c;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #614e3a;
        color: #fff;
        border: 1px solid #fff;
    }
    div[data-testid="stExpander"] {
        background-color: #26201a;
        border: 1px solid #4a3b2c;
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
    username = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    
    if st.button("Enter Whiterun"):
        try:
            res = supabase.auth.sign_in_with_password({"email": username, "password": password})
            st.session_state.logged_in = True
            
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
    tabs = ["📋 View Ledger", "🪙 Register Asset", "⚙️ Manage & Edit Assets", "👑 Jarl's Court"]
    active_tabs = st.tabs(tabs)

    # TAB 1: VIEW LEDGER (WITH 7-DAY DYNAMIC COLOR COUNTDOWNS)
    with active_tabs[0]:
        st.subheader("Current Asset Allocations & Expirations")
        data = supabase.table("rentals").select("*").order("id").execute()
        
        if data.data:
            now = datetime.datetime.now(datetime.timezone.utc)
            
            for item in data.data:
                # Setup structural timing blocks
                paid_at_str = item.get("paid_at")
                is_paid = item.get("is_paid", False)
                
                # Default calculation base points
                if paid_at_str:
                    paid_at = datetime.datetime.fromisoformat(paid_at_str.replace("Z", "+00:00"))
                else:
                    paid_at = now
                
                expiry_time = paid_at + datetime.timedelta(days=7)
                time_remaining = expiry_time - now
                total_hours_left = time_remaining.total_seconds() / 3600
                
                # Determine Badge Color Coding based on context rules
                if not is_paid:
                    color_style = "#ff4b4b"  # Crimson Unpaid Red
                    time_status = "⚠️ UNPAID - Rent Overdue"
                elif total_hours_left <= 0:
                    color_style = "#d32f2f"  # Expired Deep Red
                    time_status = "⌛ Term Expired! Collect Gold"
                elif total_hours_left <= 48:
                    color_style = "#ff9800"  # Critical warning Amber Orange
                    days = int(time_remaining.days)
                    hours = int((time_remaining.seconds) // 3600)
                    time_status = f"⏳ {days}d {hours}h left (Critical)"
                else:
                    color_style = "#4caf50"  # Safe Guild Green
                    days = int(time_remaining.days)
                    hours = int((time_remaining.seconds) // 3600)
                    time_status = f"✅ {days}d {hours}h safe"

                # Render Asset Parchment Entry Card
                st.markdown(f"""
                <div style="border-left: 6px solid {color_style}; padding: 15px; margin-bottom: 12px; background-color: #221c16; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 18px; font-weight: bold; color: #dfb76c;">{item['property_name']} ({item['property_type']})</span>
                        <span style="background-color: {color_style}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">{time_status}</span>
                    </div>
                    <div style="margin-top: 8px; font-size: 14px; color: #bda88a;">
                        <strong>Current Tenant:</strong> {item['current_tenant'] if item['current_tenant'] else 'None'} | 
                        <strong>Weekly Price:</strong> {item['rent_amount']} Gold Pieces
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("The ledger scroll is empty. No houses or barrels are currently leased.")

    # TAB 2: REGISTER NEW ASSET
    with active_tabs[1]:
        st.subheader("Add Asset to the Scroll")
        with st.form("rent_form"):
            prop_name = st.text_input("Property / Container Location (e.g., Breezehome / Riften Barrel #4)")
            prop_type = st.selectbox("Asset Classification", ["House", "Barrel"])
            tenant = st.text_input("Assigned Tenant Name")
            gold = st.number_input("Weekly Rent (Gold Pieces)", min_value=0, step=25)
            paid = st.checkbox("Mark as Paid for this Week (Starts 7-day Timer)", value=True)
            
            if st.form_submit_button("Seal Agreement with Wax"):
                if prop_name:
                    ins_data = {
                        "property_name": prop_name,
                        "property_type": prop_type,
                        "current_tenant": tenant,
                        "rent_amount": gold,
                        "is_paid": paid,
                        "paid_at": datetime.datetime.now(datetime.timezone.utc).isoformat() if paid else None
                    }
                    supabase.table("rentals").insert(ins_data).execute()
                    st.success(f"Added {prop_name} safely to the dynamic manifest!")
                    st.rerun()
                else:
                    st.error("Your asset must have a location description name!")

    # TAB 3: EDIT EXISTING PROPERTIES / REMOVE FROM LEDGER
    with active_tabs[2]:
        st.subheader("Amend or Erase Existing Listings")
        edit_data = supabase.table("rentals").select("*").order("id").execute()
        
        if edit_data.data:
            # Map clean option naming strings for editing dropdown selections
            property_options = {f"{row['id']} - {row['property_name']}": row for row in edit_data.data}
            selected_key = st.selectbox("Choose property to alter or destroy:", list(property_options.keys()))
            
            target_row = property_options[selected_key]
            
            # Sub-form structure containing the targeted edit objects
            st.markdown("---")
            st.markdown(f"#### Editing Entry ID: {target_row['id']}")
            
            new_name = st.text_input("Modify Property Name", value=target_row['property_name'])
            new_type = st.selectbox("Modify Classification", ["House", "Barrel"], index=["House", "Barrel"].index(target_row['property_type']))
            new_tenant = st.text_input("Update Tenant Name", value=target_row['current_tenant'] if target_row['current_tenant'] else "")
            new_gold = st.number_input("Update Weekly Rent (Gold)", min_value=0, value=int(target_row['rent_amount']), step=25)
            
            # Handle payment transitions to restart the 7-day clock
            current_payment_status = target_row['is_paid']
            new_paid = st.checkbox("Weekly Rent Paid", value=current_payment_status)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Apply Ledger Modifications"):
                    update_payload = {
                        "property_name": new_name,
                        "property_type": new_type,
                        "current_tenant": new_tenant,
                        "rent_amount": new_gold,
                        "is_paid": new_paid,
                    }
                    # If turning payment status from Unpaid to Paid, reset countdown clock natively
                    if new_paid and not current_payment_status:
                        update_payload["paid_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    elif not new_paid:
                        update_payload["paid_at"] = None
                        
                    supabase.table("rentals").update(update_payload).eq("id", target_row['id']).execute()
                    st.success("Entry details successfully rewritten in ink.")
                    st.rerun()
                    
            with col2:
                if st.button("🚨 Strike from Ledger (Delete Record)"):
                    supabase.table("rentals").delete().eq("id", target_row['id']).execute()
                    st.success("Record permanently removed from the Hold records.")
                    st.rerun()
        else:
            st.info("No recorded assets found to modify.")

    # TAB 4: MASTER USER CONTROLS (Jarl Only)
    with active_tabs[3]:
        st.subheader("The Jarl's Decree")
