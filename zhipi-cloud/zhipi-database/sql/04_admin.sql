-- =====================================================
-- 智批云 - 管理员表 + 种子数据
-- 对应子模式设计中的"管理子模式"
-- =====================================================

USE zhipi_cloud;

-- 管理员表
CREATE TABLE IF NOT EXISTS admin (
    admin_id    VARCHAR(15)  NOT NULL COMMENT '管理员编号，主键',
    name        VARCHAR(15)  NOT NULL COMMENT '管理员姓名',
    password    VARCHAR(255) NOT NULL COMMENT '登录密码（bcrypt加密）',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (admin_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统管理员表';

-- 种子数据：管理员账号 admin / 123456
INSERT IGNORE INTO admin (admin_id, name, password) VALUES
('admin', '系统管理员', '$2b$12$j9V0TqqtVKEmtLmBVCC8B..ztXDOHFkXQ5onX.0nbV9uSKunLyEVC');
