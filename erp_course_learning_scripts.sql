ALTER TABLE iems_academic_batch
  ADD COLUMN start_year YEAR(4) NOT NULL,
  ADD COLUMN end_year YEAR(4) NOT NULL,
  ADD COLUMN total_terms INT(3) NOT NULL,
  ADD COLUMN academic_batch_owner MEDIUMINT(8) UNSIGNED NOT NULL,
  ADD COLUMN cia_passing_marks FLOAT(8,2) UNSIGNED DEFAULT '0.00',
  ADD COLUMN tee_passing_marks FLOAT(8,2) UNSIGNED DEFAULT '0.00',
  ADD COLUMN academic_batch_release_status TINYINT(3) NOT NULL DEFAULT '0',
  ADD COLUMN first_year_flag TINYINT(1) NOT NULL DEFAULT '0',
  ADD COLUMN po_matrix_flag MEDIUMINT(8) DEFAULT NULL,
  ADD COLUMN oe_pi_flag TINYINT(4) NOT NULL DEFAULT '1',
  ADD COLUMN clo_bl_flag TINYINT(1) UNSIGNED NOT NULL DEFAULT '0',
  ADD COLUMN edu_sys_flag TINYINT(1) UNSIGNED DEFAULT '0',
  ADD COLUMN avg_po_attnt_flag TINYINT(4) NOT NULL DEFAULT '0',
  ADD COLUMN import_ref_crclm_id MEDIUMINT(8) UNSIGNED DEFAULT NULL,
  ADD COLUMN import_type TINYINT(2) UNSIGNED DEFAULT NULL;

ALTER TABLE iems_semester
  ADD COLUMN term_name VARCHAR(50) NOT NULL,
  ADD COLUMN academic_start_year YEAR(4) DEFAULT NULL,
  ADD COLUMN academic_end_year YEAR(4) DEFAULT NULL,
  ADD COLUMN semester_duration INT(5) NOT NULL,
  ADD COLUMN total_theory_courses MEDIUMINT(8) NOT NULL,
  ADD COLUMN total_practical_courses MEDIUMINT(8) NOT NULL,
  ADD COLUMN total_crs_enroll DECIMAL(3,1) DEFAULT NULL,
  ADD COLUMN enroll_start_date DATETIME DEFAULT NULL,
  ADD COLUMN enroll_start_time TIME NOT NULL,
  ADD COLUMN enroll_end_date DATE NOT NULL,
  ADD COLUMN enroll_end_time TIME NOT NULL,
  ADD COLUMN unit_id MEDIUMINT(8) UNSIGNED NOT NULL DEFAULT '3',
  ADD COLUMN publish_flag TINYINT(4) DEFAULT '0',
  ADD COLUMN own_crclm_elective TINYINT(2) DEFAULT NULL COMMENT 'Allow only 0 to 9',
  ADD COLUMN other_crclm_elective TINYINT(2) DEFAULT NULL COMMENT 'Allow only 0 to 9';
ALTER TABLE iems_semester
  ADD CONSTRAINT academic_batch_semester_ibfk_2
  FOREIGN KEY (unit_id)
  REFERENCES unit (unit_id)
  ON DELETE CASCADE
  ON UPDATE CASCADE;

update iems_users set password='178dd7891832bf647b42179c0a61c13352ca0ed4', salt='1fe1ba8305b60772d489710ec3d798c0' where username='coe';

update iems_users set username='admin' where username='coe';