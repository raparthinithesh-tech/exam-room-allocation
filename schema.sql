-- Online Examination Hall Allocation Portal
-- Database Schema

CREATE DATABASE IF NOT EXISTS exam_portal;
USE exam_portal;

-- Student Table
CREATE TABLE IF NOT EXISTS Student (
    Roll_No VARCHAR(20) PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Password VARCHAR(255) NOT NULL,
    Branch VARCHAR(50) NOT NULL,
    Email VARCHAR(100),
    Phone VARCHAR(15),
    Semester INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exam Table
CREATE TABLE IF NOT EXISTS Exam (
    Exam_ID INT AUTO_INCREMENT PRIMARY KEY,
    Subject VARCHAR(100) NOT NULL,
    Date DATE NOT NULL,
    Time VARCHAR(20) NOT NULL,
    Duration VARCHAR(20) DEFAULT '3 Hours',
    Semester INT,
    Branch VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Allocation Table
CREATE TABLE IF NOT EXISTS Allocation (
    Alloc_ID INT AUTO_INCREMENT PRIMARY KEY,
    Roll_No VARCHAR(20) NOT NULL,
    Exam_ID INT NOT NULL,
    Room_No VARCHAR(20) NOT NULL,
    Seat_No VARCHAR(10) NOT NULL,
    Block VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Roll_No) REFERENCES Student(Roll_No) ON DELETE CASCADE,
    FOREIGN KEY (Exam_ID) REFERENCES Exam(Exam_ID) ON DELETE CASCADE,
    UNIQUE KEY unique_alloc (Roll_No, Exam_ID)
);

-- Sample Data
INSERT INTO Student (Roll_No, Name, Password, Branch, Email, Phone, Semester) VALUES
('CS001', 'Arjun Sharma', 'pass123', 'Computer Science', 'arjun@college.edu', '9876543210', 4),
('CS002', 'Priya Nair', 'pass123', 'Computer Science', 'priya@college.edu', '9876543211', 4),
('EC001', 'Rahul Verma', 'pass123', 'Electronics', 'rahul@college.edu', '9876543212', 4),
('ME001', 'Sneha Patel', 'pass123', 'Mechanical', 'sneha@college.edu', '9876543213', 4);

INSERT INTO Exam (Subject, Date, Time, Duration, Semester, Branch) VALUES
('Data Structures', '2026-06-20', '09:00 AM', '3 Hours', 4, 'Computer Science'),
('Digital Electronics', '2026-06-21', '02:00 PM', '3 Hours', 4, 'Electronics'),
('Database Management', '2026-06-22', '09:00 AM', '3 Hours', 4, 'Computer Science'),
('Engineering Mechanics', '2026-06-23', '02:00 PM', '3 Hours', 4, 'Mechanical');

INSERT INTO Allocation (Roll_No, Exam_ID, Room_No, Seat_No, Block) VALUES
('CS001', 1, 'A-101', 'S-01', 'Block A'),
('CS001', 3, 'B-202', 'S-05', 'Block B'),
('CS002', 1, 'A-101', 'S-02', 'Block A'),
('CS002', 3, 'B-202', 'S-06', 'Block B'),
('EC001', 2, 'C-301', 'S-10', 'Block C'),
('ME001', 4, 'D-401', 'S-15', 'Block D');
