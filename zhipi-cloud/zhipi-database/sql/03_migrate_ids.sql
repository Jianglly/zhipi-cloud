-- =====================================================
-- 智批云 (ZhiPi Cloud) - 数据库迁移脚本
-- 将已有旧数据迁移到新的编号规则
-- 适用场景：已运行过旧版 01_create_tables.sql + 02_seed_data.sql，需要保留历史数据
-- 用法：在 MySQL 中执行：source 03_migrate_ids.sql
-- 注意：迁移前请先备份数据库！
-- =====================================================

USE zhipi_cloud;

SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1) 添加 class.class_code 字段（MySQL 不支持 ADD COLUMN IF NOT EXISTS）
-- =====================================================

-- 使用存储过程安全添加列
DROP PROCEDURE IF EXISTS _add_column_if_not_exists;
DELIMITER //
CREATE PROCEDURE _add_column_if_not_exists(
    IN p_table VARCHAR(64),
    IN p_column VARCHAR(64),
    IN p_definition VARCHAR(500)
)
BEGIN
    DECLARE col_exists INT DEFAULT 0;
    SELECT COUNT(*) INTO col_exists
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = p_table
      AND COLUMN_NAME = p_column;
    IF col_exists = 0 THEN
        SET @sql = CONCAT('ALTER TABLE ', p_table, ' ADD COLUMN ', p_column, ' ', p_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END //
DELIMITER ;

-- 添加 class_code 列
CALL _add_column_if_not_exists('class', 'class_code', 'INT NULL COMMENT "班级内编号 1-9"');

-- 添加 old_teacher_id 备份列
CALL _add_column_if_not_exists('teacher', 'old_teacher_id', 'VARCHAR(15) NULL COMMENT "迁移前旧编号"');

-- 添加 old_student_id 备份列
CALL _add_column_if_not_exists('student', 'old_student_id', 'VARCHAR(15) NULL COMMENT "迁移前旧编号"');

-- =====================================================
-- 2) 根据现有班级名称生成 class_code
--    假设 class_name 最后出现的数字就是班号：高三年级1班 -> 1
-- =====================================================
UPDATE class
SET class_code = CAST(REGEXP_SUBSTR(class_name, '[0-9]+') AS UNSIGNED)
WHERE class_code IS NULL;

-- 添加唯一索引
DROP INDEX IF EXISTS idx_class_code ON class;
CREATE UNIQUE INDEX idx_class_code ON class(class_code);

-- =====================================================
-- 3) 创建 teacher_class 表
-- =====================================================
CREATE TABLE IF NOT EXISTS teacher_class (
    teacher_id  VARCHAR(15)  NOT NULL,
    class_id    VARCHAR(20)  NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (teacher_id, class_id),
    KEY idx_class (class_id),
    CONSTRAINT fk_tc_teacher FOREIGN KEY (teacher_id) REFERENCES teacher (teacher_id) ON DELETE CASCADE,
    CONSTRAINT fk_tc_class   FOREIGN KEY (class_id)   REFERENCES class   (class_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 4) 将现有 teacher.class_id 迁移到 teacher_class
-- =====================================================
INSERT IGNORE INTO teacher_class (teacher_id, class_id)
SELECT teacher_id, class_id FROM teacher WHERE class_id IS NOT NULL;

-- =====================================================
-- 5) 把教师 subject 规范为 语文/数学/英语
--    外语 -> 英语，其他非三科科目需要人工确认
-- =====================================================
UPDATE teacher SET subject = '英语' WHERE subject = '外语';
UPDATE teacher SET subject = '语文' WHERE subject NOT IN ('语文', '数学', '英语') AND subject REGEXP '语|文';
UPDATE teacher SET subject = '数学' WHERE subject NOT IN ('语文', '数学', '英语') AND subject REGEXP '数|学';
-- 剩余未匹配的科目默认设为语文，请人工核查
UPDATE teacher SET subject = '语文' WHERE subject NOT IN ('语文', '数学', '英语');

-- =====================================================
-- 6) 教师编号迁移：T + 科目码(1位) + 序号(2位)
--    语文=1, 数学=2, 英语=3
-- =====================================================

-- 备份旧编号
UPDATE teacher SET old_teacher_id = teacher_id WHERE old_teacher_id IS NULL;

-- 创建临时映射表（需要 MySQL 8.0+ 支持 ROW_NUMBER）
DROP TABLE IF EXISTS _teacher_id_map;
CREATE TEMPORARY TABLE _teacher_id_map AS
SELECT
    teacher_id AS old_id,
    CONCAT('T',
        CASE subject
            WHEN '语文' THEN '1'
            WHEN '数学' THEN '2'
            WHEN '英语' THEN '3'
            ELSE '1'
        END,
        LPAD(ROW_NUMBER() OVER (PARTITION BY subject ORDER BY old_teacher_id), 2, '0')
    ) AS new_id
FROM teacher;

-- 更新 teacher 表
UPDATE teacher t
JOIN _teacher_id_map m ON t.old_teacher_id = m.old_id
SET t.teacher_id = m.new_id;

-- 更新 teacher_class 表
UPDATE teacher_class tc
JOIN _teacher_id_map m ON tc.teacher_id = m.old_id
SET tc.teacher_id = m.new_id;

-- 更新 paper 表
UPDATE paper p
JOIN _teacher_id_map m ON p.teacher_id = m.old_id
SET p.teacher_id = m.new_id;

-- =====================================================
-- 7) 学生编号迁移：S + 班级码(1位) + 序号(2位)
-- =====================================================

-- 备份旧编号
UPDATE student SET old_student_id = student_id WHERE old_student_id IS NULL;

DROP TABLE IF EXISTS _student_id_map;
CREATE TEMPORARY TABLE _student_id_map AS
SELECT
    s.student_id AS old_id,
    CONCAT('S', c.class_code, LPAD(ROW_NUMBER() OVER (PARTITION BY s.class_id ORDER BY s.old_student_id), 2, '0')) AS new_id
FROM student s
JOIN class c ON s.class_id = c.class_id;

UPDATE student s
JOIN _student_id_map m ON s.old_student_id = m.old_id
SET s.student_id = m.new_id;

UPDATE score sc
JOIN _student_id_map m ON sc.student_id = m.old_id
SET sc.student_id = m.new_id;

-- =====================================================
-- 8) 规范试卷和成绩科目
-- =====================================================
UPDATE paper SET subject = '英语' WHERE subject = '外语';
UPDATE score SET subject = '英语' WHERE subject = '外语';
UPDATE paper SET subject = '语文' WHERE subject NOT IN ('语文', '数学', '英语');
UPDATE score SET subject = '语文' WHERE subject NOT IN ('语文', '数学', '英语');

-- =====================================================
-- 9) 更新班级编号为 入学年份后两位 + 班级号 格式（如 2501）
--    若已执行新的 02_seed_data.sql，则无需此步骤
-- =====================================================
-- UPDATE class SET class_id = CONCAT(SUBSTRING(grade, 3, 2), LPAD(class_code, 2, '0')) WHERE class_id REGEXP '[^0-9]';

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- 10) 清理临时表和存储过程
-- =====================================================
DROP TABLE IF EXISTS _teacher_id_map;
DROP TABLE IF EXISTS _student_id_map;
DROP PROCEDURE IF EXISTS _add_column_if_not_exists;

-- =====================================================
-- 迁移完成！验证数据：
-- SELECT teacher_id, name, subject FROM teacher;
-- SELECT student_id, name, class_id FROM student LIMIT 10;
-- SELECT * FROM teacher_class;
-- =====================================================
