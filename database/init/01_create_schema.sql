-- Create schema for real estate data
CREATE SCHEMA IF NOT EXISTS real_estate;

-- Set default search path for the database
ALTER DATABASE real_estate_db SET search_path TO real_estate, public;

-- Set search path for current session
SET search_path TO real_estate, public;