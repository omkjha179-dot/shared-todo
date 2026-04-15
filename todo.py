import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Shared To-Do", layout="wide")
st.title("🚀 Shared To-Do List - You vs Friend")

# ================== Supabase Connection ==================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "your-anon-key")

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

if "current_user" not in st.session_state:
    st.session_state.current_user = None

users = ["Om", "Keshab"]   

if not st.session_state.current_user:
    st.subheader("Choose your name")
    selected = st.selectbox("Who are you?", users)
    if st.button("Login"):
        st.session_state.current_user = selected
        st.rerun()
else:
    st.sidebar.success(f"Logged in as: **{st.session_state.current_user}**")
    if st.sidebar.button("Switch User"):
        st.session_state.current_user = None
        st.rerun()

    current_user = st.session_state.current_user

    st.subheader("Add New Task")
    with st.form("add_task"):
        title = st.text_input("Task Title")
        desc = st.text_area("Description (optional)")
        if st.form_submit_button("Add Task"):
            if title:
                supabase.table("tasks").insert({
                    "title": title,
                    "description": desc,
                    "completed": False,
                    "user_id": current_user
                }).execute()
                st.success("Task added!")
                st.rerun()

    st.subheader("All Shared Tasks")
    response = supabase.table("tasks").select("*").order("created_at", desc=True).execute()
    tasks = response.data

    if tasks:
        df = pd.DataFrame(tasks)
        df['created_at'] = pd.to_datetime(df['created_at'])

        for _, task in df.iterrows():
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                checked = st.checkbox(task['title'], value=task['completed'], key=f"chk_{task['id']}")
                if checked != task['completed']:
                    supabase.table("tasks").update({
                        "completed": checked,
                        "completed_at": datetime.now().isoformat() if checked else None
                    }).eq("id", task['id']).execute()
                    st.rerun()
            with col2:
                st.caption(f"by {task['user_id']}")
            with col3:
                if st.button("🗑", key=f"del_{task['id']}"):
                    supabase.table("tasks").delete().eq("id", task['id']).execute()
                    st.rerun()
    else:
        st.info("No tasks yet. Add one above!")

st.subheader("📊 Monthly Productivity (You vs Friend)")
if st.button("Generate This Month's Summary"):
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

        # Get all tasks this month
        resp = supabase.table("tasks").select("*").gte("created_at", month_start).execute()
        month_tasks = resp.data

        if month_tasks:
            df_month = pd.DataFrame(month_tasks)
            df_month['created_at'] = pd.to_datetime(df_month['created_at'])

            summary = []
            for user in users:
                user_tasks = df_month[df_month['user_id'] == user]
                total = len(user_tasks)
                completed = len(user_tasks[user_tasks['completed'] == True])
                rate = round((completed / total * 100), 1) if total > 0 else 0

                summary.append({
                    "User": user,
                    "Total Tasks": total,
                    "Completed": completed,
                    "Completion %": rate
                })

            summary_df = pd.DataFrame(summary)

            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
            with col2:
                fig = px.bar(summary_df, x="User", y=["Total Tasks", "Completed"],
                             title="You vs Friend This Month",
                             barmode="group", text_auto=True)
                st.plotly_chart(fig, use_container_width=True)

            # Winner message
            winner = summary_df.loc[summary_df["Completed"].idxmax(), "User"]
            st.success(f"🏆 **{winner}** is leading this month!")
        else:
            st.info("No tasks recorded this month yet.")

