-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    department VARCHAR(100)
);

-- Babies table
CREATE TABLE babies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    birth_date TIMESTAMP,
    parent_id INTEGER REFERENCES users(id) ON DELETE CASCADE
);

-- Feedings table
CREATE TABLE feedings (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER REFERENCES babies(id) ON DELETE CASCADE NOT NULL,
    type VARCHAR(10) NOT NULL, -- "breast", "bottle", "solid"
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    amount FLOAT,
    notes VARCHAR(500)
);

-- Sleep table
CREATE TABLE sleeps (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER REFERENCES babies(id) ON DELETE CASCADE NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    notes VARCHAR(500)
);

-- Diapers table
CREATE TABLE diapers (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER REFERENCES babies(id) ON DELETE CASCADE NOT NULL,
    type VARCHAR(10) NOT NULL, -- "wet", "dirty", "both"
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes VARCHAR(500)
);

-- Crying table
CREATE TABLE cryings (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER REFERENCES babies(id) ON DELETE CASCADE NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    reason VARCHAR(15),
    predicted_reason VARCHAR(15),
    prediction_confidence FLOAT,
    actual_reason VARCHAR(15),
    notes VARCHAR(500)
); 