-- ================================================
--  DATABASE: Elderly Cybersecurity E-Learning (MySQL)
--  Fully Matches app.py Models
-- ================================================

CREATE DATABASE IF NOT EXISTS ecs_learning
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ecs_learning;

-- ================================================
-- USERS
-- ================================================
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(120),
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    active BOOLEAN DEFAULT TRUE,
    points INT DEFAULT 0,
    level INT DEFAULT 1
);

-- ================================================
-- LESSONS
-- ================================================
CREATE TABLE lessons (
    id INT PRIMARY KEY AUTO_INCREMENT,
    module VARCHAR(120) DEFAULT 'Cyber Safety Basics',
    title VARCHAR(200) NOT NULL,
    body TEXT,
    video VARCHAR(300)
);

-- ================================================
-- QUIZZES
-- ================================================
CREATE TABLE quizzes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    lesson_id INT NOT NULL,
    question VARCHAR(400) NOT NULL,
    options_json TEXT NOT NULL,
    correct_index INT NOT NULL,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- ================================================
-- USER LESSON PROGRESS
-- ================================================
CREATE TABLE user_lessons (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    lesson_id INT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- ================================================
-- ACHIEVEMENTS
-- ================================================
CREATE TABLE achievements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(120) UNIQUE,
    description VARCHAR(300)
);

-- ================================================
-- USER → ACHIEVEMENTS
-- ================================================
CREATE TABLE user_achievements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    achievement_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);

-- ================================================
-- FORUM POSTS
-- ================================================
CREATE TABLE forum_posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    text TEXT NOT NULL,
    ts VARCHAR(40),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ================================================
-- SUPPORT CHAT (User ↔ Admin)
-- ================================================
CREATE TABLE support_messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    from_admin BOOLEAN DEFAULT FALSE,
    text TEXT NOT NULL,
    ts VARCHAR(40),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ================================================
-- INSERT DEFAULT ACHIEVEMENTS
-- ================================================
INSERT INTO achievements (name, description) VALUES
('First Steps', 'Completed your first lesson!'),
('All Done', 'Completed all lessons in the course.'),
('Quiz Whiz', 'Scored 100% on a quiz.');

-- ================================================
-- INSERT DEFAULT ADMIN ACCOUNT
-- (You can change the password hash later)
-- Password = Admin@1234 (must be ≥10 chars with symbol/number/letter)
-- ================================================
INSERT INTO users (name, email, password_hash, role, active)
VALUES ('Admin', 'admin@site.com',
'$pbkdf2-sha256$29000$mj2nXr6nTq2e4Z6k1$uEIbkAhxQvdyYiBFpdjqAMwHwA7Tcln5ZQFH9/Jw0UI',
'admin', TRUE);
