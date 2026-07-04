-- =====================================================
-- 智批云 (ZhiPi Cloud) - 种子数据 (新编号规则)
-- 科目：仅语文/数学/英语
-- 班级编号：入学年份后两位 + 班级两位，如 2501
-- 教师编号：T + 科目码(1位) + 入职序号(2位)
-- 学生编号：S + 班级码(1位) + 学号(2位)
-- 所有密码：123456 (bcrypt 加密)
-- =====================================================

USE zhipi_cloud;

-- =====================================================
-- 班级数据
-- =====================================================
INSERT IGNORE INTO class (class_id, class_code, class_name, grade, department) VALUES
('2501', 1, '高三年级1班', '2025', '高中部'),
('2502', 2, '高三年级2班', '2025', '高中部'),
('2503', 3, '高三年级3班', '2025', '高中部'),
('2504', 4, '高三年级4班', '2025', '高中部'),
('2505', 5, '高三年级5班', '2025', '高中部');

-- =====================================================
-- 教师数据（6位，语数英各2位，每位任教3个班）
-- 密码：123456 的 bcrypt 哈希
-- 编号规则：T + 科目码(1位) + 入职序号(2位)
-- =====================================================
INSERT IGNORE INTO teacher (teacher_id, name, class_id, subject, password, task, phone) VALUES
('T101', '李文华', '2501', '语文', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000101'),
('T102', '王芳',   '2504', '语文', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000102'),
('T201', '张建国', '2501', '数学', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000201'),
('T202', '刘强',   '2504', '数学', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000202'),
('T301', '陈晓燕', '2501', '英语', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000301'),
('T302', '赵丽',   '2504', '英语', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', 0, '13800000302');

-- 教师任教班级映射（每位教师任教3个班，确保5个班每个班都有语数英老师）
-- T101(语文): 2501, 2502, 2503     T102(语文): 2504, 2505, 2501
-- T201(数学): 2501, 2502, 2503     T202(数学): 2504, 2505, 2502
-- T301(英语): 2501, 2502, 2503     T302(英语): 2504, 2505, 2503
INSERT IGNORE INTO teacher_class (teacher_id, class_id) VALUES
('T101', '2501'), ('T101', '2502'), ('T101', '2503'),
('T102', '2504'), ('T102', '2505'), ('T102', '2501'),
('T201', '2501'), ('T201', '2502'), ('T201', '2503'),
('T202', '2504'), ('T202', '2505'), ('T202', '2502'),
('T301', '2501'), ('T301', '2502'), ('T301', '2503'),
('T302', '2504'), ('T302', '2505'), ('T302', '2503');

-- =====================================================
-- 学生数据（30人，每班6人）
-- 学号 = S + 班级码(1位) + 班内序号(2位)
-- =====================================================
INSERT IGNORE INTO student (student_id, name, class_id, password, phone) VALUES
-- 2501 班（6人）
('S101', '林浩然', '2501', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000101'),
('S102', '陈雨晴', '2501', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000102'),
('S103', '王子轩', '2501', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000103'),
('S104', '张思琪', '2501', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000104'),
('S105', '刘子墨', '2501', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000105'),
('S106', '周雅婷', '2501', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000106'),
-- 2502 班（6人）
('S201', '吴俊杰', '2502', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000201'),
('S202', '郑欣怡', '2502', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000202'),
('S203', '孙浩宇', '2502', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000203'),
('S204', '黄诗涵', '2502', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000204'),
('S205', '徐晨曦', '2502', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000205'),
('S206', '杨子萱', '2502', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000206'),
-- 2503 班（6人）
('S301', '马天翔', '2503', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000301'),
('S302', '罗婉清', '2503', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000302'),
('S303', '谢明辉', '2503', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000303'),
('S304', '唐佳怡', '2503', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000304'),
('S305', '许文博', '2503', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000305'),
('S306', '韩梦瑶', '2503', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000306'),
-- 2504 班（6人）
('S401', '冯子豪', '2504', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000401'),
('S402', '董思远', '2504', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000402'),
('S403', '程雨萱', '2504', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000403'),
('S404', '曹铭泽', '2504', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000404'),
('S405', '袁紫月', '2504', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000405'),
('S406', '邓皓阳', '2504', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000406'),
-- 2505 班（6人）
('S501', '蒋文轩', '2505', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000501'),
('S502', '蔡静雯', '2505', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000502'),
('S503', '潘志强', '2505', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000503'),
('S504', '范雨桐', '2505', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000504'),
('S505', '石浩然', '2505', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000505'),
('S506', '钟灵秀', '2505', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC', '13900000506');

-- =====================================================
-- 试卷数据（语数英各科，覆盖多个班级）
-- =====================================================
INSERT IGNORE INTO paper (paper_id, title, subject, class_id, teacher_id, total_score, exam_date, status, answer_key) VALUES
(1, '高三语文第一次月考', '语文', '2501', 'T101', 150.00, '2025-06-27', 1,
 '{"q1":"A","q2":"D","q3":"D","q4":"C","q5":"A","q6":"C","q7":"B","q8":"A","q9":"B","q10":"C","q11":"D","q12":"A","q13":"B","q14":"D","q15":"D","q16":"C","q17":"C","q18":"D"}'),
(2, '高三数学第一次月考', '数学', '2501', 'T201', 150.00, '2025-06-28', 1,
 '{"q1":"B","q2":"C","q3":"A","q4":"D","q5":"B","q6":"C","q7":"A","q8":"D","q9":"B","q10":"C","q11":"A","q12":"D","q13":"B","q14":"C","q15":"A","q16":"D","q17":"B","q18":"C"}'),
(3, '高三英语第一次月考', '英语', '2501', 'T301', 150.00, '2025-06-29', 1,
 '{"q1":"C","q2":"A","q3":"B","q4":"D","q5":"C","q6":"A","q7":"D","q8":"B","q9":"C","q10":"A","q11":"D","q12":"B","q13":"C","q14":"A","q15":"B","q16":"D","q17":"A","q18":"C"}'),
(4, '高三语文第一次月考', '语文', '2504', 'T102', 150.00, '2025-06-27', 1,
 '{"q1":"A","q2":"D","q3":"D","q4":"C","q5":"A","q6":"C","q7":"B","q8":"A","q9":"B","q10":"C","q11":"D","q12":"A","q13":"B","q14":"D","q15":"D","q16":"C","q17":"C","q18":"D"}');

-- =====================================================
-- 成绩数据
-- 语文(2501) paper_id=1 / 数学(2501) paper_id=2 / 英语(2501) paper_id=3 / 语文(2504) paper_id=4
-- =====================================================
INSERT IGNORE INTO score (score_id, student_id, paper_id, subject, class_id, name, score, rank_in_class, rank_in_all, exam_date, ai_score, manual_score, status) VALUES
-- 2501班 语文 (paper 1)
(1,  'S101', 1, '语文', '2501', '林浩然', 128.00, 1, NULL, '2025-06-27', 128.00, NULL, 1),
(2,  'S102', 1, '语文', '2501', '陈雨晴', 115.00, 2, NULL, '2025-06-27', 115.00, NULL, 1),
(3,  'S103', 1, '语文', '2501', '王子轩', 102.00, 3, NULL, '2025-06-27', 102.00, NULL, 1),
(4,  'S104', 1, '语文', '2501', '张思琪',  96.00, 4, NULL, '2025-06-27',  96.00, NULL, 1),
(5,  'S105', 1, '语文', '2501', '刘子墨',  87.00, 5, NULL, '2025-06-27',  87.00, NULL, 1),
(6,  'S106', 1, '语文', '2501', '周雅婷',  78.00, 6, NULL, '2025-06-27',  78.00, NULL, 1),
-- 2501班 数学 (paper 2)
(7,  'S101', 2, '数学', '2501', '林浩然', 135.00, 1, NULL, '2025-06-28', 135.00, NULL, 1),
(8,  'S102', 2, '数学', '2501', '陈雨晴', 122.00, 2, NULL, '2025-06-28', 122.00, NULL, 1),
(9,  'S103', 2, '数学', '2501', '王子轩', 108.00, 3, NULL, '2025-06-28', 108.00, NULL, 1),
(10, 'S104', 2, '数学', '2501', '张思琪',  95.00, 4, NULL, '2025-06-28',  95.00, NULL, 1),
(11, 'S105', 2, '数学', '2501', '刘子墨',  82.00, 5, NULL, '2025-06-28',  82.00, NULL, 1),
(12, 'S106', 2, '数学', '2501', '周雅婷',  71.00, 6, NULL, '2025-06-28',  71.00, NULL, 1),
-- 2501班 英语 (paper 3)
(13, 'S101', 3, '英语', '2501', '林浩然', 142.00, 1, NULL, '2025-06-29', 142.00, NULL, 1),
(14, 'S102', 3, '英语', '2501', '陈雨晴', 130.00, 2, NULL, '2025-06-29', 130.00, NULL, 1),
(15, 'S103', 3, '英语', '2501', '王子轩', 118.00, 3, NULL, '2025-06-29', 118.00, NULL, 1),
(16, 'S104', 3, '英语', '2501', '张思琪', 105.00, 4, NULL, '2025-06-29', 105.00, NULL, 1),
(17, 'S105', 3, '英语', '2501', '刘子墨',  92.00, 5, NULL, '2025-06-29',  92.00, NULL, 1),
(18, 'S106', 3, '英语', '2501', '周雅婷',  85.00, 6, NULL, '2025-06-29',  85.00, NULL, 1),
-- 2504班 语文 (paper 4)
(19, 'S401', 4, '语文', '2504', '冯子豪', 131.00, 1, NULL, '2025-06-27', 131.00, NULL, 1),
(20, 'S402', 4, '语文', '2504', '董思远', 119.00, 2, NULL, '2025-06-27', 119.00, NULL, 1),
(21, 'S403', 4, '语文', '2504', '程雨萱', 106.00, 3, NULL, '2025-06-27', 106.00, NULL, 1),
(22, 'S404', 4, '语文', '2504', '曹铭泽',  98.00, 4, NULL, '2025-06-27',  98.00, NULL, 1),
(23, 'S405', 4, '语文', '2504', '袁紫月',  89.00, 5, NULL, '2025-06-27',  89.00, NULL, 1),
(24, 'S406', 4, '语文', '2504', '邓皓阳',  76.00, 6, NULL, '2025-06-27',  76.00, NULL, 1);

-- =====================================================
-- 管理员数据
-- =====================================================
INSERT IGNORE INTO admin (admin_id, name, password) VALUES
('admin', '系统管理员', '$2b$12$x8z0LP7SsQwdtWviMYLQ4ectF5JiDMTNG7HXrXv38e4SL6j7GlWA.');
