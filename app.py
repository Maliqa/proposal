import streamlit as st
import pandas as pd
import sqlite3
import datetime
import os

# --- Database Functions ---
def init_db():
    with sqlite3.connect('project_mapping.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                category TEXT NOT NULL,
                pic TEXT NOT NULL,
                status TEXT NOT NULL,
                date_start TEXT NOT NULL,
                date_end TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS project_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        conn.commit()

@st.cache_resource
def get_connection():
    return sqlite3.connect('project_mapping.db', check_same_thread=False)

def get_all_projects():
    try:
        with get_connection() as conn:
            df = pd.read_sql("SELECT * FROM projects", conn)
        return df
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return pd.DataFrame()

def add_project(project_name, category, pic, status, date_start, date_end):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO projects (project_name, category, pic, status, date_start, date_end) VALUES (?, ?, ?, ?, ?, ?)",
                (project_name, category, pic, status, date_start.strftime('%Y-%m-%d'), date_end.strftime('%Y-%m-%d'))
            )
            conn.commit()
            st.success("Project added successfully!")
    except sqlite3.Error as e:
        st.error(f"Error adding project: {e}")

def update_project(id, project_name, category, pic, status, date_start, date_end):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE projects SET project_name=?, category=?, pic=?, status=?, date_start=?, date_end=? WHERE id=?",
                (project_name, category, pic, status, date_start.strftime('%Y-%m-%d'), date_end.strftime('%Y-%m-%d'), id)
            )
            conn.commit()
            st.success("Project updated successfully!")
    except sqlite3.Error as e:
        st.error(f"Error updating project: {e}")

def delete_project(id):
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM projects WHERE id=?", (id,))
            conn.commit()
            st.success("Project deleted successfully!")
    except sqlite3.Error as e:
        st.error(f"Error deleting project: {e}")

# --- File Management Functions ---
def upload_file(project_id, uploaded_file):
    if uploaded_file is not None:
        directory = f"files/project_{project_id}/"
        os.makedirs(directory, exist_ok=True)

        filepath = os.path.join(directory, uploaded_file.name)

        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO project_files (project_id, file_name, file_path) VALUES (?, ?, ?)",
                (project_id, uploaded_file.name, filepath)
            )
            conn.commit()
            st.success("File uploaded successfully!")

def delete_file(file_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_files WHERE id=?", (file_id,))
            row = cursor.fetchone()
            
            # Check if row exists
            if row is None:
                st.error("File does not exist in the database.")
                return
            
            # Check if file exists on disk
            if os.path.exists(row[2]):
                os.remove(row[2])
                cursor.execute("DELETE FROM project_files WHERE id=?", (file_id,))
                conn.commit()
                st.success("File deleted successfully!")
            else:
                st.error("File does not exist on disk.")
    except Exception as e:
        st.error(f"Error deleting the file: {e}")


# --- Streamlit App ---
init_db()
st.image("cistech.png", width=350)

st.title("Dashboard Mapping Project")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["View Projects", "Add Project", "Edit Project", "Delete Project", "Manage Files"])

with tab1:
    df = get_all_projects()
    if not df.empty:
        display_df = df.rename(columns={
            'project_name': 'Project',
            'category': 'Category',
            'pic': 'PIC',
            'status': 'Status',
            'date_start': 'Start Date',
            'date_end': 'End Date'
        }).reset_index(drop=True)
        display_df.index += 1
        st.dataframe(display_df.drop('id', axis=1), use_container_width=True)
    else:
        st.info("No Projects found in the database.")

with tab2:
    st.subheader("Add New Project")
    with st.form(key="add_project_form"):
        new_category = st.selectbox("Category", ["Project", "Service"])
        new_project = st.text_input("Project Name")
        new_pic = st.text_input("PIC")
        new_status = st.selectbox("Status", ["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"])

        st.write("Select Start and End Dates")
        today = datetime.date.today()
        start_date, end_date = st.date_input(
            "Select Start and End",
            value=(today, today + datetime.timedelta(days=30)),
            min_value=today - datetime.timedelta(days=365),
            max_value=today + datetime.timedelta(days=365),
        )

        submit_button = st.form_submit_button(label="Add Project")

        if submit_button:
            if new_project and new_pic:
                if isinstance((start_date, end_date), tuple) and len((start_date, end_date)) == 2:
                    add_project(new_project, new_category, new_pic, new_status, start_date, end_date)
                else:
                    st.error("Please select both start and end dates.")
            else:
                st.error("Project Name and PIC are required!")

with tab3:
    st.subheader("Edit Project")
    df = get_all_projects()
    if not df.empty:
        options = df[['id', 'project_name']].copy()
        selected_option = st.selectbox(
            "Select Project to Edit",
            options['id'].tolist(),
            format_func=lambda x: options[options['id'] == x]['project_name'].iloc[0]
        )

        selected_row = df[df['id'] == selected_option].iloc[0]
        with st.form(key="edit_form"):
            edit_category = st.selectbox(
                "Category",
                ["Project", "Service"],
                index=["Project", "Service"].index(selected_row['category'])
            )
            edit_projname = st.text_input("Name of the Project:", selected_row["project_name"])
            edit_pic = st.text_input("PIC:", selected_row["pic"])
            edit_status = st.selectbox(
                "Status",
                ["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"],
                index=["Not Started", "Waiting BA", "Not Report", "In Progress", "On Hold", "Completed"].index(selected_row["status"])
            )
            start_dt = datetime.datetime.strptime(selected_row['date_start'], '%Y-%m-%d').date()
            end_dt = datetime.datetime.strptime(selected_row['date_end'], '%Y-%m-%d').date()
            start_dt, end_dt = st.date_input(
                "Select start and end dates",
                value=(start_dt, end_dt),
                min_value=datetime.date.today() - datetime.timedelta(days=365),
                max_value=datetime.date.today() + datetime.timedelta(days=365)
            )

            update_btn = st.form_submit_button(label="Update Project")

            if update_btn:
                if edit_projname and edit_pic:
                    if isinstance((start_dt, end_dt), tuple) and len((start_dt, end_dt)) == 2:
                        update_project(selected_option, edit_projname, edit_category, edit_pic, edit_status, start_dt, end_dt)
                    else:
                        st.error("Please select both start & end dates.")
                else:
                    st.error("Name of the Project & PIC are required!")

with tab4:
    st.subheader("Delete Projects")
    df = get_all_projects()
    if not df.empty:
        delete_options = df[['id', 'project_name']].copy()
        delete_selected_option = st.selectbox(
            "Choose a Project to Delete",
            delete_options['id'].tolist(),
            format_func=lambda x: delete_options[delete_options['id'] == x]['project_name'].iloc[0]
        )

        if st.button(label="Delete Selected Project"):
            delete_project(delete_selected_option)

    else:
        st.info("No projects found.")

with tab5:
    st.subheader("Manage Files for Each Project")
    df_projects = get_all_projects()

    if not df_projects.empty:
        selected_project_for_files = st.selectbox(
            "Choose a Project to Manage Files",
            df_projects['id'].tolist(),
            format_func=lambda x: df_projects[df_projects['id'] == x]['project_name'].iloc[0]
        )

        uploading_new_file = st.file_uploader("Upload New File Here", type=["pdf", "docx", "png", "jpg", "jpeg", "xlsx", "xls"])

        if st.button(label="Upload New File"):
            upload_file(selected_project_for_files, uploading_new_file)

        files_df = pd.read_sql_query(
            f'''
            SELECT pf.id, pf.file_name, pf.file_path
            FROM project_files pf
            WHERE pf.project_id = {selected_project_for_files}
            ''',
            con=get_connection()
        )

        if not files_df.empty:
            for index, row in files_df.iterrows():
                col_1, col_2, col_3 = st.columns([6, 2, 1])
                col_1.write(row['file_name'])

                with open(row['file_path'], 'rb') as f:
                    col_2.download_button(
                        label="Download",
                        data=f.read(),
                        file_name=row['file_name'],
                        mime='application/octet-stream',
                        key=f'download-{row["id"]}'
                    )

              
        else:
            st.info("No files found for this project.")
    else:
        st.info("No projects available to manage files.")
