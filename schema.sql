CREATE TABLE college (
    id UUID PRIMARY KEY,
    name TEXT,
    location TEXT,
    established_date DATE,
    website TEXT,
    email TEXT,
    phone TEXT,
    description TEXT
);

CREATE TABLE courses (
    id UUID PRIMARY KEY,
    name TEXT,
    description TEXT,
    duration TEXT,
    fees NUMERIC,
    college_id UUID REFERENCES college(id)
);

CREATE TABLE students (
    id UUID PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    date_of_birth DATE,
    gender TEXT,
    address TEXT,
    college_id UUID REFERENCES college(id)
);

CREATE TABLE enrollments (
    id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(id),
    course_id UUID REFERENCES courses(id),
    enrollment_date DATE,
    completion_date DATE
);

CREATE TABLE timetable (
    id UUID PRIMARY KEY,
    course_id UUID REFERENCES courses(id),
    timings int[] -- Array of timings in minutes from 00:00 of Sunday. Example Wednesday 10:00 AM to 11:30 AM will be represented as [1440*3 + 600, 1440*3 + 600 + 90] = [5400, 5490]
);

CREATE TABLE faculty (
    id UUID PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    date_of_birth DATE,
    gender TEXT,
    address TEXT,
    college_id UUID REFERENCES college(id)
);

CREATE TABLE classes (
    id UUID PRIMARY KEY,
    course_id UUID REFERENCES courses(id),
    faculty_id UUID REFERENCES faculty(id),
    timetable_id UUID REFERENCES timetable(id),
    start_time timestamp with time zone,
    end_time timestamp with time zone
);

CREATE TABLE attendance (
    id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(id),
    class_id UUID REFERENCES classes(id),
    date DATE,
    status TEXT -- present, absent, late
); 