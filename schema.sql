-- Normalized schema for the resume backend.
-- Run via `python seed.py`, which creates the database first and then applies
-- these statements. To apply by hand: `mysql -u root -p resume < schema.sql`.

SET NAMES utf8mb4;

-- Single-row table holding the resume headline.
CREATE TABLE IF NOT EXISTS profile (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(200) NOT NULL,
    title    VARCHAR(200) NOT NULL,
    location VARCHAR(200) NOT NULL,
    summary  TEXT         NOT NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS contact (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    label      VARCHAR(60)  NOT NULL,
    value      VARCHAR(255) NOT NULL,
    href       VARCHAR(500) NOT NULL,
    sort_order INT          NOT NULL DEFAULT 0,
    INDEX idx_contact_order (sort_order, id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS experience (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    role       VARCHAR(200) NOT NULL,
    org        VARCHAR(200) NOT NULL,
    period     VARCHAR(100) NOT NULL,
    sort_order INT          NOT NULL DEFAULT 0,
    INDEX idx_experience_order (sort_order, id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

-- Bullet points belonging to an experience entry.
CREATE TABLE IF NOT EXISTS experience_points (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    experience_id INT NOT NULL,
    text          TEXT NOT NULL,
    sort_order    INT  NOT NULL DEFAULT 0,
    INDEX idx_points_owner (experience_id, sort_order, id),
    CONSTRAINT fk_points_experience FOREIGN KEY (experience_id)
        REFERENCES experience (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS projects (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(200) NOT NULL,
    blurb      TEXT         NOT NULL,
    sort_order INT          NOT NULL DEFAULT 0,
    INDEX idx_projects_order (sort_order, id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS education (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    title      VARCHAR(200) NOT NULL,
    org        VARCHAR(200) NOT NULL,
    period     VARCHAR(100) NOT NULL,
    sort_order INT          NOT NULL DEFAULT 0,
    INDEX idx_education_order (sort_order, id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

-- Skills are shared between experience entries and projects.
CREATE TABLE IF NOT EXISTS skills (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    UNIQUE KEY uq_skill_name (name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS experience_skills (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    experience_id INT NOT NULL,
    skill_id      INT NOT NULL,
    UNIQUE KEY uq_experience_skill (experience_id, skill_id),
    CONSTRAINT fk_es_experience FOREIGN KEY (experience_id)
        REFERENCES experience (id) ON DELETE CASCADE,
    CONSTRAINT fk_es_skill FOREIGN KEY (skill_id)
        REFERENCES skills (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS project_skills (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    skill_id   INT NOT NULL,
    UNIQUE KEY uq_project_skill (project_id, skill_id),
    CONSTRAINT fk_ps_project FOREIGN KEY (project_id)
        REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_ps_skill FOREIGN KEY (skill_id)
        REFERENCES skills (id) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
