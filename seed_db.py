import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "database": "microinternDB",
    "user": "postgres",
    "password": "2810",
    "port": 5433
}

def seed():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # Create a demo company
        cur.execute("INSERT INTO users (email, password_hash, role) VALUES ('demo@company.com', 'pbkdf2:sha256:1000000$demo$demo', 'company') RETURNING user_id")
        user_id = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO companies (user_id, company_name, industry, company_size, contact_first_name, contact_last_name, phone, website) 
            VALUES (%s, 'TechCorp', 'Technology', '50-200', 'Demo', 'User', '1234567890', 'https://techcorp.com') 
            RETURNING company_id
        """, (user_id,))
        company_id = cur.fetchone()[0]
        
        # Create some tasks
        tasks = [
            (company_id, 'Frontend Developer (React)', 'Engineering', 'Develop responsive UI components using React and Tailwind CSS.', 500, '2 weeks', 5, 'React, Tailwind, TypeScript', '2026-06-01'),
            (company_id, 'Content Writer', 'Marketing', 'Write high-quality blog posts and social media content for our tech blog.', 200, '1 week', 3, 'Writing, SEO, Social Media', '2026-05-20'),
            (company_id, 'Python Backend Assistant', 'Engineering', 'Help maintain Flask APIs and database migrations.', 450, '3 weeks', 2, 'Python, Flask, PostgreSQL', '2026-06-15')
        ]
        
        for t in tasks:
            cur.execute("""
                INSERT INTO tasks (company_id, task_name, task_date, category, description, payment, duration, max_applicants, skills, deadline) 
                VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s)
            """, t)
            
        conn.commit()
        print("Database seeded successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Seeding failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed()
