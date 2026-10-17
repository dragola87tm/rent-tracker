import streamlit as st
from supabase import create_client, Client
import datetime
from theme import apply_skyrim_theme

# Initialize Supabase Connection
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

apply_skyrim_theme()
st.title("⚔️ The Hold's Rental Ledger")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = "Steward"

if not st.session_state.logged_in:
    st.subheader("Identify Yourself to the Guard")
    username = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    
    if st.button("Enter Winterhold"):
        try:
            res = supabase.auth.sign_in_with_password({"email": username, "password": password})
            st.session_state.logged_in = True
            user_id = res.user.id
            profile = supabase.table("user_profiles").select("role").eq("id", user_id).execute()
            st.session_state.user_role = profile.data[0]["role"] if profile.data else "Steward"
            st.rerun()
        except Exception:
            st.error("You committed crimes against Skyrim and her people! (Invalid Credentials)")
else:
    st.sidebar.markdown(f"**Current Rank:** {st.session_state.user_role}")
    if st.sidebar.button("Leave Hold (Logout)"):
        st.session_state.logged_in = False
        st.rerun()

    active_tabs = st.tabs(["📋 View Ledger", "🪙 Register Asset", "⚙️ Manage & Edit Assets", "👑 Jarl's Court"])

    # TAB 1: VIEW LEDGER
    with active_tabs[0]:
        st.subheader("Current Asset Allocations & Expirations")
        data = supabase.table("rentals").select("*").order("id").execute()
        if data.data:
            now = datetime.datetime.now(datetime.timezone.utc)
            for item in data.data:
                paid_at_str = item.get("paid_at")
                is_paid = item.get("is_paid", False)
                paid_at = datetime.datetime.fromisoformat(paid_at_str.replace("Z", "+00:00")) if paid_at_str else now
                total_hours_left = ((paid_at + datetime.timedelta(days=7)) - now).total_seconds() / 3600
                
                if not is_paid:
                    color_style, time_status = "#ff4b4b", "⚠️ UNPAID - Rent Overdue"
                elif total_hours_left <= 0:
                    color_style, time_status = "#d32f2f", "⌛ Term Expired! Collect Gold"
                elif total_hours_left <= 48:
                    color_style, time_status = "#ff9800", f"⏳ {int(total_hours_left//24)}d {int(total_hours_left%24)}h left"
                else:
                    color_style, time_status = "#4caf50", f"✅ {int(total_hours_left//24)}d {int(total_hours_left%24)}h safe"

                st.markdown(f"""
                <div style="border-left: 6px solid {color_style}; padding: 15px; margin-bottom: 12px; background-color: #221c16; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 18px; font-weight: bold; color: #dfb76c;">{item['property_name']} ({item['property_type']})</span>
                        <span style="background-color: {color_style}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">{time_status}</span>
                    </div>
                    <div style="margin-top: 8px; font-size: 14px; color: #bda88a;">
                        <strong>Tenant:</strong> {item['current_tenant'] if item['current_tenant'] else 'None'} | <strong>Price:</strong> {item['rent_amount']} Gold
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("The ledger scroll is empty.")

    # TAB 2: REGISTER NEW ASSET
    with active_tabs[1]:
        st.subheader("Add Asset to the Scroll")
        with st.form("rent_form"):
            prop_name = st.text_input("Property / Container Location")
            prop_type = st.selectbox("Asset Classification", ["House", "Barrel"])
            tenant = st.text_input("Assigned Tenant Name")
            gold = st.number_input("Weekly Rent (Gold Pieces)", min_value=0, step=25)
            paid = st.checkbox("Mark as Paid for this Week", value=True)
            if st.form_submit_button("Seal Agreement with Wax"):
                if prop_name:
                    supabase.table("rentals").insert({
                        "property_name": prop_name, "property_type": prop_type, "current_tenant": tenant,
                        "rent_amount": gold, "is_paid": paid,
                        "paid_at": datetime.datetime.now(datetime.timezone.utc).isoformat() if paid else None
                    }).execute()
                    st.success("Added safely to the dynamic manifest!")
                    st.rerun()

    # TAB 3: EDIT EXISTING PROPERTIES
    with active_tabs[2]:
        st.subheader("Amend or Erase Existing Listings")
        edit_data = supabase.table("rentals").select("*").order("id").execute()
        if edit_data.data:
            property_options = {f"{row['id']} - {row['property_name']}": row for row in edit_data.data}
            selected_key = st.selectbox("Choose property to alter or destroy:", list(property_options.keys()))
            target_row = property_options[selected_key]
            
            new_name = st.text_input("Modify Property Name", value=target_row['property_name'])
            new_type = st.selectbox("Modify Classification", ["House", "Barrel"], index=["House", "Barrel"].index(target_row['property_type']))
            new_tenant = st.text_input("Update Tenant Name", value=target_row['current_tenant'] if target_row['current_tenant'] else "")
            new_gold = st.number_input("Update Weekly Rent (Gold)", min_value=0, value=int(target_row['rent_amount']))
            current_payment_status = target_row['is_paid']
            new_paid = st.checkbox("Weekly Rent Paid", value=current_payment_status)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Apply Ledger Modifications"):
                    payload = {"property_name": new_name, "property_type": new_type, "current_tenant": new_tenant, "rent_amount": new_gold, "is_paid": new_paid}
                    if new_paid and not current_payment_status:
                        payload["paid_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    elif not new_paid:
                        payload["paid_at"] = None
                    supabase.table("rentals").update(payload).eq("id", target_row['id']).execute()
                    st.success("Entry details rewritten in ink.")
                    st.rerun()
            with col2:
                if st.button("🚨 Strike from Ledger (Delete Record)"):
                    supabase.table("rentals").delete().eq("id", target_row['id']).execute()
                    st.rerun()

    # TAB 4: MASTER USER CONTROLS (Jarl Only)
    with active_tabs[3]:
        st.subheader("The Jarl's Decree")
        if st.session_state.user_role != "Jarl":
            st.error("Stop right there! You do not have the Jarl's authority to access these chambers.")
        else:
            st.warning("Master Controls: Banish Users from the Hold")
            stewards = supabase.table("user_profiles").select("id, username").eq("role", "Steward").execute()
            if stewards.data:
                steward_dict = {user["username"]: user["id"] for user in stewards.data}
                target_user = st.selectbox("Select Steward to Banish", list(steward_dict.keys()))
                if st.button("Behead / Banish User Account"):
                    supabase.table("user_profiles").delete().eq("id", steward_dict[target_user]).execute()
                    supabase.auth.admin.delete_user(steward_dict[target_user])
                    st.rerun()
            else:
                st.info("No subordinate stewards found in the Hold.")
