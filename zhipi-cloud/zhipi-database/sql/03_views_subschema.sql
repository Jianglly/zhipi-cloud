-- =====================================================
-- 智批云 (ZhiPi Cloud) - 数据库视图设计（子模式）
-- 对应文档：子模式设计 - 学生子模式、教师子模式、管理子模式
-- =====================================================

USE zhipi_cloud;

-- =====================================================
-- 学生子模式：学生只能看自己相关的数据
-- =====================================================

-- 视图1：学生个人成绩视图（只能看自己）
-- 应用层通过WHERE student_id = :current_user_id 过滤
CREATE OR REPLACE VIEW v_student_score AS
SELECT
    s.score_id,
    s.student_id,
    s.name,
    s.subject,
    s.class_id,
    s.score,
    s.rank_in_class,
    s.rank_in_all,
    s.exam_date,
    s.ai_score,
    s.manual_score,
    s.status,
    p.title AS paper_title,
    p.total_score
FROM score s
JOIN paper p ON s.paper_id = p.paper_id
WHERE s.status = 3;  -- 只显示已完成批阅的成绩

-- 视图2：学生成绩趋势视图
CREATE OR REPLACE VIEW v_student_score_trend AS
SELECT
    s.student_id,
    s.name,
    s.subject,
    s.score,
    s.rank_in_class,
    s.exam_date,
    p.total_score,
    ROUND(s.score / p.total_score * 100, 1) AS score_percent
FROM score s
JOIN paper p ON s.paper_id = p.paper_id
WHERE s.status = 3
ORDER BY s.student_id, s.exam_date;

-- =====================================================
-- 教师子模式：教师可查看本班学生信息和成绩
-- =====================================================

-- 视图3：班级成绩概览（教师用）
CREATE OR REPLACE VIEW v_class_score_overview AS
SELECT
    s.class_id,
    s.subject,
    s.exam_date,
    p.title AS paper_title,
    COUNT(s.score_id)                       AS student_count,
    ROUND(AVG(s.score), 2)                  AS avg_score,
    MAX(s.score)                            AS max_score,
    MIN(s.score)                            AS min_score,
    ROUND(STDDEV(s.score), 2)               AS std_dev,
    SUM(CASE WHEN s.score >= 90 THEN 1 ELSE 0 END) AS excellent_count,
    SUM(CASE WHEN s.score >= 75 AND s.score < 90 THEN 1 ELSE 0 END) AS good_count,
    SUM(CASE WHEN s.score >= 60 AND s.score < 75 THEN 1 ELSE 0 END) AS pass_count,
    SUM(CASE WHEN s.score < 60 THEN 1 ELSE 0 END) AS fail_count
FROM score s
JOIN paper p ON s.paper_id = p.paper_id
WHERE s.status = 3
GROUP BY s.class_id, s.subject, s.exam_date, p.title;

-- 视图4：班级学生成绩排名（教师用）
CREATE OR REPLACE VIEW v_class_ranking AS
SELECT
    s.class_id,
    s.student_id,
    s.name,
    s.subject,
    s.score,
    s.rank_in_class,
    s.exam_date,
    p.total_score,
    ROUND(s.score / p.total_score * 100, 1) AS score_percent,
    CASE
        WHEN s.score >= p.total_score * 0.9 THEN '优秀'
        WHEN s.score >= p.total_score * 0.75 THEN '良好'
        WHEN s.score >= p.total_score * 0.6 THEN '及格'
        ELSE '不及格'
    END AS grade_level
FROM score s
JOIN paper p ON s.paper_id = p.paper_id
ORDER BY s.class_id, s.exam_date, s.rank_in_class;

-- 视图5：待批阅试卷列表（教师用）
CREATE OR REPLACE VIEW v_pending_marking AS
SELECT
    s.score_id,
    s.student_id,
    s.name,
    s.class_id,
    s.subject,
    p.title AS paper_title,
    s.exam_date,
    s.status,
    s.ai_score,
    s.answer_image,
    CASE s.status
        WHEN 0 THEN '待批阅'
        WHEN 1 THEN 'AI批阅中'
        WHEN 2 THEN '待人工审核'
        WHEN 3 THEN '已完成'
    END AS status_text
FROM score s
JOIN paper p ON s.paper_id = p.paper_id
WHERE s.status IN (0, 1, 2);

-- =====================================================
-- 管理视图：系统统计
-- =====================================================

-- 视图6：系统运行总览
CREATE OR REPLACE VIEW v_system_stats AS
SELECT
    (SELECT COUNT(*) FROM student)    AS total_students,
    (SELECT COUNT(*) FROM teacher)    AS total_teachers,
    (SELECT COUNT(*) FROM paper)      AS total_papers,
    (SELECT COUNT(*) FROM score)      AS total_scores,
    (SELECT COUNT(*) FROM score WHERE status = 3) AS completed_scores,
    (SELECT COUNT(*) FROM score WHERE status IN (0,1,2)) AS pending_scores;
