-- =====================================================
-- 智批云 (ZhiPi Cloud) - 数据库建表脚本
-- 数据库: zhipi_cloud
-- 引擎: MySQL InnoDB
-- 字符集: utf8mb4
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS zhipi_cloud
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE zhipi_cloud;

-- =====================================================
-- 1. 班级表 (class)
-- 存储班级基本信息
-- =====================================================
CREATE TABLE IF NOT EXISTS class (
    class_id    VARCHAR(20)  NOT NULL COMMENT '班级编号，如 24计科2班',
    class_name  VARCHAR(50)  NOT NULL COMMENT '班级全称',
    grade       VARCHAR(10)  NOT NULL COMMENT '年级，如 2024',
    department  VARCHAR(50)  DEFAULT NULL COMMENT '所属院系',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班级信息表';


-- =====================================================
-- 2. 用户表：学生 (student)
-- 对应需求分析：学号6位，姓名9字符，班级2位int
-- =====================================================
CREATE TABLE IF NOT EXISTS student (
    student_id  VARCHAR(15)  NOT NULL COMMENT '学号，主键，唯一标识',
    name        VARCHAR(15)  NOT NULL COMMENT '学生姓名',
    class_id    VARCHAR(20)  NOT NULL COMMENT '所在班级编号，外键关联class表',
    password    VARCHAR(255) NOT NULL DEFAULT '123456' COMMENT '登录密码（加密存储）',
    phone       VARCHAR(15)  DEFAULT NULL COMMENT '联系电话',
    created_at  TIMESTAMP    NULL     DEFAULT NULL,
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id),
    KEY idx_class (class_id),
    CONSTRAINT fk_student_class FOREIGN KEY (class_id) REFERENCES class (class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生信息表';


-- =====================================================
-- 3. 用户表：教师 (teacher)
-- 对应数据库设计：teacher_id, name, class, subject, task
-- =====================================================
CREATE TABLE IF NOT EXISTS teacher (
    teacher_id  VARCHAR(15)  NOT NULL COMMENT '教师编号，主键',
    name        VARCHAR(15)  NOT NULL COMMENT '教师姓名',
    class_id    VARCHAR(20)  NOT NULL COMMENT '负责班级，外键关联class表',
    subject     VARCHAR(15)  NOT NULL COMMENT '任教科目',
    password    VARCHAR(255) NOT NULL DEFAULT '123456' COMMENT '登录密码（加密存储）',
    task        INT          NOT NULL DEFAULT 0 COMMENT '累计批阅任务数',
    phone       VARCHAR(15)  DEFAULT NULL COMMENT '联系电话',
    created_at  TIMESTAMP    NULL     DEFAULT NULL,
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (teacher_id),
    KEY idx_class (class_id),
    CONSTRAINT fk_teacher_class FOREIGN KEY (class_id) REFERENCES class (class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师信息表';


-- =====================================================
-- 4. 试卷表 (paper)
-- 存储试卷和标准答案配置
-- =====================================================
CREATE TABLE IF NOT EXISTS paper (
    paper_id        INT          NOT NULL AUTO_INCREMENT COMMENT '试卷ID',
    title           VARCHAR(100) NOT NULL COMMENT '试卷标题',
    subject         VARCHAR(15)  NOT NULL COMMENT '科目',
    class_id        VARCHAR(20)  NOT NULL COMMENT '适用班级',
    teacher_id      VARCHAR(15)  NOT NULL COMMENT '出卷教师ID',
    total_score     DECIMAL(5,2) NOT NULL DEFAULT 150 COMMENT '总分（默认150分）',
    exam_date       DATE         NOT NULL COMMENT '考试日期',
    status          TINYINT      NOT NULL DEFAULT 0 COMMENT '状态：0=草稿 1=发布 2=批阅中 3=已完成',
    answer_key      TEXT         DEFAULT NULL COMMENT '客观题标准答案（JSON格式）',
    description     TEXT         DEFAULT NULL COMMENT '试卷描述',
    created_at      TIMESTAMP    NULL     DEFAULT NULL,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (paper_id),
    KEY idx_class_subject (class_id, subject),
    KEY idx_teacher (teacher_id),
    KEY idx_exam_date (exam_date),
    CONSTRAINT fk_paper_teacher FOREIGN KEY (teacher_id) REFERENCES teacher (teacher_id),
    CONSTRAINT fk_paper_class FOREIGN KEY (class_id) REFERENCES class (class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='试卷信息表';


-- =====================================================
-- 5. 成绩表 (score)
-- 核心表，记录学生每次考试成绩和排名
-- 物理设计：按 exam_date 范围分区，辅助索引见下方
-- =====================================================
CREATE TABLE IF NOT EXISTS score (
    score_id        INT          NOT NULL AUTO_INCREMENT COMMENT '成绩记录ID',
    student_id      VARCHAR(15)  NOT NULL COMMENT '学号，外键',
    paper_id        INT          NOT NULL COMMENT '试卷ID，外键',
    subject         VARCHAR(15)  NOT NULL COMMENT '科目',
    class_id        VARCHAR(20)  NOT NULL COMMENT '班级',
    name            VARCHAR(15)  NOT NULL COMMENT '学生姓名（冗余以提高查询效率）',
    score           DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '成绩，范围0-150',
    rank_in_class   INT          DEFAULT NULL COMMENT '班级排名',
    rank_in_all     INT          DEFAULT NULL COMMENT '全校排名',
    exam_date       DATE         NOT NULL COMMENT '考试日期',
    ai_score        DECIMAL(5,2) DEFAULT NULL COMMENT 'AI批阅得分（客观题部分）',
    manual_score    DECIMAL(5,2) DEFAULT NULL COMMENT '教师手动批阅得分（主观题部分）',
    status          TINYINT      NOT NULL DEFAULT 0 COMMENT '状态：0=待批阅 1=AI批阅中 2=待人工审核 3=已完成',
    answer_image    VARCHAR(500) DEFAULT NULL COMMENT '答卷图片路径',
    ai_result       TEXT         DEFAULT NULL COMMENT 'AI批阅结果详情（JSON）',
    created_at      TIMESTAMP    NULL     DEFAULT NULL,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (score_id),
    UNIQUE KEY uk_student_paper (student_id, paper_id),
    -- 物理设计中的辅助索引（B+Tree）
    KEY idx_exam_date_subject (exam_date, subject),
    KEY idx_class_subject_score (class_id, subject, score),
    KEY idx_student (student_id),
    KEY idx_status (status),
    KEY idx_status_class (status, class_id),
    CONSTRAINT fk_score_student FOREIGN KEY (student_id) REFERENCES student (student_id),
    CONSTRAINT fk_score_paper FOREIGN KEY (paper_id) REFERENCES paper (paper_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成绩记录表';


-- =====================================================
-- 6. 操作日志表 (operation_log)
-- 安全与日志审计模块
-- =====================================================
CREATE TABLE IF NOT EXISTS operation_log (
    log_id      BIGINT       NOT NULL AUTO_INCREMENT COMMENT '日志ID',
    user_id     VARCHAR(15)  NOT NULL COMMENT '操作用户ID（学号或教师编号）',
    user_type   TINYINT      NOT NULL DEFAULT 0 COMMENT '用户类型：0=学生 1=教师',
    action      VARCHAR(100) NOT NULL COMMENT '操作行为描述',
    module      VARCHAR(50)  NOT NULL COMMENT '所属模块',
    ip_address  VARCHAR(50)  DEFAULT NULL COMMENT 'IP地址',
    detail      TEXT         DEFAULT NULL COMMENT '详细信息（JSON）',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    KEY idx_user (user_id, user_type),
    KEY idx_created_at (created_at),
    KEY idx_module (module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统操作日志表';


-- =====================================================
-- =====================================================
-- 索引设计说明（对应物理设计文档）
-- =====================================================
-- Score(exam_date, subject): 支持按考试日期+科目筛选成绩，用于生成班级排名
-- Score(class_id, subject, score): 班级单科成绩排序，避免回表（覆盖索引）
-- Score(status): 待批阅列表查询加速
-- Score(status, class_id): 按班级查询待批阅记录
-- Teacher(class_id): 查询某班级的任课教师
-- 已在表定义中包含上述索引
