import streamlit as st
from datetime import date, datetime, time


APP_TITLE = "Nursing Department Task Manager"
PRIORITY_LEVELS = ["High", "Medium", "Low"]
SHIFTS = ["Day", "Evening", "Night"]
DEFAULT_WARDS = [
    "Emergency",
    "ICU",
    "Medical Ward",
    "Surgical Ward",
    "Pediatrics",
    "Maternity",
]


def format_date_range(start_date: date, end_date: date) -> str:
    if start_date == end_date:
        return start_date.strftime("%b %d, %Y")
    return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"


def derive_training_status(training: dict, today: date) -> str:
    if training["completed"]:
        return "Completed"
    if training["start_date"] <= today <= training["end_date"]:
        return "Ongoing"
    if training["end_date"] < today:
        return "Completed"
    return "Upcoming"


def training_in_year(training: dict, year: int) -> bool:
    return training["start_date"].year == year or training["end_date"].year == year


def seed_trainings(today: date) -> list:
    year = today.year
    return [
        {
            "id": "TRN-001",
            "title": "Medication Reconciliation Refresher",
            "start_date": date(year, 1, 15),
            "end_date": date(year, 1, 15),
            "priority": "High",
            "location": "Training Room A",
            "owner": "Education Lead",
            "notes": "Required for onboarding and annual review.",
            "completed": True,
        },
        {
            "id": "TRN-002",
            "title": "Rapid Response and Code Blue",
            "start_date": date(year, 2, 6),
            "end_date": date(year, 2, 8),
            "priority": "High",
            "location": "Simulation Lab",
            "owner": "Critical Care Team",
            "notes": "Includes mock drills for all shifts.",
            "completed": False,
        },
        {
            "id": "TRN-003",
            "title": "IV Therapy Competency",
            "start_date": date(year, 3, 12),
            "end_date": date(year, 3, 13),
            "priority": "Medium",
            "location": "Skills Room",
            "owner": "Nurse Educator",
            "notes": "Bring IV starter kits and PPE.",
            "completed": False,
        },
        {
            "id": "TRN-004",
            "title": "Wound Care Best Practices",
            "start_date": date(year, 5, 5),
            "end_date": date(year, 5, 5),
            "priority": "Low",
            "location": "Conference Room 2",
            "owner": "Clinical Lead",
            "notes": "Optional for outpatient teams.",
            "completed": False,
        },
    ]


def seed_tasks(today: date) -> list:
    return [
        {
            "id": "TSK-001",
            "title": "Admission data collection",
            "ward": "Medical Ward",
            "shift": "Day",
            "priority": "High",
            "task_date": today,
            "due_time": time(9, 30),
            "assigned_to": "RN Team A",
            "notes": "Confirm allergies, home meds, and history.",
            "completed": False,
        },
        {
            "id": "TSK-002",
            "title": "Discharge teaching documentation",
            "ward": "Surgical Ward",
            "shift": "Day",
            "priority": "Medium",
            "task_date": today,
            "due_time": time(11, 0),
            "assigned_to": "RN Team B",
            "notes": "Include wound care and follow-up visits.",
            "completed": False,
        },
        {
            "id": "TSK-003",
            "title": "IV antibiotic administration",
            "ward": "ICU",
            "shift": "Evening",
            "priority": "High",
            "task_date": today,
            "due_time": time(17, 30),
            "assigned_to": "Charge Nurse",
            "notes": "Verify line patency and infusion rate.",
            "completed": False,
        },
        {
            "id": "TSK-004",
            "title": "Vitals rounding and safety checks",
            "ward": "Pediatrics",
            "shift": "Night",
            "priority": "Low",
            "task_date": today,
            "due_time": time(22, 0),
            "assigned_to": "RN Team C",
            "notes": "Include fall prevention checklist.",
            "completed": False,
        },
    ]


def init_state(today: date) -> None:
    if "trainings" not in st.session_state:
        st.session_state.trainings = seed_trainings(today)
        st.session_state.training_counter = len(st.session_state.trainings) + 1
    if "tasks" not in st.session_state:
        st.session_state.tasks = seed_tasks(today)
        st.session_state.task_counter = len(st.session_state.tasks) + 1
    if "uploads" not in st.session_state:
        st.session_state.uploads = []


def next_id(prefix: str, counter_key: str) -> str:
    counter_value = st.session_state.get(counter_key, 1)
    st.session_state[counter_key] = counter_value + 1
    return f"{prefix}-{counter_value:03d}"


def render_training_list(trainings: list, today: date, key_prefix: str) -> None:
    if not trainings:
        st.info("No trainings match the selected filters.")
        return

    priority_rank = {level: idx for idx, level in enumerate(PRIORITY_LEVELS)}
    sorted_trainings = sorted(
        trainings,
        key=lambda training: (
            training["start_date"],
            priority_rank.get(training["priority"], 99),
            training["title"],
        ),
    )

    for training in sorted_trainings:
        status = derive_training_status(training, today)
        with st.container():
            cols = st.columns([0.06, 0.44, 0.2, 0.15, 0.15])
            completed = cols[0].checkbox(
                "",
                value=training["completed"],
                key=f"{key_prefix}_training_done_{training['id']}",
            )
            if completed != training["completed"]:
                training["completed"] = completed
            with cols[1]:
                st.markdown(f"**{training['title']}**")
                st.caption(
                    f"Location: {training['location']} | Owner: {training['owner']}"
                )
            cols[2].markdown(format_date_range(training["start_date"], training["end_date"]))
            cols[3].markdown(training["priority"])
            cols[4].markdown(status)
            if training["notes"]:
                st.caption(training["notes"])
            st.markdown("---")


def render_task_list(tasks: list) -> None:
    if not tasks:
        st.info("No tasks match the selected filters.")
        return

    for task in tasks:
        with st.container():
            cols = st.columns([0.06, 0.3, 0.15, 0.12, 0.12, 0.1, 0.15])
            completed = cols[0].checkbox(
                "",
                value=task["completed"],
                key=f"task_done_{task['id']}",
            )
            if completed != task["completed"]:
                task["completed"] = completed
            cols[1].markdown(f"**{task['title']}**")
            cols[2].markdown(task["ward"])
            cols[3].markdown(task["shift"])
            cols[4].markdown(task["priority"])
            cols[5].markdown(task["due_time"].strftime("%H:%M"))
            cols[6].markdown(task["assigned_to"] or "-")
            if task["notes"]:
                st.caption(task["notes"])
            st.markdown("---")


st.set_page_config(page_title=APP_TITLE, page_icon="🏥", layout="wide")

today = date.today()
init_state(today)

st.title(APP_TITLE)
st.caption(
    "Track nurse trainings, daily nursing tasks, and report uploads in one place."
)

all_wards = sorted(
    {ward for ward in DEFAULT_WARDS}
    | {task["ward"] for task in st.session_state.tasks if task.get("ward")}
)

current_year = today.year
year_options = [current_year - 1, current_year, current_year + 1]

with st.sidebar:
    st.header("Filters")
    selected_year = st.selectbox("Calendar year", year_options, index=1)
    alarm_window = st.slider("Alarm window (days)", 1, 60, 14)
    training_priority_filter = st.multiselect(
        "Training priorities",
        PRIORITY_LEVELS,
        default=PRIORITY_LEVELS,
    )
    task_date_filter = st.date_input(
        "Task date (filter)", value=today, key="task_date_filter"
    )
    ward_filter = st.multiselect("Wards", all_wards, default=all_wards)
    task_priority_filter = st.multiselect(
        "Task priorities",
        PRIORITY_LEVELS,
        default=PRIORITY_LEVELS,
    )

    st.markdown("---")
    st.subheader("Add training")
    with st.form("add_training_form", clear_on_submit=True):
        training_title = st.text_input("Training title")
        training_priority = st.selectbox("Priority", PRIORITY_LEVELS)
        training_start = st.date_input("Start date", value=today, key="training_start")
        training_end = st.date_input("End date", value=today, key="training_end")
        training_location = st.text_input("Location", value="Training Room")
        training_owner = st.text_input("Owner", value="Nurse Educator")
        training_notes = st.text_area("Notes", height=80)
        training_completed = st.checkbox("Mark as completed")
        submitted_training = st.form_submit_button("Add training")
        if submitted_training:
            if not training_title.strip():
                st.error("Training title is required.")
            elif training_end < training_start:
                st.error("End date must be on or after the start date.")
            else:
                st.session_state.trainings.append(
                    {
                        "id": next_id("TRN", "training_counter"),
                        "title": training_title.strip(),
                        "start_date": training_start,
                        "end_date": training_end,
                        "priority": training_priority,
                        "location": training_location.strip() or "Training Room",
                        "owner": training_owner.strip() or "Nurse Educator",
                        "notes": training_notes.strip(),
                        "completed": training_completed,
                    }
                )
                st.success("Training added.")

    st.markdown("---")
    st.subheader("Add daily task")
    with st.form("add_task_form", clear_on_submit=True):
        task_title = st.text_input("Task")
        task_ward = st.selectbox("Ward", all_wards, index=0)
        task_shift = st.selectbox("Shift", SHIFTS, index=0)
        task_priority = st.selectbox("Priority", PRIORITY_LEVELS, index=1)
        task_date = st.date_input("Task date", value=today, key="task_date")
        task_due_time = st.time_input("Due time", value=time(9, 0))
        task_assigned = st.text_input("Assigned to", value="RN Team")
        task_notes = st.text_area("Notes", height=60)
        submitted_task = st.form_submit_button("Add task")
        if submitted_task:
            if not task_title.strip():
                st.error("Task description is required.")
            else:
                st.session_state.tasks.append(
                    {
                        "id": next_id("TSK", "task_counter"),
                        "title": task_title.strip(),
                        "ward": task_ward,
                        "shift": task_shift,
                        "priority": task_priority,
                        "task_date": task_date,
                        "due_time": task_due_time,
                        "assigned_to": task_assigned.strip(),
                        "notes": task_notes.strip(),
                        "completed": False,
                    }
                )
                st.success("Daily task added.")


trainings_in_year = [
    training
    for training in st.session_state.trainings
    if training_in_year(training, selected_year)
    and training["priority"] in training_priority_filter
]

upcoming_trainings = [
    training
    for training in trainings_in_year
    if derive_training_status(training, today) == "Upcoming"
]
ongoing_trainings = [
    training
    for training in trainings_in_year
    if derive_training_status(training, today) == "Ongoing"
]
completed_trainings = [
    training
    for training in trainings_in_year
    if derive_training_status(training, today) == "Completed"
]

alarm_trainings = []
for training in upcoming_trainings:
    days_until = (training["start_date"] - today).days
    if 0 <= days_until <= alarm_window:
        alarm_trainings.append((training, days_until))

st.header("Alarm Center")
if alarm_trainings:
    for training, days_until in sorted(alarm_trainings, key=lambda item: item[1]):
        day_label = "today" if days_until == 0 else f"in {days_until} day(s)"
        st.warning(
            f"{training['title']} starts {day_label}. "
            f"Priority: {training['priority']}."
        )
else:
    st.success(
        f"No upcoming trainings within the next {alarm_window} days for {selected_year}."
    )

tab_trainings, tab_tasks, tab_reports = st.tabs(
    ["Training Calendar", "Daily Nursing Tasks", "Reports and Uploads"]
)

with tab_trainings:
    st.subheader(f"Training Calendar - {selected_year}")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Upcoming", len(upcoming_trainings))
    metric_cols[1].metric("Ongoing", len(ongoing_trainings))
    metric_cols[2].metric("Completed", len(completed_trainings))

    status_tabs = st.tabs(["Upcoming", "Ongoing", "Completed", "All"])
    with status_tabs[0]:
        render_training_list(upcoming_trainings, today, "upcoming")
    with status_tabs[1]:
        render_training_list(ongoing_trainings, today, "ongoing")
    with status_tabs[2]:
        render_training_list(completed_trainings, today, "completed")
    with status_tabs[3]:
        render_training_list(trainings_in_year, today, "all")

with tab_tasks:
    st.subheader(f"Daily Nursing Tasks - {task_date_filter.strftime('%b %d, %Y')}")
    tasks_for_day = [
        task
        for task in st.session_state.tasks
        if task["task_date"] == task_date_filter
        and task["priority"] in task_priority_filter
        and task["ward"] in ward_filter
    ]
    tasks_for_day = sorted(
        tasks_for_day,
        key=lambda task: (task["ward"], task["shift"], task["due_time"]),
    )

    total_tasks = len(tasks_for_day)
    completed_tasks = sum(task["completed"] for task in tasks_for_day)
    high_priority = sum(task["priority"] == "High" for task in tasks_for_day)
    task_metrics = st.columns(3)
    task_metrics[0].metric("Total tasks", total_tasks)
    task_metrics[1].metric("Completed", completed_tasks)
    task_metrics[2].metric("High priority", high_priority)

    render_task_list(tasks_for_day)

with tab_reports:
    st.subheader("Upload reports or task attachments")
    st.caption(
        "Placeholder uploads are stored in memory for this session only."
    )
    uploaded_files = st.file_uploader(
        "Upload files",
        type=["pdf", "docx", "xlsx", "png", "jpg"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        existing_keys = {
            (item["name"], item["size_kb"]) for item in st.session_state.uploads
        }
        for uploaded in uploaded_files:
            file_key = (uploaded.name, round(uploaded.size / 1024, 1))
            if file_key in existing_keys:
                continue
            st.session_state.uploads.append(
                {
                    "name": uploaded.name,
                    "size_kb": round(uploaded.size / 1024, 1),
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "status": "Pending review",
                }
            )
        st.success("Upload placeholders added.")

    if st.session_state.uploads:
        st.markdown("### Uploaded items")
        st.dataframe(st.session_state.uploads, use_container_width=True)
    else:
        st.info("No report uploads yet.")

