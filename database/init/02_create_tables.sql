-- Set search path
SET search_path TO real_estate, public;

-- Create properties table
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(10),
    property_type VARCHAR(50) NOT NULL,
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    square_feet INTEGER,
    lot_size DECIMAL(10,2),
    year_built INTEGER,
    price DECIMAL(12,2),
    date_listed DATE,
    date_sold DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create rentals table
CREATE TABLE IF NOT EXISTS rentals (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id),
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(10),
    property_type VARCHAR(50) NOT NULL,
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    square_feet INTEGER,
    monthly_rent DECIMAL(10,2),
    lease_start_date DATE,
    lease_end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create market_data table for aggregated metrics
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    property_type VARCHAR(50) NOT NULL,
    bedrooms INTEGER,
    avg_price DECIMAL(12,2),
    avg_rent DECIMAL(10,2),
    avg_price_per_sqft DECIMAL(10,2),
    avg_rent_per_sqft DECIMAL(10,2),
    gross_yield DECIMAL(5,2),
    sample_size INTEGER,
    data_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_properties_city_type ON properties(city, property_type);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_date_sold ON properties(date_sold);
CREATE INDEX IF NOT EXISTS idx_properties_bedrooms ON properties(bedrooms);

CREATE INDEX IF NOT EXISTS idx_rentals_city_type ON rentals(city, property_type);
CREATE INDEX IF NOT EXISTS idx_rentals_rent ON rentals(monthly_rent);
CREATE INDEX IF NOT EXISTS idx_rentals_bedrooms ON rentals(bedrooms);

CREATE INDEX IF NOT EXISTS idx_market_data_city_type ON market_data(city, property_type);
CREATE INDEX IF NOT EXISTS idx_market_data_date ON market_data(data_date);

-- Create view for easy yield calculations
CREATE OR REPLACE VIEW property_yields AS
SELECT 
    p.id,
    p.city,
    p.state,
    p.property_type,
    p.bedrooms,
    p.bathrooms,
    p.square_feet,
    p.price,
    r.monthly_rent,
    CASE 
        WHEN p.price > 0 THEN (r.monthly_rent * 12) / p.price * 100
        ELSE NULL
    END as gross_yield,
    p.date_listed,
    p.date_sold
FROM properties p
LEFT JOIN rentals r ON p.id = r.property_id
WHERE p.price > 0 AND r.monthly_rent > 0;

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rentals_updated_at BEFORE UPDATE ON rentals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();