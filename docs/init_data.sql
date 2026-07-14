-- =====================================================================
-- 초기 샘플 데이터
-- Ansible template: roles/db/templates/init_data.sql.j2
-- =====================================================================

INSERT INTO doctors (doctor_id, name, department, specialty) VALUES
(1, '김내과', '내과', '소화기'),
(2, '이외과', '외과', '일반외과'),
(3, '박정형', '정형외과', '척추'),
(4, '최피부', '피부과', '아토피');

INSERT INTO patients (patient_id, name, birth_date) VALUES
(1, '홍길동', '1990-01-01'),
(2, '김철수', '1985-03-15'),
(3, '이영희', '1995-07-22');

INSERT INTO appointments (appointment_id, patient_id, doctor_id, appt_date, appt_time, status) VALUES
(1, 1, 1, '2026-07-01', '09:00:00', '예약완료'),
(2, 2, 3, '2026-07-01', '10:00:00', '예약완료'),
(3, 3, 4, '2026-07-02', '14:00:00', '진료완료');

INSERT INTO records (record_id, patient_id, doctor_id, visit_date, symptoms, diagnosis) VALUES
(1, 3, 4, '2026-06-10', '피부 가려움, 발진', '접촉성 피부염');

INSERT INTO prescriptions (prescription_id, record_id, drug_name, dosage, usage_instruction, duration) VALUES
(1, 1, '세티리진정', '10mg', '1일 1회 취침 전', '7일'),
(2, 1, '덱사메타손크림', '외용', '1일 2회 환부 도포', '7일');
