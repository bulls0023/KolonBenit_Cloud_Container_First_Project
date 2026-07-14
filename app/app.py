import os
from datetime import date

import pymysql
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "10.10.1.10"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "hospital_app"),
    "password": os.environ.get("MYSQL_PASSWORD", "ChangeMe_App_2026!"),
    "database": os.environ.get("MYSQL_DATABASE", "hospital"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

ALL_SLOTS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
]


def get_conn():
    return pymysql.connect(**DB_CONFIG)


# ---------------------------------------------------------------------
# 페이지 라우트 (템플릿 렌더링)
# ---------------------------------------------------------------------
@app.route("/")
def page_index():
    return render_template("index.html")


@app.route("/reserve/step1")
def page_step1():
    return render_template("reserve-step1.html")


@app.route("/reserve/step2")
def page_step2():
    return render_template("reserve-step2.html")


@app.route("/reserve/step3")
def page_step3():
    return render_template("reserve-step3.html")


@app.route("/reserve/step4")
def page_step4():
    return render_template("reserve-step4.html")


@app.route("/reserve/step5")
def page_step5():
    return render_template("reserve-step5.html")


@app.route("/reserve/lookup")
def page_lookup():
    return render_template("reserve-lookup.html")


@app.route("/records")
def page_records():
    return render_template("records.html")


@app.route("/prescription")
def page_prescription():
    return render_template("prescription.html")


@app.route("/health")
def health():
    # DB 연결까지 확인하는 헬스체크 (K8s readiness/liveness probe용)
    try:
        conn = get_conn()
        conn.close()
        return jsonify(status="ok", db="ok")
    except Exception as e:
        return jsonify(status="ok", db="error", detail=str(e)), 200


# ---------------------------------------------------------------------
# API 라우트
# ---------------------------------------------------------------------
@app.route("/api/patients")
def api_patients_lookup():
    """이름으로 등록 환자 조회 (예약 1단계에서 사용)"""
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify(found=False)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT patient_id, name, birth_date FROM patients WHERE name=%s",
                (name,),
            )
            row = cur.fetchone()
        if row:
            row["birth_date"] = str(row["birth_date"])
        return jsonify(found=bool(row), patient=row)
    finally:
        conn.close()


@app.route("/api/patients", methods=["POST"])
def api_patients_create():
    """신규 환자 등록 (이름 + 생년월일)"""
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    birth_date = data.get("birth_date")
    if not name or not birth_date:
        return jsonify(error="name and birth_date required"), 400

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO patients (name, birth_date) VALUES (%s, %s)",
                (name, birth_date),
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT LAST_INSERT_ID() AS id")
            new_id = cur.fetchone()["id"]
        return jsonify(patient_id=new_id, name=name), 201
    finally:
        conn.close()


@app.route("/api/doctors")
def api_doctors():
    """진료과별 의사 목록 조회"""
    dept = request.args.get("dept", "").strip()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if dept:
                cur.execute(
                    "SELECT doctor_id, name, department, specialty FROM doctors WHERE department=%s",
                    (dept,),
                )
            else:
                cur.execute(
                    "SELECT doctor_id, name, department, specialty FROM doctors"
                )
            rows = cur.fetchall()
        return jsonify(rows)
    finally:
        conn.close()


@app.route("/api/slots")
def api_slots():
    """특정 의사/날짜의 예약 가능 시간 슬롯 조회"""
    doctor_id = request.args.get("doctor_id")
    slot_date = request.args.get("date")
    if not doctor_id or not slot_date:
        return jsonify(error="doctor_id and date required"), 400

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT appt_time FROM appointments "
                "WHERE doctor_id=%s AND appt_date=%s AND status != '취소'",
                (doctor_id, slot_date),
            )
            booked = [str(r["appt_time"])[:5] for r in cur.fetchall()]
        return jsonify(all=ALL_SLOTS, booked=booked)
    finally:
        conn.close()


@app.route("/api/appointments", methods=["GET", "POST"])
def api_appointments():
    conn = get_conn()
    try:
        if request.method == "POST":
            data = request.get_json(force=True)
            required = ["patient_id", "doctor_id", "date", "time"]
            if not all(data.get(k) for k in required):
                return jsonify(error="patient_id, doctor_id, date, time required"), 400

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO appointments "
                    "(patient_id, doctor_id, appt_date, appt_time, status) "
                    "VALUES (%s, %s, %s, %s, '예약완료')",
                    (data["patient_id"], data["doctor_id"], data["date"], data["time"]),
                )
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("SELECT LAST_INSERT_ID() AS id")
                new_id = cur.fetchone()["id"]
            return (
                jsonify(appointment_id=new_id, code=f"R-{new_id:06d}"),
                201,
            )

        # GET: 환자명으로 예약 목록 조회
        patient_name = request.args.get("patient_name", "").strip()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.appointment_id AS id, a.appt_date AS date,
                       a.appt_time AS time, a.status,
                       d.name AS doctor, d.department AS dept
                FROM appointments a
                JOIN patients p ON a.patient_id = p.patient_id
                JOIN doctors d ON a.doctor_id = d.doctor_id
                WHERE p.name = %s
                ORDER BY a.appt_date DESC, a.appt_time DESC
                """,
                (patient_name,),
            )
            rows = cur.fetchall()
        for r in rows:
            r["date"] = str(r["date"])
            r["time"] = str(r["time"])[:5]
        return jsonify(rows)
    finally:
        conn.close()


@app.route("/api/appointments/<int:appt_id>", methods=["PATCH"])
def api_appointment_update(appt_id):
    """예약 취소 (상태 변경)"""
    data = request.get_json(force=True)
    status = data.get("status", "취소")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE appointments SET status=%s WHERE appointment_id=%s",
                (status, appt_id),
            )
        conn.commit()
        return jsonify(ok=True, appointment_id=appt_id, status=status)
    finally:
        conn.close()


@app.route("/api/records")
def api_records():
    """환자명으로 진료기록 조회"""
    patient_name = request.args.get("patient_name", "").strip()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.record_id AS id, r.visit_date AS date,
                       r.symptoms, r.diagnosis,
                       d.name AS doctor, d.department AS dept
                FROM records r
                JOIN patients p ON r.patient_id = p.patient_id
                JOIN doctors d ON r.doctor_id = d.doctor_id
                WHERE p.name = %s
                ORDER BY r.visit_date DESC
                """,
                (patient_name,),
            )
            rows = cur.fetchall()
        for r in rows:
            r["date"] = str(r["date"])
        return jsonify(rows)
    finally:
        conn.close()


@app.route("/api/prescriptions")
def api_prescriptions():
    """진료기록 ID 또는 환자명으로 처방전 조회"""
    record_id = request.args.get("record_id")
    patient_name = request.args.get("patient_name", "").strip()

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if record_id:
                cur.execute(
                    """
                    SELECT pr.drug_name AS name, pr.dosage,
                           pr.usage_instruction AS `usage`, pr.duration,
                           r.visit_date AS date, d.name AS doctor,
                           d.department AS dept, r.diagnosis
                    FROM prescriptions pr
                    JOIN records r ON pr.record_id = r.record_id
                    JOIN doctors d ON r.doctor_id = d.doctor_id
                    WHERE pr.record_id = %s
                    """,
                    (record_id,),
                )
            elif patient_name:
                cur.execute(
                    """
                    SELECT pr.drug_name AS name, pr.dosage,
                           pr.usage_instruction AS `usage`, pr.duration,
                           r.visit_date AS date, d.name AS doctor,
                           d.department AS dept, r.diagnosis
                    FROM prescriptions pr
                    JOIN records r ON pr.record_id = r.record_id
                    JOIN doctors d ON r.doctor_id = d.doctor_id
                    JOIN patients p ON r.patient_id = p.patient_id
                    WHERE p.name = %s
                    ORDER BY r.visit_date DESC
                    """,
                    (patient_name,),
                )
            else:
                return jsonify(found=False), 400
            rows = cur.fetchall()

        if not rows:
            return jsonify(found=False)

        record_info = {
            "date": str(rows[0]["date"]),
            "doctor": rows[0]["doctor"],
            "dept": rows[0]["dept"],
            "diagnosis": rows[0]["diagnosis"],
        }
        drugs = [
            {
                "name": r["name"],
                "dosage": r["dosage"],
                "usage": r["usage"],
                "duration": r["duration"],
            }
            for r in rows
        ]
        return jsonify(found=True, record=record_info, drugs=drugs)
    finally:
        conn.close()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
