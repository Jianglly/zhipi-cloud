-- =====================================================
-- 智批云 (ZhiPi Cloud) - 种子数据 (测试数据)
-- 账号来源：auto_test_guide.py 参考数据
-- 所有密码：123456 (bcrypt 加密)
-- =====================================================
-- 注意：此文件使用 INSERT IGNORE，已存在的数据不会被覆盖
-- 系统启动时会自动执行此文件，但不会清空已有数据
-- =====================================================

USE zhipi_cloud;

-- =====================================================
-- 班级数据（高中 3+1+2 模式）
-- INSERT IGNORE：如果已存在则跳过，不破坏数据
-- =====================================================
INSERT IGNORE INTO class (class_id, class_name, grade, department) VALUES
('高三一班',   '高三年级1班', '2025', '高中部'),
('高三二班',   '高三年级2班', '2025', '高中部'),
('高三三班',   '高三年级3班', '2025', '高中部'),
('高三四班',   '高三年级4班', '2025', '高中部'),
('高三五班',   '高三年级5班', '2025', '高中部');

-- =====================================================
-- 教师数据（高中教师，5位）
-- 密码：123456 的 bcrypt 哈希
-- =====================================================
INSERT IGNORE INTO teacher (teacher_id, name, class_id, subject, password, task, phone) VALUES
('T007', '李文华', '高三一班', '语文',     '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000007'),
('T008', '张建国', '高三二班', '数学',     '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000008'),
('T009', '陈晓燕', '高三三班', '外语',     '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000009'),
('T010', '王志强', '高三四班', '物理',     '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000010'),
('T011', '赵丽敏', '高三五班', '历史',     '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000011');

-- =====================================================
-- 学生数据（高中，30人，每班6人）
-- 密码：123456 的 bcrypt 哈希
-- =====================================================
INSERT IGNORE INTO student (student_id, name, class_id, password, phone) VALUES
-- 高三一班（6人）
('S032', '林浩然', '高三一班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000032'),
('S033', '陈雨晴', '高三一班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000033'),
('S034', '王子轩', '高三一班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000034'),
('S035', '张思琪', '高三一班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000035'),
('S036', '刘子墨', '高三一班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000036'),
('S037', '周雅婷', '高三一班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000037'),
-- 高三二班（6人）
('S038', '吴俊杰', '高三二班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000038'),
('S039', '郑欣怡', '高三二班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000039'),
('S040', '孙浩宇', '高三二班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000040'),
('S041', '黄诗涵', '高三二班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000041'),
('S042', '徐晨曦', '高三二班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000042'),
('S043', '杨子萱', '高三二班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000043'),
-- 高三三班（6人）
('S044', '马天翔', '高三三班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000044'),
('S045', '罗婉清', '高三三班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000045'),
('S046', '谢明辉', '高三三班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000046'),
('S047', '唐佳怡', '高三三班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000047'),
('S048', '许文博', '高三三班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000048'),
('S049', '韩梦瑶', '高三三班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000049'),
-- 高三四班（6人）
('S050', '冯子豪', '高三四班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000050'),
('S051', '董思远', '高三四班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000051'),
('S052', '程雨萱', '高三四班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000052'),
('S053', '曹铭泽', '高三四班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000053'),
('S054', '袁紫月', '高三四班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000054'),
('S055', '邓皓阳', '高三四班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000055'),
-- 高三五班（6人）
('S056', '蒋文轩', '高三五班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000056'),
('S057', '蔡静雯', '高三五班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000057'),
('S058', '潘志强', '高三五班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000058'),
('S059', '范雨桐', '高三五班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000059'),
('S060', '石浩然', '高三五班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000060'),
('S061', '钟灵秀', '高三五班', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000061');

-- =====================================================
-- 试卷数据（仅在无试卷时插入初始演示数据）
-- =====================================================
INSERT IGNORE INTO paper (paper_id, title, subject, class_id, teacher_id, total_score, exam_date, status, answer_key) VALUES
(1, '汇编语言小测', '汇编语言', '高三一班', 'T007', 100.00, '2025-06-27', 1,
 '{"q1":"A","q2":"D","q3":"D","q4":"C","q5":"A","q6":"C","q7":"B","q8":"A","q9":"B","q10":"C","q11":"D","q12":"A","q13":"B","q14":"D","q15":"D","q16":"C","q17":"C","q18":"D"}');

-- =====================================================
-- 成绩数据（6条，仅在无成绩时插入）
-- =====================================================
INSERT IGNORE INTO score (score_id, student_id, paper_id, subject, class_id, name, score, rank_in_class, rank_in_all, exam_date, ai_score, manual_score, status) VALUES
(1, 'S032', 1, '汇编语言', '高三一班', '林浩然', 0.00, NULL, NULL, '2025-06-27', NULL, NULL, 0),
(2, 'S033', 1, '汇编语言', '高三一班', '陈雨晴', 0.00, NULL, NULL, '2025-06-27', NULL, NULL, 0),
(3, 'S034', 1, '汇编语言', '高三一班', '王子轩', 0.00, NULL, NULL, '2025-06-27', NULL, NULL, 0),
(4, 'S035', 1, '汇编语言', '高三一班', '张思琪', 0.00, NULL, NULL, '2025-06-27', NULL, NULL, 0),
(5, 'S036', 1, '汇编语言', '高三一班', '刘子墨', 0.00, NULL, NULL, '2025-06-27', NULL, NULL, 0),
(6, 'S037', 1, '汇编语言', '高三一班', '周雅婷', 0.00, NULL, NULL, '2025-06-27', NULL, NULL, 0);
