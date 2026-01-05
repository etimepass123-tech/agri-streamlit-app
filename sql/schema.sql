-- REMOVED: CREATE DATABASE agri_db;
-- REMOVED: USE agri_db;

CREATE TABLE experiment_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exp_id VARCHAR(50),
    location VARCHAR(100),
    year INT,
    season VARCHAR(50),
    replication INT,
    block INT,
    treatment VARCHAR(100),
    entry_status VARCHAR(20) DEFAULT 'Draft'
);

CREATE TABLE experiment_traits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exp_id VARCHAR(50),
    trait_name VARCHAR(100),
    data_type VARCHAR(20) DEFAULT 'number',
    unit VARCHAR(50),
    is_active TINYINT(1) DEFAULT 1
);

CREATE TABLE observation_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metadata_id INT,
    attribute_name VARCHAR(100),
    attribute_value DOUBLE,
    FOREIGN KEY (metadata_id) REFERENCES experiment_metadata(id)
);
