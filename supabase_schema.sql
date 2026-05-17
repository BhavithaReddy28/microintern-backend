CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE students (
    student_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    university VARCHAR(255),
    major VARCHAR(255),
    bio TEXT,
    resume_url VARCHAR(255),
    github_url VARCHAR(255),
    linkedin_url VARCHAR(255),
    level VARCHAR(50),
    balance NUMERIC DEFAULT 0,
    rating NUMERIC DEFAULT 0,
    hireable BOOLEAN DEFAULT TRUE,
    id_card_url TEXT,
    graduation_year INTEGER,
    verification_status TEXT DEFAULT 'pending',
    rejection_reason TEXT,
    points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    company_name VARCHAR(255),
    industry VARCHAR(100),
    company_size VARCHAR(50),
    contact_first_name VARCHAR(100),
    contact_last_name VARCHAR(100),
    phone VARCHAR(20),
    website VARCHAR(255),
    balance NUMERIC DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE CASCADE,
    task_name VARCHAR(255),
    task_date DATE,
    category VARCHAR(100),
    description TEXT,
    payment NUMERIC,
    duration VARCHAR(50),
    max_applicants INTEGER,
    skills TEXT,
    deadline DATE,
    task_link TEXT,
    level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE task_applications (
    application_id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    submission_link TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE CASCADE,
    rating NUMERIC,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE skills (
    skill_id SERIAL PRIMARY KEY,
    skill_name VARCHAR(100) UNIQUE
);

CREATE TABLE student_skills (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skills(skill_id) ON DELETE CASCADE
);

CREATE TABLE task_skills (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skills(skill_id) ON DELETE CASCADE
);

CREATE TABLE platform_stats (
    id SERIAL PRIMARY KEY,
    total_fees NUMERIC DEFAULT 0,
    total_gst NUMERIC DEFAULT 0,
    total_escrow NUMERIC DEFAULT 0
);

CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    token VARCHAR(255),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(255),
    message TEXT,
    type VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    message_id SERIAL PRIMARY KEY,
    sender_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    receiver_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    content TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE saved_tasks (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE portfolio_items (
    portfolio_id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
    title VARCHAR(255),
    description TEXT,
    media_url TEXT,
    project_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    amount NUMERIC,
    type VARCHAR(20),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
