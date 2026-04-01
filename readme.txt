<<<<<<< HEAD
1 Setup (Windows)

//create virtual env
python -m venv .venv

//Activate (Windows CMD)
.venv\Scripts\activate

//Activate (Windows PowerShell)
.venv\Scripts\Activate
=======
1 Setup

//create virtual env
python -m venv env

python -m venv .venv

//Activate 
source ./env/bin/activate
>>>>>>> 8300d09d370d5943178b7404524fb487ab6ec52c

//ensure latest version
python -m pip install --upgrade pip

//dependency installation
pip install -r requirements.txt


2 Command to runserver 
//Activate created venv and run app
<<<<<<< HEAD
.venv\Scripts\activate
uvicorn app.main:app --reload

uvicorn app.main:app --reload --host 10.91.0.213 --port 8001

D:\lms-backend\
cd edu.erp\Coding\backend

for POST/api/v1/topic/import_topic
Import Topic
{
  "topic_code": "T001",
  "topic_title": "Introduction",
  "topic_content": "Basic concepts",
  "academic_batch_id": 1,
  "semester_id": 1,
  "course_id": 1,
  "created_by": 1
}

for PUT /api/v1/topic/update_topic/{topic_id}
Update Topic
topic id=14
{
  "topic_code": "T002",
  "topic_title": "Introduction Updated",
  "topic_content": "Updated content",
  "academic_batch_id": 1,
  "semester_id": 1,
  "course_id": 1,
  "created_by": 1
}

#2nd task edit topic values used to check
PUT
/api/v1/topic/edit_topic_schedule
Edit Topic Schedule
Request body
{
  "inst_map_id": 3,
  "conduction_date": "2026-03-07",
  "actual_delivery_date": "2026-03-07",
  "marks_expt": 1,
  "modified_by": 1
}

POST/api/v1/topic/add_extra_topic
Add Extra Topic

{
  "topic_id": 17,
  "academic_batch_id": 1,
  "semester_id": 1,
  "course_id": 1,
  "section_id": 1,
  "instructor_id": 1,
  "topic_hrs": "1",
  "num_of_sessions": 1,
  "created_by": 1
}

=======
source ./env/bin/activate
uvicorn app.main:app --reload

uvicorn app.main:app --reload --host 10.91.0.213 --port 8001
>>>>>>> 8300d09d370d5943178b7404524fb487ab6ec52c
