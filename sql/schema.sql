CREATE DATABASE agri_streamlit;
USE agri_streamlit;

-- A–G METADATA
CREATE TABLE experiment_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exp_id VARCHAR(100),
    location VARCHAR(100),
    year INT,
    season VARCHAR(50),
    replication INT,
    block INT,
    treatment VARCHAR(100),
    entry_status ENUM('New','Draft','Submitted') DEFAULT 'New'
);

-- H+ TRAIT DEFINITIONS
CREATE TABLE experiment_traits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exp_id VARCHAR(100),
    trait_name VARCHAR(100)
);

-- LONG FORMAT VALUES
CREATE TABLE observation_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT,
    attribute_name VARCHAR(100),
    attribute_value DOUBLE,
    entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
