CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(50) PRIMARY KEY,
    brand_name VARCHAR(100) NOT NULL,
    theme_color VARCHAR(10) NOT NULL,
    system_prompt TEXT NOT NULL,
    knowledge_base JSONB NOT NULL,
    booking_rules JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) REFERENCES tenants(tenant_id),
    client_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    slot_time VARCHAR(50) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO tenants (tenant_id, brand_name, theme_color, system_prompt, knowledge_base, booking_rules)
VALUES (
  'city-care-clinic',
  'City Care Clinic',
  '#0e7490',
  'You are a professional medical intake AI for City Care Clinic. Maintain an empathetic, calm tone. Prioritize urgent symptoms by directing users to emergency services if red flags are detected.',
  '[{"q": "What is the consultation fee?", "a": "OPD consultations are $50."}, {"q": "What are your operating hours?", "a": "Mon-Sat, 8:00 AM to 6:00 PM."}]'::jsonb,
  '{"slot_duration_mins": 30, "required_fields": ["patient_name", "phone", "reason_for_visit"]}'::jsonb
) ON CONFLICT (tenant_id) DO UPDATE SET system_prompt = EXCLUDED.system_prompt;

INSERT INTO tenants (tenant_id, brand_name, theme_color, system_prompt, knowledge_base, booking_rules)
VALUES (
  'prime-realty',
  'Prime Realty',
  '#b45309',
  'You are an energetic sales assistant for Prime Realty. Focus on capturing high-intent buyer leads and scheduling property walkthroughs.',
  '[{"q": "Where are your properties located?", "a": "Downtown, Westside Meadows, and Harbor View."}, {"q": "What is the down payment?", "a": "Standard financing requires 10% to 20% down."}]'::jsonb,
  '{"slot_duration_mins": 60, "required_fields": ["client_name", "phone", "budget_range"]}'::jsonb
) ON CONFLICT (tenant_id) DO UPDATE SET system_prompt = EXCLUDED.system_prompt;
