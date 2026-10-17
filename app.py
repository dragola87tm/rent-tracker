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
    st.session_state.user_email = ""

if not st.session_state.logged_in:
    st.subheader("Identify Yourself to the Guard")
    username = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    
    if st.button("Enter Winterhold"):
        try:
            res = supabase.auth.sign_in_with_password({"email": username, "password": password})
            st.session_state.logged_in = True
            st.session_state.user_email = username
                        # Safe list parsing to extract your role string correctly
            user_id = res.user.id
            profile = supabase.table("user_profiles").select("role").eq("id", user_id).execute()
            
            if profile.data and len(profile.data) > 0:
                st.session_state.user_role = profile.data[0]["role"]
            else:
                st.session_state.user_role = "Steward"
                
            st.rerun()

        except Exception:
            st.error("You committed crimes against Skyrim and her people! (Invalid Credentials)")
else:
    st.sidebar.markdown(f"**Current Rank:** {st.session_state.user_role}")
    st.sidebar.markdown(f"**User:** {st.session_state.user_email}")
    if st.sidebar.button("Leave Hold (Logout)"):
        st.session_state.logged_in = False
        st.rerun()

    active_tabs = st.tabs(["📋 View Ledger", "🪙 Register Asset", "⚙️ Manage & Edit Assets", "✉️ Contact Jarl", "👑 Jarl's Court"])

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
            
            new_tenant = st.text_input("Update Tenant Name", value=target_row['current_tenant'] if target_row['current_tenant'] else "")
            raw_rent = target_row.get('rent_amount')
            clean_rent = int(raw_rent) if raw_rent is not None else 0
            
            new_gold = st.number_input("Update Weekly Rent (Gold)", min_value=0, value=clean_rent)
            current_payment_status = target_row['is_paid']
            new_paid = st.checkbox("Weekly Rent Paid", value=current_payment_status)
                        # Safe classification parsing with fallback default
            current_type = target_row.get('property_type', 'House')
            default_index = ["House", "Barrel"].index(current_type) if current_type in ["House", "Barrel"] else 0
            
            new_type = st.selectbox("Modify Classification", ["House", "Barrel"], index=default_index)

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


        else:
            st.info("No recorded assets found to modify.")

    # TAB 4: CONTACT JARL (Steward Message Panel)
    with active_tabs[3]:
        st.subheader("Send a Courier to the Jarl")
        with st.form("message_jarl_form"):
            msg_text = st.text_area("Write your message here, Steward...", max_chars=500)
            if st.form_submit_button("Send Courier to Dragonsreach"):
                if msg_text.strip():
                    supabase.table("hold_messages").insert({
                        "sender_username": st.session_state.user_email,
                        "message_content": msg_text.strip()
                    }).execute()
                    st.success("Your message has been handed over to a courier!")
                else:
                    st.error("The parchment is blank! Write a message first.")
    # TAB 5: JARL'S COURT (Jarl Only)
    with active_tabs[4]:
        st.subheader("The Jarl's Royal Court & Vault")
        if st.session_state.user_role != "Jarl":
            st.error("Stop right there! You do not have the Jarl's authority to access these chambers.")
        else:
            # --- GOLD VAULT SECTION ---
            st.markdown("### 🪙 The Hold Treasury")
            
            # Fetch data to calculate calculated vault amounts
            all_rentals = supabase.table("rentals").select("property_name").eq("id", -1).execute()
            
            # Safe database check to read manual rectification value from index array list
            rect_row = supabase.table("rentals").select("rent_amount").eq("id", -1).execute()
            rectification_modifier = rect_row.data[0]["rent_amount"] if (rect_row.data and len(rect_row.data) > 0) else 0
            
            # Sum up valid automated gold entries from standard active leases
            active_gold_data = supabase.table("rentals").select("rent_amount").eq("is_paid", True).gt("id", 0).execute()
            calculated_gold = sum([row["rent_amount"] for row in active_gold_data.data]) if active_gold_data.data else 0
            
            total_vault_gold = calculated_gold + rectification_modifier

            # Display Ledger Metric Card
            st.markdown(f"""
            <div style="background-color: #2c2217; border: 2px solid #dfb76c; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
                <span style="font-size: 16px; text-transform: uppercase; color: #bda88a; letter-spacing: 2px;">Total Gold Pieces in Vault</span>
                <h1 style="font-size: 45px; color: #dfb76c; margin: 10px 0 0 0; text-shadow: 3px 3px 0px #000;">💰 {total_vault_gold} o</h1>
                <p style="font-size: 12px; color: #8e7a63; margin-top: 5px;">(Base Ledger: {calculated_gold}g | Jarl Adjustments: {rectification_modifier:+}g)</p>
            </div>
            """, unsafe_allow_html=True)

            # Rectify Treasury Errors Form
            with st.expander("⚖️ Rectify Vault Accounting Errors"):
                st.info("Adjust the balance directly if taxes or unexpected debts changed the treasury vault calculation totals.")
                new_rect = st.number_input("Adjustment Value (Can be positive or negative)", value=int(rectification_modifier), step=50)
                if st.button("Apply Vault Rectification"):
                    if rect_row.data and len(rect_row.data) > 0:
                        supabase.table("rentals").update({"rent_amount": new_rect}).eq("id", -1).execute()
                    else:
                        supabase.table("rentals").insert({"id": -1, "property_name": "VAULT_MODIFIER", "property_type": "System", "rent_amount": new_rect, "is_paid": True}).execute()
                    st.success("Treasury values updated in the high book.")
                    st.rerun()

            # --- MESSAGES PANEL SECTION ---
            st.markdown("---")
            st.markdown("### ✉️ Courier Reports (Steward Messages)")
            messages_data = supabase.table("hold_messages").select("*").order("sent_at", desc=True).execute()
            
            if messages_data.data:
                for msg in messages_data.data:
                    st.markdown(f"""
                    <div style="background-color: #1f1a14; border-left: 4px solid #bda88a; padding: 12px; margin-bottom: 8px;">
                        <strong style="color:#dfb76c;">From:</strong> {msg['sender_username']}<br/>
                        <span style="font-size:14px; color:#d4c4a8;">{msg['message_content']}</span><br/>
                        <small style="color:#6e5f4f;">Received at: {msg['sent_at'][:16]}</small>
                    </div>
                    """, unsafe_allow_html=True)
                if st.button("Clear All Read Messages"):
                    supabase.table("hold_messages").delete().neq("id", 0).execute()
                    st.success("All messages cleared!")
                    st.rerun()
            else:
                st.info("No messages brought by courier today.")

            # --- USER BANISHMENT CONTROL ---
            st.markdown("---")
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
