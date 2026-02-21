import streamlit as st
import requests
import json
import os
from datetime import datetime

st.set_page_config(page_title="Admin Dashboard - Patient Management", layout="wide")

# API base URL
API_URL = st.secrets.get(
    "API_URL",
    os.getenv("API_URL", "https://807pdm6rih.execute-api.us-east-1.amazonaws.com")
)

st.title("⚙️ Admin Dashboard - Patient & Medication Management")

# Sidebar for navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select Section:",
        ["Patients", "Medications", "Sessions"]
    )

# ============================================================================
# PATIENTS PAGE
# ============================================================================

if page == "Patients":
    st.header("Patient Management")
    
    tab1, tab2, tab3 = st.tabs(["View Patients", "Add Patient", "Edit/Delete Patient"])
    
    # TAB 1: View Patients
    with tab1:
        st.subheader("All Patients")
        
        if st.button("Refresh Patient List", key="refresh_patients"):
            st.rerun()
        
        try:
            response = requests.get(f"{API_URL}/patients")
            if response.status_code == 200:
                data = response.json()
                patients = data.get("patients", [])
                
                if patients:
                    cols = st.columns([1, 2, 2, 2, 1])
                    with cols[0]:
                        st.write("**ID**")
                    with cols[1]:
                        st.write("**First Name**")
                    with cols[2]:
                        st.write("**Last Name**")
                    with cols[3]:
                        st.write("**Pairing Code**")
                    with cols[4]:
                        st.write("**Meds**")
                    
                    st.divider()
                    
                    for patient in patients:
                        cols = st.columns([1, 2, 2, 2, 1])
                        with cols[0]:
                            st.write(patient["patient_id"])
                        with cols[1]:
                            st.write(patient["first_name"])
                        with cols[2]:
                            st.write(patient["last_name"])
                        with cols[3]:
                            st.write(patient["pairing_code"])
                        with cols[4]:
                            # Get medication count for this patient
                            try:
                                med_response = requests.get(
                                    f"{API_URL}/patients/{patient['patient_id']}/medications"
                                )
                                if med_response.status_code == 200:
                                    med_count = len(med_response.json().get("medications", []))
                                    st.write(f"{med_count}")
                            except:
                                st.write("N/A")
                else:
                    st.info("No patients found")
            else:
                st.error("Error fetching patients")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
    
    # TAB 2: Add Patient
    with tab2:
        st.subheader("Add New Patient")
        
        with st.form("add_patient_form"):
            first_name = st.text_input("First Name", key="new_first_name")
            last_name = st.text_input("Last Name", key="new_last_name")
            pairing_code = st.text_input("Pairing Code (e.g., 1234)", key="new_pairing_code")
            
            submitted = st.form_submit_button("Add Patient")
            
            if submitted:
                if not all([first_name, last_name, pairing_code]):
                    st.error("Please fill in all required fields")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/patients",
                            json={
                                "first_name": first_name,
                                "last_name": last_name,
                                "pairing_code": pairing_code,
                                "is_active": True
                            }
                        )
                        
                        if response.status_code == 200:
                            patient_resp = response.json()
                            st.success(f"Patient {patient_resp.get('patient_id')} added successfully!")
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
    
    # TAB 3: Edit/Delete Patient
    with tab3:
        st.subheader("Edit or Delete Patient")
        
        patient_id = st.text_input("Enter Patient ID to edit/delete:", key="edit_patient_id")
        
        if patient_id:
            try:
                response = requests.get(f"{API_URL}/patients/{patient_id}")
                if response.status_code == 200:
                    patient = response.json()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Current Information")
                        st.write(f"**ID:** {patient['patient_id']}")
                        st.write(f"**First Name:** {patient['first_name']}")
                        st.write(f"**Last Name:** {patient['last_name']}")
                        st.write(f"**Pairing Code:** {patient['pairing_code']}")
                        st.write(f"**Active:** {patient['is_active']}")
                    
                    with col2:
                        st.subheader("Update Information")
                        st.write(f"*Only Pairing Code and Active status can be changed*")
                        
                        with st.form("edit_patient_form"):
                            pairing_code = st.text_input("Pairing Code", value=patient['pairing_code'], key="edit_pairing_code")
                            is_active = st.checkbox("Active", value=patient['is_active'], key="edit_is_active")
                            
                            submitted = st.form_submit_button("Update Patient")
                            
                            if submitted:
                                try:
                                    response = requests.put(
                                        f"{API_URL}/patients/{patient_id}",
                                        json={
                                            "first_name": patient['first_name'],
                                            "last_name": patient['last_name'],
                                            "pairing_code": pairing_code,
                                            "is_active": is_active
                                        }
                                    )
                                    
                                    if response.status_code == 200:
                                        st.success("Patient updated successfully!")
                                    else:
                                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"Connection error: {str(e)}")
                    
                    # Delete section
                    st.divider()
                    if st.button("Delete Patient", key="delete_patient_btn", type="secondary"):
                        try:
                            response = requests.delete(f"{API_URL}/patients/{patient_id}")
                            if response.status_code == 200:
                                st.success(f"Patient {patient_id} deleted successfully!")
                            else:
                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")
                else:
                    st.error("Patient not found")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

# ============================================================================
# MEDICATIONS PAGE
# ============================================================================

elif page == "Medications":
    st.header("Medication Management")
    
    tab1, tab2, tab3 = st.tabs(["Add Medication", "View All Medications", "Edit Medication"])
    
    # TAB 1: Add Medication
    with tab1:
        st.subheader("Add Medication to Patient")
        
        patient_id = st.text_input("Patient ID:", key="med_patient_id")
        
        if patient_id:
            try:
                response = requests.get(f"{API_URL}/patients/{patient_id}")
                if response.status_code == 200:
                    patient = response.json()
                    st.write(f"Patient: {patient['first_name']} {patient['last_name']}")
                    
                    col1, col2 = st.columns(2)
                    
                    # BUTTON 1: Select Existing Medication
                    with col1:
                        if st.button("Select Existing Medication", key="btn_select_med"):
                            st.session_state.med_action = "select"
                    
                    # BUTTON 2: Add New Medication
                    with col2:
                        if st.button("Add New Medication", key="btn_add_new_med"):
                            st.session_state.med_action = "new"
                    
                    # Handle selected action
                    if "med_action" in st.session_state:
                        if st.session_state.med_action == "select":
                            st.subheader("Select Existing Medication")
                            
                            try:
                                response = requests.get(f"{API_URL}/medications")
                                if response.status_code == 200:
                                    all_meds = response.json().get("medications", [])
                                    if all_meds:
                                        med_options = {
                                            f"{m['name']} ({m['dose']}, {m.get('frequency', 'once')} daily)": m
                                            for m in all_meds
                                        }
                                        selected_med = st.selectbox("Choose medication:", list(med_options.keys()), key="select_existing_med")
                                        
                                        if st.button("Confirm & Add", key="confirm_existing_med"):
                                            selected_med_obj = med_options[selected_med]
                                            selected_med_id = selected_med_obj['medication_id']
                                            try:
                                                # Link existing medication to patient
                                                response = requests.post(
                                                    f"{API_URL}/patients/{patient_id}/medications",
                                                    json={
                                                        "medication_id": selected_med_id,
                                                        "name": selected_med_obj['name'],
                                                        "dose": selected_med_obj['dose'],
                                                        "frequency": selected_med_obj.get('frequency', 'once')
                                                    }
                                                )
                                                
                                                if response.status_code == 200:
                                                    st.success("Medication added to patient!")
                                                    del st.session_state.med_action
                                                else:
                                                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                            except Exception as e:
                                                st.error(f"Connection error: {str(e)}")
                                    else:
                                        st.info("No existing medications found. Create a new one instead.")
                            except Exception as e:
                                st.error(f"Error fetching medications: {str(e)}")
                        
                        elif st.session_state.med_action == "new":
                            st.subheader("Create New Medication")
                            
                            with st.form("add_new_medication_form"):
                                name = st.text_input("Medication Name (e.g., Lisinopril)", key="new_med_name")
                                dose = st.text_input("Dose (e.g., 20 mg)", key="new_med_dose")
                                frequency = st.text_input("Frequency (e.g., once, twice, thrice)", value="once", key="new_med_frequency")
                                
                                submitted = st.form_submit_button("Create & Add Medication")
                                
                                if submitted:
                                    if not all([name, dose, frequency]):
                                        st.error("Please fill in all fields")
                                    else:
                                        try:
                                            response = requests.post(
                                                f"{API_URL}/patients/{patient_id}/medications",
                                                json={
                                                    "name": name,
                                                    "dose": dose,
                                                    "frequency": frequency
                                                }
                                            )
                                            
                                            if response.status_code == 200:
                                                med_resp = response.json()
                                                st.success(f"Medication {med_resp.get('medication_id')} created and added successfully!")
                                                del st.session_state.med_action
                                            else:
                                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                        except Exception as e:
                                            st.error(f"Connection error: {str(e)}")
                else:
                    st.error("Patient not found")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")
    
    # TAB 2: View All Medications
    with tab2:
        st.subheader("All Medications & Patients")
        
        try:
            # Fetch all medications
            med_response = requests.get(f"{API_URL}/medications")
            if med_response.status_code == 200:
                all_meds = med_response.json().get("medications", [])
                
                # Fetch all patients for patient name lookup
                patient_response = requests.get(f"{API_URL}/patients")
                if patient_response.status_code == 200:
                    patient_data = patient_response.json().get("patients", [])
                    patient_map = {p['patient_id']: f"{p['first_name']} {p['last_name']}" for p in patient_data}
                    
                    if all_meds:
                        st.write(f"**Total Medications: {len(all_meds)}**")
                        st.divider()
                        
                        # Display each medication with associated patient
                        for med in all_meds:
                            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 2, 1])
                            
                            with col1:
                                st.write(f"**{med['name']}**")
                            with col2:
                                st.caption(f"{med['dose']}")
                            with col3:
                                st.caption(f"{med.get('frequency', 'once')} daily")
                            with col4:
                                patient_name = patient_map.get(med['patient_id'], "Unassigned")
                                st.write(patient_name)
                            with col5:
                                if st.button("Remove", key=f"remove_med_{med['medication_id']}", type="secondary"):
                                    try:
                                        response = requests.delete(
                                            f"{API_URL}/patients/{med['patient_id']}/medications/{med['medication_id']}"
                                        )
                                        if response.status_code == 200:
                                            st.success("Medication removed!")
                                            st.rerun()
                                        else:
                                            st.error("Error removing medication")
                                    except Exception as e:
                                        st.error(f"Connection error: {str(e)}")
                    else:
                        st.info("No medications found")
                else:
                    st.error("Error fetching patients")
            else:
                st.error("Error fetching medications")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
    
    # TAB 3: Edit Medication
    with tab3:
        st.subheader("Edit or Delete Medication")
        
        try:
            # Fetch all medications
            med_response = requests.get(f"{API_URL}/medications")
            if med_response.status_code == 200:
                all_meds = med_response.json().get("medications", [])
                
                if all_meds:
                    # Create dropdown of all medications
                    med_options = {
                        f"{m['name']} ({m['dose']}, {m.get('frequency', 'once')} daily) - ID: {m['medication_id']}": m['medication_id']
                        for m in all_meds
                    }
                    
                    selected_med_display = st.selectbox(
                        "Select medication to edit:",
                        list(med_options.keys()),
                        key="edit_med_select"
                    )
                    
                    selected_med_id = med_options[selected_med_display]
                    
                    # Find the selected medication
                    selected_med = next((m for m in all_meds if m['medication_id'] == selected_med_id), None)
                    
                    if selected_med:
                        # Display current patient info
                        patient_response = requests.get(f"{API_URL}/patients/{selected_med['patient_id']}")
                        patient_name = "Unknown"
                        if patient_response.status_code == 200:
                            patient = patient_response.json()
                            patient_name = f"{patient['first_name']} {patient['last_name']}"
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Current Information")
                            st.write(f"**Medication ID:** {selected_med['medication_id']}")
                            st.write(f"**Patient:** {patient_name}")
                            st.write(f"**Current Name:** {selected_med['name']}")
                            st.write(f"**Current Dose:** {selected_med['dose']}")
                            st.write(f"**Current Frequency:** {selected_med.get('frequency', 'once')}")
                        
                        with col2:
                            st.subheader("Update Information")
                            
                            with st.form("edit_medication_form"):
                                new_name = st.text_input("Medication Name", value=selected_med['name'], key="edit_med_name")
                                new_dose = st.text_input("Dose", value=selected_med['dose'], key="edit_med_dose")
                                new_frequency = st.text_input("Frequency", value=selected_med.get('frequency', 'once'), key="edit_med_frequency")
                                
                                col_update, col_delete = st.columns(2)
                                
                                with col_update:
                                    update_submitted = st.form_submit_button("Update Medication", type="primary")
                                
                                with col_delete:
                                    delete_submitted = st.form_submit_button("Delete Medication", type="secondary")
                                
                                if update_submitted:
                                    if not all([new_name, new_dose, new_frequency]):
                                        st.error("Please fill in all fields")
                                    else:
                                        try:
                                            response = requests.put(
                                                f"{API_URL}/medications/{selected_med_id}",
                                                json={
                                                    "medication_id": selected_med_id,
                                                    "patient_id": selected_med['patient_id'],
                                                    "name": new_name,
                                                    "dose": new_dose,
                                                    "frequency": new_frequency
                                                }
                                            )
                                            
                                            if response.status_code == 200:
                                                st.success("Medication updated successfully!")
                                                st.rerun()
                                            else:
                                                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                        except Exception as e:
                                            st.error(f"Connection error: {str(e)}")
                                
                                if delete_submitted:
                                    try:
                                        response = requests.delete(
                                            f"{API_URL}/patients/{selected_med['patient_id']}/medications/{selected_med_id}"
                                        )
                                        
                                        if response.status_code == 200:
                                            st.success("Medication deleted successfully!")
                                            st.rerun()
                                        else:
                                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                                    except Exception as e:
                                        st.error(f"Connection error: {str(e)}")
                else:
                    st.info("No medications found")
            else:
                st.error("Error fetching medications")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

# ============================================================================
# SESSIONS PAGE
# ============================================================================

elif page == "Sessions":
    st.header("Patient Session Viewer")
    view_all_patients = st.checkbox("View all patients", key="view_all_patients")

    def render_sessions_for_patient(current_patient_id: str, show_patient_header: bool = False):
        try:
            patient_response = requests.get(f"{API_URL}/patients/{current_patient_id}")
            if patient_response.status_code != 200:
                st.error(f"Patient {current_patient_id} not found")
                return

            patient = patient_response.json()

            if show_patient_header:
                st.subheader(f"Patient {patient['patient_id']} - {patient['first_name']} {patient['last_name']}")
            else:
                st.subheader("Patient Information")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Patient ID", patient['patient_id'])
            with col2:
                st.metric("Name", f"{patient['first_name']} {patient['last_name']}")
            with col3:
                st.metric("Pairing Code", patient['pairing_code'])
            with col4:
                st.metric("Status", "🟢 Active" if patient['is_active'] else "🔴 Inactive")

            st.subheader("Medications")
            med_response = requests.get(f"{API_URL}/patients/{current_patient_id}/medications")
            if med_response.status_code == 200:
                medications = med_response.json().get('medications', [])
                if medications:
                    med_cols = st.columns([2, 1, 1, 1])
                    with med_cols[0]:
                        st.write("**Name**")
                    with med_cols[1]:
                        st.write("**Dose**")
                    with med_cols[2]:
                        st.write("**Frequency**")
                    with med_cols[3]:
                        st.write("**ID**")
                    st.divider()

                    for med in medications:
                        med_cols = st.columns([2, 1, 1, 1])
                        with med_cols[0]:
                            st.write(med['name'])
                        with med_cols[1]:
                            st.write(med['dose'])
                        with med_cols[2]:
                            st.write(med.get('frequency', 'once'))
                        with med_cols[3]:
                            st.write(med['medication_id'])
                else:
                    st.info("No medications assigned")
            else:
                st.warning("Could not fetch medications")

            st.divider()

            sessions_response = requests.get(f"{API_URL}/patients/{current_patient_id}/sessions")
            if sessions_response.status_code == 200:
                sessions = sessions_response.json().get('sessions', [])
                if sessions:
                    st.write(f"**Total sessions: {len(sessions)}**")
                    st.divider()

                    for session in sessions:
                        session_id = session.get('session_id', 'Unknown')
                        created_at = session.get('created_at', '-')
                        ended_at = session.get('ended_at', '-')
                        st.markdown(f"### Session {session_id}")
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        with meta_col1:
                            st.metric("Created", created_at)
                        with meta_col2:
                            st.metric("Ended", ended_at)
                        with meta_col3:
                            admin_count = len(session.get('medication_administration', []))
                            st.metric("Medication Entries", admin_count)

                        medication_admin = session.get('medication_administration', [])
                        if medication_admin:
                            table_data = []
                            for record in medication_admin:
                                table_data.append({
                                    "Administration ID": record.get('administration_id'),
                                    "Medication ID": record.get('medication_id'),
                                    "Medication Name": record.get('medication_name'),
                                        "Frequency": record.get('medication_frequency', '-'),
                                    "Confirmed": "✅ Yes" if record.get('patient_confirmed') else "❌ No",
                                    "Nurse Contact": "✅ Yes" if record.get('nurse_contact_required') else "❌ No",
                                    "Educational Prompt": "✅ Yes" if record.get('educational_prompt_delivered') else "❌ No",
                                    "Error": record.get('error_description', '-') if record.get('error_flag') else "-",
                                    "Ended At": record.get('ended_at', '-')
                                })
                            st.dataframe(table_data, use_container_width=True)
                        else:
                            st.info("No medication administration entries in this session")

                        st.divider()
                else:
                    st.info("No sessions found")
            else:
                st.warning("Could not fetch sessions")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

    if view_all_patients:
        try:
            all_patients_response = requests.get(f"{API_URL}/patients")
            if all_patients_response.status_code == 200:
                all_patients = all_patients_response.json().get("patients", [])
                if all_patients:
                    for idx, patient in enumerate(all_patients):
                        render_sessions_for_patient(patient['patient_id'], show_patient_header=True)
                        if idx < len(all_patients) - 1:
                            st.markdown("---")
                else:
                    st.info("No patients found")
            else:
                st.warning("Could not fetch patients")
        except Exception as e:
            st.error(f"Error loading patients: {str(e)}")
    else:
        patient_id = st.text_input("Patient ID:", key="session_patient_id")
        if patient_id:
            render_sessions_for_patient(patient_id)

# Footer
st.divider()
st.caption("Admin Dashboard | Alexa Skill - Medication Intervention System")
