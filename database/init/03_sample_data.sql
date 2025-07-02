-- Set search path
SET search_path TO real_estate, public;

-- Insert sample properties data
INSERT INTO properties (address, city, state, zip_code, property_type, bedrooms, bathrooms, square_feet, lot_size, year_built, price, date_listed, date_sold) VALUES
-- Seattle properties
('123 Pine St', 'Seattle', 'WA', '98101', 'apartment', 2, 2.0, 1200, 0, 2015, 785000, '2024-01-15', '2024-02-20'),
('456 1st Ave', 'Seattle', 'WA', '98104', 'apartment', 1, 1.0, 750, 0, 2018, 525000, '2024-02-01', '2024-03-10'),
('789 Capitol Hill', 'Seattle', 'WA', '98122', 'condo', 2, 2.0, 1100, 0, 2020, 695000, '2024-01-20', NULL),
('321 Ballard Ave', 'Seattle', 'WA', '98107', 'house', 3, 2.5, 2200, 5000, 1995, 1250000, '2024-01-10', '2024-02-28'),
('654 Queen Anne', 'Seattle', 'WA', '98109', 'apartment', 2, 1.0, 950, 0, 2010, 625000, '2024-03-01', NULL),

-- Portland properties  
('111 Pearl District', 'Portland', 'OR', '97209', 'apartment', 2, 2.0, 1150, 0, 2017, 650000, '2024-01-25', '2024-03-05'),
('222 Hawthorne', 'Portland', 'OR', '97214', 'apartment', 1, 1.0, 700, 0, 2019, 425000, '2024-02-10', NULL),
('333 Alberta St', 'Portland', 'OR', '97211', 'house', 3, 2.0, 1800, 4500, 1990, 875000, '2024-01-30', '2024-03-15'),
('444 Burnside', 'Portland', 'OR', '97214', 'condo', 2, 1.5, 1000, 0, 2021, 575000, '2024-02-15', NULL),

-- San Francisco properties
('555 Market St', 'San Francisco', 'CA', '94103', 'apartment', 1, 1.0, 650, 0, 2019, 895000, '2024-01-05', '2024-02-15'),
('666 Mission Bay', 'San Francisco', 'CA', '94158', 'condo', 2, 2.0, 1250, 0, 2022, 1450000, '2024-01-15', NULL),
('777 Nob Hill', 'San Francisco', 'CA', '94108', 'apartment', 2, 1.5, 1100, 0, 2016, 1250000, '2024-02-20', '2024-03-25'),

-- Austin properties
('888 6th Street', 'Austin', 'TX', '78701', 'apartment', 2, 2.0, 1050, 0, 2020, 485000, '2024-01-18', '2024-02-25'),
('999 South Congress', 'Austin', 'TX', '78704', 'house', 3, 2.5, 2000, 6500, 2005, 925000, '2024-02-05', NULL),
('1010 East Austin', 'Austin', 'TX', '78702', 'apartment', 1, 1.0, 800, 0, 2021, 385000, '2024-03-10', NULL);

-- Insert corresponding rental data
INSERT INTO rentals (property_id, address, city, state, zip_code, property_type, bedrooms, bathrooms, square_feet, monthly_rent, lease_start_date, lease_end_date) VALUES
(1, '123 Pine St', 'Seattle', 'WA', '98101', 'apartment', 2, 2.0, 1200, 2850, '2024-03-01', '2025-02-28'),
(2, '456 1st Ave', 'Seattle', 'WA', '98104', 'apartment', 1, 1.0, 750, 2200, '2024-03-15', '2025-03-14'),
(3, '789 Capitol Hill', 'Seattle', 'WA', '98122', 'condo', 2, 2.0, 1100, 2650, '2024-02-01', '2025-01-31'),
(4, '321 Ballard Ave', 'Seattle', 'WA', '98107', 'house', 3, 2.5, 2200, 4200, '2024-03-01', '2025-02-28'),
(5, '654 Queen Anne', 'Seattle', 'WA', '98109', 'apartment', 2, 1.0, 950, 2450, '2024-04-01', '2025-03-31'),
(6, '111 Pearl District', 'Portland', 'OR', '97209', 'apartment', 2, 2.0, 1150, 2200, '2024-03-15', '2025-03-14'),
(7, '222 Hawthorne', 'Portland', 'OR', '97214', 'apartment', 1, 1.0, 700, 1650, '2024-03-01', '2025-02-28'),
(8, '333 Alberta St', 'Portland', 'OR', '97211', 'house', 3, 2.0, 1800, 3200, '2024-04-01', '2025-03-31'),
(10, '555 Market St', 'San Francisco', 'CA', '94103', 'apartment', 1, 1.0, 650, 3200, '2024-03-01', '2025-02-28'),
(11, '666 Mission Bay', 'San Francisco', 'CA', '94158', 'condo', 2, 2.0, 1250, 4800, '2024-02-01', '2025-01-31'),
(13, '888 6th Street', 'Austin', 'TX', '78701', 'apartment', 2, 2.0, 1050, 1950, '2024-03-01', '2025-02-28'),
(15, '1010 East Austin', 'Austin', 'TX', '78702', 'apartment', 1, 1.0, 800, 1450, '2024-04-01', '2025-03-31');

-- Insert aggregated market data
INSERT INTO market_data (city, state, property_type, bedrooms, avg_price, avg_rent, avg_price_per_sqft, avg_rent_per_sqft, gross_yield, sample_size, data_date) VALUES
-- Seattle market data
('Seattle', 'WA', 'apartment', 1, 525000, 2200, 700, 2.93, 5.03, 25, CURRENT_DATE),
('Seattle', 'WA', 'apartment', 2, 678333, 2650, 648, 2.53, 4.69, 45, CURRENT_DATE),
('Seattle', 'WA', 'condo', 2, 695000, 2650, 632, 2.41, 4.57, 15, CURRENT_DATE),
('Seattle', 'WA', 'house', 3, 1250000, 4200, 568, 1.91, 4.03, 30, CURRENT_DATE),

-- Portland market data
('Portland', 'OR', 'apartment', 1, 425000, 1650, 607, 2.36, 4.66, 20, CURRENT_DATE),
('Portland', 'OR', 'apartment', 2, 650000, 2200, 565, 1.91, 4.06, 35, CURRENT_DATE),
('Portland', 'OR', 'house', 3, 875000, 3200, 486, 1.78, 4.39, 25, CURRENT_DATE),

-- San Francisco market data  
('San Francisco', 'CA', 'apartment', 1, 895000, 3200, 1377, 4.92, 4.29, 30, CURRENT_DATE),
('San Francisco', 'CA', 'apartment', 2, 1250000, 4500, 1136, 4.09, 4.32, 40, CURRENT_DATE),
('San Francisco', 'CA', 'condo', 2, 1450000, 4800, 1160, 3.84, 3.97, 20, CURRENT_DATE),

-- Austin market data
('Austin', 'TX', 'apartment', 1, 385000, 1450, 481, 1.81, 4.52, 25, CURRENT_DATE),
('Austin', 'TX', 'apartment', 2, 485000, 1950, 462, 1.86, 4.82, 35, CURRENT_DATE),
('Austin', 'TX', 'house', 3, 925000, 3500, 463, 1.75, 4.54, 20, CURRENT_DATE);

-- Add more diverse rental data without property references
INSERT INTO rentals (address, city, state, zip_code, property_type, bedrooms, bathrooms, square_feet, monthly_rent, lease_start_date, lease_end_date) VALUES
-- Additional Seattle rentals
('100 Downtown Plaza', 'Seattle', 'WA', '98101', 'apartment', 1, 1.0, 700, 2100, '2024-02-15', '2025-02-14'),
('200 Fremont Bridge', 'Seattle', 'WA', '98103', 'apartment', 2, 1.5, 1050, 2750, '2024-03-20', '2025-03-19'),
('300 U District', 'Seattle', 'WA', '98105', 'apartment', 1, 1.0, 650, 1850, '2024-01-10', '2025-01-09'),

-- Additional Portland rentals
('150 Division St', 'Portland', 'OR', '97202', 'apartment', 2, 1.0, 950, 2050, '2024-02-01', '2025-01-31'),
('250 Belmont', 'Portland', 'OR', '97214', 'condo', 1, 1.0, 725, 1750, '2024-03-05', '2025-03-04'),

-- Additional SF rentals
('700 SOMA Loft', 'San Francisco', 'CA', '94103', 'apartment', 1, 1.0, 600, 3100, '2024-01-20', '2025-01-19'),
('800 Pacific Heights', 'San Francisco', 'CA', '94115', 'apartment', 2, 2.0, 1300, 5200, '2024-02-10', '2025-02-09'),

-- Additional Austin rentals
('1100 Riverside Dr', 'Austin', 'TX', '78704', 'apartment', 2, 2.0, 1100, 2100, '2024-01-15', '2025-01-14'),
('1200 Mueller', 'Austin', 'TX', '78723', 'apartment', 1, 1.0, 750, 1550, '2024-03-01', '2025-02-28');