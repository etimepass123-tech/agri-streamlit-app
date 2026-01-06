-- Locations
CREATE TABLE locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('super_admin','admin','user') NOT NULL,
    location_id INT,
    FOREIGN KEY (location_id) REFERENCES locations(id)
        ON DELETE SET NULL
);

-- Experiment metadata (A–G + treatment rows)
CREATE TABLE experiment_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exp_id VARCHAR(100),
    location VARCHAR(100),
    year INT,
    season VARCHAR(50),
    replication INT,
    block INT,
    treatment VARCHAR(100),
    entry_status ENUM('Draft','Submitted') DEFAULT 'Draft',
    is_active TINYINT(1) DEFAULT 1,
    location_id INT NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations(id)
        ON DELETE CASCADE
);

-- Traits (H+ columns)
CREATE TABLE experiment_traits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exp_id VARCHAR(100),
    trait_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) DEFAULT 'number',
    unit VARCHAR(50) DEFAULT '',
    is_active TINYINT(1) DEFAULT 1,
    location_id INT NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations(id)
        ON DELETE CASCADE
);

-- Observation data (long format)
CREATE TABLE observation_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT NOT NULL,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value DOUBLE,
    location_id INT NOT NULL,
    FOREIGN KEY (metadata_id) REFERENCES experiment_metadata(id)
        ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id)
        ON DELETE CASCADE
);
